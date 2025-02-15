from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.tools.homeassistant_api import HomeAssistantAPI, parse_sensor_state


class HomeAssistantSensorToolArgs(BaseModel):
    entity_ids: list[str] = Field(
        description="""
The entity ids to get the sensor states for. Use only entity_ids from the list of
supported sensors.

Supported Sensors:

Living Room:
| Entity ID                                    | Description                      |
|---------------------------------------------|----------------------------------|
| sensor.weather_station_inside_temperature    | Temperature                      |
| light.living_room                           | All lights in the living room    |
| media_player.sony_xbr_65a1e                 | Living Room TV                   |
| climate.t6_pro_z_wave_programmable_therm    | Living Room Thermostat           |

Backyard:
| Entity ID                                    | Description                      |
|---------------------------------------------|----------------------------------|
| sensor.weather_station_humidity              | Humidity                         |
| sensor.weather_station_dew_point             | Dew Point                        |
| sensor.weather_station_solar_rad_lx          | Solar radiation lux              |
| sensor.weather_station_feels_like            | Feels like temperature           |
| sensor.weather_station_event_rain            | Rain right now                   |
| sensor.weather_station_wind_average_10_min   | Wind speed                       |
| sensor.weather_station_wind_direction_avg    | Wind direction                   |
| sensor.weather_station_yearly_rain           | Yearly rain                      |
| sensor.weather_station_last_rain             | Last rain date                   |

Kitty Corner:
| Entity ID                                    | Description                      |
|---------------------------------------------|----------------------------------|
| sensor.weather_station_temperature_2         | Temperature                      |
| sensor.feeder_bot_food_level                | Feederbot food level             |
| sensor.litter_robot_4_litter_level          | Litterbot litter level           |
| sensor.litter_robot_4_waste_drawer          | Litterbot waste drawer           |

Bathrooms:
| Entity ID                                    | Description                      |
|---------------------------------------------|----------------------------------|
| binary_sensor.motion_light_switch           | Motion detection (Master)        |
| binary_sensor.motion_switch_500s            | Motion detection (Guest)         |

Office:
| Entity ID                                    | Description                      |
|---------------------------------------------|----------------------------------|
| light.office                                | All lights in the office         |

Master Bedroom:
| Entity ID                                    | Description                      |
|---------------------------------------------|----------------------------------|
| light.bedroom                               | All lights in master bedroom     |
| sensor.weather_station_temperature_2         | Temperature                      |

Other:
| Entity ID                                    | Description                      |
|---------------------------------------------|----------------------------------|
| person.isaac_suttell                        | Isaac Suttell's Presence         |
| person.heidi_la_bash                        | Heidi La Bash's Presence         |
| sensor.date_time                            | Date and Time                    |
| sensor.moon_phase                           | Moon Phase                       |
| calendar.home                               | Home Assistant Calendar          |
""".strip()
    )


class HomeAssistantSensorTool(BaseTool):
    name: str = "homeassistant_sensor"
    description: str = """
Tool to return the latest sensor states from Home Assistant including the backyard
weather station.
        """.strip()
    args_schema: type[HomeAssistantSensorToolArgs] = HomeAssistantSensorToolArgs

    api: HomeAssistantAPI

    def _run(self, entity_ids: list[str]) -> str:
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
