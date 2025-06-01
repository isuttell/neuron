import os
import logging
import io
import asyncio
import json
import re
from typing import Optional, Dict, Set
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

import httpx
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress verbose httpcore logs
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# Configuration from environment
IMAGE_URL = os.getenv("IMAGE_URL", "https://ha.zaks.io/local/dashboard-art.png")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Paths
CURRENT_DIR = Path(__file__).parent.parent  # Go up one level from dashboard_viewer/ to project root
DIST_DIR = CURRENT_DIR / "dist"

# HTTP client for proxying requests
client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """Send message to all connected clients"""
        if not self.active_connections:
            return

        message_json = json.dumps(message)
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.error(f"Error sending to websocket: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        self.active_connections -= disconnected

manager = ConnectionManager()

# Polling state and image cache
class PollingState:
    def __init__(self):
        self.current_etag: Optional[str] = None
        self.last_check: Optional[datetime] = None
        self.poll_interval: int = 10  # seconds
        self.is_polling: bool = False
        # Image cache
        self.cached_image: Optional[bytes] = None
        self.cached_content_type: Optional[str] = None
        self.cached_headers: Dict[str, str] = {}
        # JavaScript hash for auto-refresh
        self.js_hash: Optional[str] = None

polling_state = PollingState()


def get_js_hash() -> Optional[str]:
    """Extract the JavaScript hash from index.html for auto-refresh detection"""
    try:
        index_path = DIST_DIR / "index.html"
        if not index_path.exists():
            return None

        content = index_path.read_text()
        # Look for script tag with hash in filename
        match = re.search(r'src="/assets/index-([a-zA-Z0-9_-]+)\.js"', content)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        logger.error(f"Error extracting JS hash: {e}")
        return None


async def fetch_and_cache_image():
    """Fetch the image and cache it in memory"""
    try:
        logger.info(f"Fetching image from: {IMAGE_URL}")
        response = await client.get(IMAGE_URL)

        if response.status_code == 200:
            # Cache the image data
            polling_state.cached_image = response.content
            polling_state.cached_content_type = response.headers.get("content-type", "image/png")

            # Cache relevant headers
            polling_state.cached_headers = {}
            for header in ["etag", "last-modified"]:
                if header in response.headers:
                    polling_state.cached_headers[header] = response.headers[header]

            logger.info(f"Cached image: {len(polling_state.cached_image)} bytes, ETag: {polling_state.cached_headers.get('etag')}")
            return True
        else:
            logger.error(f"Failed to fetch image: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error fetching image: {e}")
        return False


async def poll_for_changes():
    """Background task to poll for image changes"""
    # Fetch initial image on startup
    if not polling_state.cached_image:
        await fetch_and_cache_image()

    while polling_state.is_polling:
        try:
            response = await client.head(IMAGE_URL)

            if response.status_code == 200:
                new_etag = response.headers.get("etag")

                if new_etag and new_etag != polling_state.current_etag:
                    logger.info(f"Image changed! New ETag: {new_etag}")
                    polling_state.current_etag = new_etag
                    polling_state.last_check = datetime.now()

                    # Fetch and cache the new image
                    if await fetch_and_cache_image():
                        # Notify all connected clients
                        await manager.broadcast({
                            "type": "image_changed",
                            "etag": new_etag,
                            "timestamp": polling_state.last_check.isoformat()
                        })

        except Exception as e:
            logger.error(f"Error polling for changes: {e}")
            # Notify clients of error
            await manager.broadcast({
                "type": "error",
                "message": f"Failed to check for updates: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })

        # Wait before next check
        await asyncio.sleep(polling_state.poll_interval)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    logger.info(f"Dashboard Viewer starting...")
    logger.info(f"Image URL: {IMAGE_URL}")
    logger.info(f"Serving on: {HOST}:{PORT}")
    logger.info(f"Static files from: {DIST_DIR}")

    if not DIST_DIR.exists():
        logger.warning(f"Static files directory not found: {DIST_DIR}")
        logger.warning("Run 'npm run build' to build the frontend")

    # Initialize JavaScript hash for auto-refresh
    polling_state.js_hash = get_js_hash()
    if polling_state.js_hash:
        logger.info(f"JavaScript hash: {polling_state.js_hash}")
    else:
        logger.warning("Could not extract JavaScript hash")

    # Start polling task
    polling_state.is_polling = True
    poll_task = asyncio.create_task(poll_for_changes())

    yield

    # Shutdown
    polling_state.is_polling = False
    await poll_task
    await client.aclose()


app = FastAPI(title="Dashboard Viewer", lifespan=lifespan)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.head("/image")
async def image_head():
    """
    Proxy HEAD requests to the image URL.
    Returns headers including ETag for change detection.
    """
    try:
        response = await client.head(IMAGE_URL)

        # Copy relevant headers
        headers = {}
        for header in ["etag", "last-modified", "content-type", "content-length"]:
            if header in response.headers:
                headers[header] = response.headers[header]

        # Use cache control that requires revalidation
        headers["cache-control"] = "private, max-age=0, must-revalidate"

        return Response(
            status_code=response.status_code,
            headers=headers
        )
    except httpx.ConnectError as e:
        logger.error(f"Connection error to {IMAGE_URL}: {e}")
        raise HTTPException(status_code=502, detail=f"Cannot connect to image server: {str(e)}")
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy HEAD request: {e}")
        raise HTTPException(status_code=502, detail="Failed to reach image server")


@app.get("/image")
async def image_get(request: Request):
    """
    Serve the cached image with proper ETag handling.
    """
    # Check if we have a cached image
    if not polling_state.cached_image:
        logger.error("No cached image available")
        raise HTTPException(status_code=503, detail="Image not yet available")

    # Get request headers
    client_etag = request.headers.get("if-none-match")
    current_etag = polling_state.cached_headers.get("etag")

    # If client has matching ETag, return 304
    if client_etag and current_etag and client_etag == current_etag:
        return Response(
            status_code=304,
            headers={
                "etag": current_etag,
                "cache-control": "public, max-age=31536000, immutable"
            }
        )

    # Return the cached image
    return Response(
        content=polling_state.cached_image,
        media_type=polling_state.cached_content_type,
        headers={
            "etag": current_etag,
            "cache-control": "public, max-age=31536000, immutable",
            "content-length": str(len(polling_state.cached_image))
        }
    )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)

    try:
        # Send initial state
        await websocket.send_json({
            "type": "connected",
            "current_etag": polling_state.current_etag,
            "last_check": polling_state.last_check.isoformat() if polling_state.last_check else None,
            "js_hash": polling_state.js_hash
        })

        # Keep connection alive
        while True:
            try:
                # Wait for client messages
                message = await websocket.receive()

                # Check message type
                if message["type"] == "websocket.disconnect":
                    break
                elif message["type"] == "websocket.receive":
                    if "text" in message:
                        data = message["text"]
                        # Handle ping with hash check
                        if data == "ping":
                            current_js_hash = get_js_hash()
                            response = {
                                "type": "pong",
                                "js_hash": current_js_hash
                            }
                            # Check if hash changed
                            if current_js_hash != polling_state.js_hash:
                                logger.info(f"JavaScript hash changed: {polling_state.js_hash} -> {current_js_hash}")
                                polling_state.js_hash = current_js_hash
                                response["hash_changed"] = True
                            await websocket.send_json(response)
                    elif "bytes" in message:
                        # Handle binary messages if needed
                        pass

            except RuntimeError:
                # Connection closed
                break
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        manager.disconnect(websocket)


@app.get("/api/config")
async def get_config():
    """Return current configuration for debugging"""
    return {
        "image_url": IMAGE_URL,
        "server": f"{HOST}:{PORT}",
        "poll_interval": polling_state.poll_interval,
        "websocket_url": f"ws://{HOST}:{PORT}/ws"
    }


@app.get("/api/status")
async def get_status():
    """Return current polling status"""
    return {
        "is_polling": polling_state.is_polling,
        "current_etag": polling_state.current_etag,
        "last_check": polling_state.last_check.isoformat() if polling_state.last_check else None,
        "connected_clients": len(manager.active_connections),
        "js_hash": polling_state.js_hash
    }


@app.get("/test-etag")
async def test_etag(request: Request):
    """Test endpoint to debug ETag behavior"""
    client_etag = request.headers.get("if-none-match")
    test_etag = '"test-etag-123"'

    if client_etag == test_etag:
        return Response(
            status_code=304,
            headers={
                "etag": test_etag,
                "cache-control": "private, max-age=0, must-revalidate"
            }
        )
    else:
        return Response(
            content=b"Test content",
            headers={
                "etag": test_etag,
                "cache-control": "private, max-age=0, must-revalidate",
                "content-type": "text/plain"
            }
        )


# Test WebSocket endpoint
@app.get("/test-ws")
async def test_ws():
    """Serve WebSocket test page"""
    return FileResponse(CURRENT_DIR / "test-ws.html")

# Serve static files - must be last to avoid catching other routes
if DIST_DIR.exists():
    # Serve the built dashboard viewer
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")
else:
    # Development fallback
    @app.get("/")
    async def root():
        return {
            "error": "Frontend not built",
            "message": "Run 'npm run build' to build the dashboard viewer",
            "image_url": IMAGE_URL
        }


def main():
    """Main entry point for the dashboard viewer server"""
    import uvicorn
    uvicorn.run(
        "dashboard_viewer.server:app",
        host=HOST,
        port=PORT,
        reload=os.getenv("DEV_MODE", "false").lower() == "true"
    )


if __name__ == "__main__":
    main()
