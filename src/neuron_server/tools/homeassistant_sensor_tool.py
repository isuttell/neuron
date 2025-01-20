from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from neuron_server.tools.homeassistant_api import HomeAssistantAPI, parse_sensor_state
from typing import Type, List


class HomeAssistantSensorToolArgs(BaseModel):
    entity_ids: List[str] = Field(
        description="""The entity ids to get the sensor states for. Use only entity_ids from the list of supported sensors.

Supported Sensors:
[
    {"entity_id": "sensor.weather_station_inside_temperature", "room": "Living Room", "description": "Temperature"},
    {"entity_id": "sensor.weather_station_humidity", "room": "Backyard", "description": "Humidity"},
    {"entity_id": "sensor.weather_station_dew_point", "room": "Backyard", "description": "Dew Point"},
    {"entity_id": "sensor.weather_station_solar_rad_lx", "room": "Backyard", "description": "Solar radiation lux"},
    {"entity_id": "light.living_room", "room": "Living Room", "description": "All lights in the living room"},
    {"entity_id": "media_player.sony_xbr_65a1e", "room": "Living Room", "description": "Living Room TV"},
    {"entity_id": "climate.t6_pro_z_wave_programmable_thermostat", "room": "Living Room", "description": "Living Room Thermostat"},
    {"entity_id": "sensor.weather_station_feels_like", "room": "Backyard", "description": "Feels like temperature"},
    {"entity_id": "sensor.weather_station_event_rain", "room": "Backyard", "description": "Rain right now"},
    {"entity_id": "sensor.weather_station_wind_average_10_minutes", "room": "Backyard", "description": "Wind speed"},
    {"entity_id": "sensor.weather_station_wind_direction_average_10_minutes", "room": "Backyard", "description": "Wind direction"},
    {"entity_id": "sensor.weather_station_yearly_rain", "room": "Backyard", "description": "Yearly rain"},
    {"entity_id": "sensor.weather_station_last_rain", "room": "Backyard", "description": "Last rain date"},
    {"entity_id": "sensor.weather_station_temperature_2", "room": "Kitty Corner", "description": "Temperature"},
    {"entity_id": "sensor.feeder_bot_food_level", "room": "Kitty Corner", "description": "Feederbot food level"},
    {"entity_id": "sensor.litter_robot_4_litter_level", "room": "Kitty Corner", "description": "Litterbot litter level"},
    {"entity_id": "sensor.litter_robot_4_waste_drawer", "room": "Kitty Corner", "description": "Litterbot waste drawer level, 0 is empty"},
    {"entity_id": "binary_sensor.motion_light_switch_motion_detection", "room": "Master Bathroom", "description": "Motion detection"},
    {"entity_id": "binary_sensor.in_wall_motion_switch_500s_motion_detection", "room": "Guest Bathroom", "description": "Motion detection"},
    {"entity_id": "light.office", "room": "Office", "description": "All lights in the office"},
    {"entity_id": "light.bedroom", "room": "Master Bedroom", "description": "All lights in the master bedroom"},
    {"entity_id": "sensor.weather_station_temperature_2", "room": "Master Bedroom", "description": "Temperature"},
    {"entity_id": "person.isaac_suttell", "description": "Isaac Suttell's Presence"},
    {"entity_id": "person.heidi_la_bash", "description": "Heidi La Bash's Presence"},
    {"entity_id": "sensor.date_time"},
    {"entity_id": "sensor.moon_phase"},
    {"entity_id": "calendar.home", "description": "Home Assistant Calendar, for things like Trash day, etc."},
]
        """.strip()
    )


class HomeAssistantSensorTool(BaseTool):
    name: str = "homeassistant_sensor"
    description: str = (
        """
Tool to return the latest sensor states from Home Assistant.
        """.strip()
    )
    args_schema: Type[HomeAssistantSensorToolArgs] = HomeAssistantSensorToolArgs

    api: HomeAssistantAPI

    def _run(self, entity_ids: List[str]):
        # Get all sensor states
        states = self.api.get_sensor_states()

        results = []
        for entity_id in entity_ids:
            # Find the sensor state for the entity_id and ensure it exists
            state = next(
                (state for state in states if state.entity_id == entity_id), None
            )
            if state is None:
                raise ValueError(f"Sensor with entity_id {entity_id} not found")
            results.append(parse_sensor_state(state))

        # Return just the request states
        return "\n".join(results)
