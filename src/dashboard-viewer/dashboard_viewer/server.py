"""Main server module for the dashboard viewer."""
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import (
    BASE_PATH,
    CURRENT_DIR,
    DIST_DIR,
    HOMEASSISTANT_TOKEN,
    HOST,
    IMAGE_URL,
    PORT,
    SENSOR_CONFIG_PATH,
)
from .models import DashboardSensorConfig
from .polling import (
    PollingState,
    fetch_sensor_states,
    get_js_hash,
    poll_for_changes,
    poll_for_sensors,
)
from .routes import setup_routes
from .websocket import ConnectionManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress verbose httpcore logs
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# HTTP client for proxying requests
client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

# Initialize managers
manager = ConnectionManager()
polling_state = PollingState()


@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[misc]
    """Manage application lifespan."""
    # Startup
    logger.info("Dashboard Viewer starting...")
    logger.info(f"Image URL: {IMAGE_URL}")
    logger.info(f"Serving on: {HOST}:{PORT}")
    logger.info(f"Static files from: {DIST_DIR}")

    if not DIST_DIR.exists():
        logger.warning(f"Static files directory not found: {DIST_DIR}")
        logger.warning("Run 'npm run build' to build the frontend")

    # Initialize JavaScript hash for auto-refresh
    polling_state.js_hash = get_js_hash(DIST_DIR)
    if polling_state.js_hash:
        logger.info(f"JavaScript hash: {polling_state.js_hash}")
    else:
        logger.warning("Could not extract JavaScript hash")

    # Load sensor configuration
    if SENSOR_CONFIG_PATH.exists():
        try:
            polling_state.sensor_config = DashboardSensorConfig.from_yaml(
                SENSOR_CONFIG_PATH
            )
            logger.info(
                f"Loaded sensor config with "
                f"{len(polling_state.sensor_config.sensors)} sensors"
            )

            # Fetch initial sensor states
            await fetch_sensor_states(client, polling_state)
        except Exception as e:
            logger.error(f"Failed to load sensor config: {e}")
    else:
        logger.warning(f"Sensor config not found at {SENSOR_CONFIG_PATH}")

    # Start polling tasks
    polling_state.is_polling = True
    poll_task = asyncio.create_task(poll_for_changes(client, polling_state, manager))

    # Start sensor polling if configured
    if polling_state.sensor_config and HOMEASSISTANT_TOKEN:
        polling_state.sensor_poll_task = asyncio.create_task(
            poll_for_sensors(client, polling_state, manager)
        )
        logger.info("Started sensor polling")

    yield

    # Shutdown
    polling_state.is_polling = False
    await poll_task
    if polling_state.sensor_poll_task:
        await polling_state.sensor_poll_task
    await client.aclose()


# Create FastAPI app with optional root_path for subpath deployment
app = FastAPI(
    title="Dashboard Viewer",
    lifespan=lifespan,
    root_path=BASE_PATH if BASE_PATH else None
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up routes
setup_routes(app, client, polling_state, manager, CURRENT_DIR)

# Serve static files - must be last to avoid catching other routes
if DIST_DIR.exists():
    # Serve the built dashboard viewer
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="static")
else:
    # Development fallback
    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "error": "Frontend not built",
            "message": "Run 'npm run build' to build the dashboard viewer",
            "image_url": IMAGE_URL,
            "vite_base_path": BASE_PATH,
        }

    @app.head("/")
    async def root_head_fallback():  # type: ignore[misc]
        """HEAD endpoint for health checks when frontend is not built."""
        from fastapi import Response
        return Response(
            status_code=200,
            headers={
                "content-type": "application/json",
                "cache-control": "no-cache, no-store, must-revalidate",
            }
        )


def main() -> None:
    """Main entry point for the dashboard viewer server."""
    import uvicorn

    from .config import settings

    uvicorn.run(
        "dashboard_viewer.server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.dev_mode,
    )


if __name__ == "__main__":
    main()
