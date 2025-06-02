"""Configuration management for the dashboard viewer using pydantic-settings."""
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with automatic loading from environment and .env file."""

    # Server configuration
    host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    port: int = Field(default=8000, description="Port to bind the server to")

    # Image configuration
    image_url: str = Field(
        default="https://ha.zaks.io/local/dashboard-art.png",
        description="URL of the dashboard image to display"
    )

    # Home Assistant configuration
    homeassistant_url: str = Field(
        default="https://ha.zaks.io",
        description="Home Assistant instance URL"
    )
    homeassistant_token: Optional[str] = Field(
        default=None,
        description="Home Assistant long-lived access token"
    )

    # Development settings
    dev_mode: bool = Field(
        default=False,
        description="Enable development mode with auto-reload"
    )

    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # Allow loading from .env file in current directory or parent
        env_nested_delimiter="__",
        case_sensitive=False,
        # Look for .env file in multiple locations
        extra="ignore"
    )

    @property
    def has_homeassistant_auth(self) -> bool:
        """Check if Home Assistant authentication is configured."""
        return bool(self.homeassistant_token)


# Create a singleton instance
settings = Settings()

# Path configuration (not from environment)
CURRENT_DIR = Path(__file__).parent.parent
DIST_DIR = CURRENT_DIR / "dist"
SENSOR_CONFIG_PATH = CURRENT_DIR / "dashboard_sensors.yaml"

# Export commonly used settings for backward compatibility
IMAGE_URL = settings.image_url
PORT = settings.port
HOST = settings.host
HOMEASSISTANT_URL = settings.homeassistant_url
HOMEASSISTANT_TOKEN = settings.homeassistant_token or ""
