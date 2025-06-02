"""Configuration management for the dashboard viewer."""
import os
from pathlib import Path

# Environment configuration
IMAGE_URL = os.getenv("IMAGE_URL", "https://ha.zaks.io/local/dashboard-art.png")
PORT = int(os.getenv("PORT", "8000"))
HOST = os.getenv("HOST", "0.0.0.0")
HOMEASSISTANT_URL = os.getenv("HOMEASSISTANT_URL", "https://ha.zaks.io")
HOMEASSISTANT_TOKEN = os.getenv("HOMEASSISTANT_TOKEN", "")

# Paths
CURRENT_DIR = Path(__file__).parent.parent
DIST_DIR = CURRENT_DIR / "dist"
SENSOR_CONFIG_PATH = CURRENT_DIR / "dashboard_sensors.yaml"
