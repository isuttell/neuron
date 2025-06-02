"""Data models for the dashboard viewer."""
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class SensorConfig(BaseModel):
    """Configuration for a single sensor."""
    entity_id: str = Field(description="HomeAssistant entity ID")
    friendly_name: str = Field(description="Display name for the sensor")
    description: str = Field(description="Description of what the sensor monitors")
    display_type: Literal["value", "state_icon", "state_text"] = Field(
        description="How to display the sensor"
    )
    unit_suffix: bool = Field(
        default=False, description="Whether to show unit of measurement"
    )
    icon_mapping: dict[str, str] = Field(
        description="Mapping of states to icon names, with 'default' as fallback"
    )


class DashboardSensorConfig(BaseModel):
    """Configuration for all dashboard sensors."""
    poll_interval: int = Field(default=60, description="Polling interval in seconds")
    sensors: list[SensorConfig] = Field(description="List of sensors to monitor")

    @classmethod
    def from_yaml(cls, file_path: Path) -> "DashboardSensorConfig":
        """Load configuration from YAML file."""
        with open(file_path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
