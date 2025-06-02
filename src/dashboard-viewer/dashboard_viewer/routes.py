"""API routes for the dashboard viewer."""
import logging
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

from .config import HOST, IMAGE_URL, PORT
from .polling import PollingState, get_js_hash
from .websocket import ConnectionManager

logger = logging.getLogger(__name__)


def setup_routes(app: Any, client: Any, polling_state: PollingState,
                manager: ConnectionManager, current_dir: Any) -> None:
    """Set up all API routes."""

    @app.head("/image")
    async def image_head() -> Response:
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

            return Response(status_code=response.status_code, headers=headers)
        except Exception as e:
            logger.error(f"Failed to proxy HEAD request: {e}")
            raise HTTPException(
                status_code=502, detail="Failed to reach image server"
            ) from e

    @app.get("/image")
    async def image_get(request: Request) -> Response:
        """Serve the cached image with proper ETag handling."""
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
                    "cache-control": "public, max-age=31536000, immutable",
                },
            )

        # Return the cached image
        return Response(
            content=polling_state.cached_image,
            media_type=polling_state.cached_content_type,
            headers={
                "etag": current_etag,
                "cache-control": "public, max-age=31536000, immutable",
                "content-length": str(len(polling_state.cached_image)),
            },
        )

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time updates."""
        await manager.connect(websocket)

        try:
            # Send initial state
            await websocket.send_json({
                "type": "connected",
                "current_etag": polling_state.current_etag,
                "last_check": (
                    polling_state.last_check.isoformat()
                    if polling_state.last_check else None
                ),
                "js_hash": polling_state.js_hash,
            })

            # Send current sensor states
            if polling_state.sensor_states:
                await websocket.send_json({
                    "type": "sensors_state",
                    "sensors": list(polling_state.sensor_states.values()),
                    "timestamp": datetime.now().isoformat(),
                })

            # Keep connection alive
            while True:
                try:
                    # Wait for client messages
                    message = await websocket.receive()

                    # Check message type
                    if message["type"] == "websocket.disconnect":
                        break
                    if message["type"] == "websocket.receive":
                        if "text" in message:
                            data = message["text"]
                            # Handle ping with hash check
                            if data == "ping":
                                current_js_hash = get_js_hash(current_dir / "dist")
                                response = {"type": "pong", "js_hash": current_js_hash}
                                # Check if hash changed
                                if current_js_hash != polling_state.js_hash:
                                    logger.info(
                                        f"JavaScript hash changed: "
                                        f"{polling_state.js_hash} -> {current_js_hash}"
                                    )
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
    async def get_config() -> dict[str, Any]:
        """Return current configuration for debugging."""
        return {
            "image_url": IMAGE_URL,
            "server": f"{HOST}:{PORT}",
            "poll_interval": polling_state.poll_interval,
            "websocket_url": f"ws://{HOST}:{PORT}/ws",
        }

    @app.get("/api/status")
    async def get_status() -> dict[str, Any]:
        """Return current polling status."""
        return {
            "is_polling": polling_state.is_polling,
            "current_etag": polling_state.current_etag,
            "last_check": (
                polling_state.last_check.isoformat()
                if polling_state.last_check else None
            ),
            "connected_clients": len(manager.active_connections),
            "js_hash": polling_state.js_hash,
            "sensor_count": len(polling_state.sensor_states),
            "sensor_config_loaded": polling_state.sensor_config is not None,
        }

    @app.get("/api/sensors")
    async def get_sensors() -> dict[str, Any]:
        """Return current sensor states."""
        return {
            "sensors": list(polling_state.sensor_states.values()),
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/test-etag")
    async def test_etag(request: Request) -> Response:
        """Test endpoint to debug ETag behavior."""
        client_etag = request.headers.get("if-none-match")
        test_etag = '"test-etag-123"'

        if client_etag == test_etag:
            return Response(
                status_code=304,
                headers={
                    "etag": test_etag,
                    "cache-control": "private, max-age=0, must-revalidate",
                },
            )
        return Response(
            content=b"Test content",
            headers={
                "etag": test_etag,
                "cache-control": "private, max-age=0, must-revalidate",
                "content-type": "text/plain",
            },
        )

    # Test WebSocket endpoint
    @app.get("/test-ws")
    async def test_ws() -> FileResponse:
        """Serve WebSocket test page."""
        return FileResponse(current_dir / "test-ws.html")
