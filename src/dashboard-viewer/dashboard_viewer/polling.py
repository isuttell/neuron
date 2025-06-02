"""Polling state and background tasks."""
import asyncio
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import httpx

from .config import HOMEASSISTANT_TOKEN, HOMEASSISTANT_URL, IMAGE_URL
from .models import DashboardSensorConfig

if TYPE_CHECKING:
    from .websocket import ConnectionManager

logger = logging.getLogger(__name__)


class PollingState:
    """Manages polling state for images and sensors."""

    def __init__(self) -> None:
        self.current_etag: Optional[str] = None
        self.last_check: Optional[datetime] = None
        self.poll_interval: int = 10  # seconds
        self.is_polling: bool = False
        # Image cache
        self.cached_image: Optional[bytes] = None
        self.cached_content_type: Optional[str] = None
        self.cached_headers: dict[str, str] = {}
        # JavaScript hash for auto-refresh
        self.js_hash: Optional[str] = None
        # Sensor state
        self.sensor_config: Optional[DashboardSensorConfig] = None
        self.sensor_states: dict[str, dict[str, Any]] = {}
        self.sensor_poll_task: Optional[asyncio.Task] = None


def get_js_hash(dist_dir: Path) -> Optional[str]:
    """Extract the JavaScript hash from index.html for auto-refresh detection."""
    try:
        index_path = dist_dir / "index.html"
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


async def fetch_and_cache_image(
    client: httpx.AsyncClient, polling_state: PollingState
) -> bool:
    """Fetch the image and cache it in memory."""
    try:
        logger.info(f"Fetching image from: {IMAGE_URL}")
        response = await client.get(IMAGE_URL)

        if response.status_code == 200:
            # Cache the image data
            polling_state.cached_image = response.content
            polling_state.cached_content_type = response.headers.get(
                "content-type", "image/png"
            )

            # Cache relevant headers
            polling_state.cached_headers = {}
            for header in ["etag", "last-modified"]:
                if header in response.headers:
                    polling_state.cached_headers[header] = response.headers[header]

            logger.info(
                f"Cached image: {len(polling_state.cached_image)} bytes, "
                f"ETag: {polling_state.cached_headers.get('etag')}"
            )
            return True
        logger.error(f"Failed to fetch image: {response.status_code}")
        return False
    except Exception as e:
        logger.error(f"Error fetching image: {e}")
        return False


async def fetch_sensor_states(
    client: httpx.AsyncClient, polling_state: PollingState
) -> dict[str, Any]:
    """Fetch sensor states from HomeAssistant."""
    if not HOMEASSISTANT_TOKEN:
        logger.warning("HOMEASSISTANT_TOKEN not configured, skipping sensor polling")
        return {}

    if not polling_state.sensor_config:
        return {}

    try:
        headers = {
            "Authorization": f"Bearer {HOMEASSISTANT_TOKEN}",
            "Content-Type": "application/json",
        }

        # Get all states from HomeAssistant
        response = await client.get(f"{HOMEASSISTANT_URL}/api/states", headers=headers)

        if response.status_code == 200:
            all_states = response.json()

            # Create a map of entity_id to state
            state_map = {state["entity_id"]: state for state in all_states}

            # Process configured sensors
            sensor_updates = []
            for sensor_config in polling_state.sensor_config.sensors:
                state = state_map.get(sensor_config.entity_id)
                if not state:
                    logger.warning(
                        f"Sensor {sensor_config.entity_id} not found in HomeAssistant"
                    )
                    continue

                # Get icon based on state
                icon = sensor_config.icon_mapping.get(
                    state["state"],
                    sensor_config.icon_mapping.get("default", "help-circle")
                )

                # Format value based on display type
                value = state["state"]
                if sensor_config.unit_suffix:
                    unit = state.get("attributes", {}).get("unit_of_measurement", "")
                    if unit:
                        value = f"{value} {unit}"

                sensor_data = {
                    "entity_id": sensor_config.entity_id,
                    "friendly_name": sensor_config.friendly_name,
                    "description": sensor_config.description,
                    "value": value,
                    "state": state["state"],
                    "icon": icon,
                    "display_type": sensor_config.display_type,
                    "attributes": state.get("attributes", {}),
                    "last_updated": state.get("last_updated", ""),
                }

                # Check if state changed
                old_state = polling_state.sensor_states.get(sensor_config.entity_id, {})
                if (
                    old_state.get("value") != sensor_data["value"]
                    or old_state.get("state") != sensor_data["state"]
                    or old_state.get("icon") != sensor_data["icon"]
                ):
                    sensor_updates.append(sensor_data)

                # Update cached state
                polling_state.sensor_states[sensor_config.entity_id] = sensor_data

            return {"all_sensors": list(polling_state.sensor_states.values()),
                    "updates": sensor_updates}
        logger.error(f"Failed to fetch sensor states: {response.status_code}")
        return {}

    except Exception as e:
        logger.error(f"Error fetching sensor states: {e}")
        return {}


async def poll_for_sensors(
    client: httpx.AsyncClient,
    polling_state: PollingState,
    manager: "ConnectionManager"
) -> None:
    """Background task to poll for sensor changes."""
    if not polling_state.sensor_config:
        logger.warning("No sensor configuration loaded")
        return

    while polling_state.is_polling:
        try:
            result = await fetch_sensor_states(client, polling_state)

            if result.get("updates"):
                # Notify all connected clients of sensor updates
                await manager.broadcast({
                    "type": "sensors_update",
                    "sensors": result["all_sensors"],
                    "timestamp": datetime.now().isoformat(),
                })
                logger.info(f"Sent sensor updates: {len(result['updates'])} changed")

        except Exception as e:
            logger.error(f"Error polling sensors: {e}")

        # Wait before next check
        await asyncio.sleep(polling_state.sensor_config.poll_interval)


async def poll_for_changes(
    client: httpx.AsyncClient,
    polling_state: PollingState,
    manager: "ConnectionManager",
) -> None:
    """Background task to poll for image changes."""
    # Fetch initial image on startup
    if not polling_state.cached_image:
        await fetch_and_cache_image(client, polling_state)

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
                    if await fetch_and_cache_image(client, polling_state):
                        # Notify all connected clients
                        await manager.broadcast({
                            "type": "image_changed",
                            "etag": new_etag,
                            "timestamp": polling_state.last_check.isoformat(),
                        })

        except Exception as e:
            logger.error(f"Error polling for changes: {e}")
            # Notify clients of error
            await manager.broadcast({
                "type": "error",
                "message": f"Failed to check for updates: {str(e)}",
                "timestamp": datetime.now().isoformat(),
            })

        # Wait before next check
        await asyncio.sleep(polling_state.poll_interval)
