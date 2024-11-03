from langchain.tools import BaseTool
from pydantic import BaseModel, Field
import requests
from typing import Dict, Any
from enum import Enum
from neuron_server.config import config
from neuron_server.logger import logger
from neuron_server.tools.homeassistant_apy import HomeAssistantAPI, parse_sensor_state


class Room(Enum):
    LIVING_ROOM = "living_room"
    BACKYARD = "backyard"
    KITTY_CORNER = "kitty_corner"


rooms = {
    Room.LIVING_ROOM.value: [
        "sensor.weather_station_inside_temperature",
        "sensor.weather_station_humidity_indoor",
        "light.living_room",
    ],
    Room.BACKYARD.value: [
        "sensor.weather_station_feels_like",
        "sensor.weather_station_event_rain",
    ],
    Room.KITTY_CORNER.value: [
        "sensor.weather_station_temperature_2",
        "sensor.feeder_bot_food_level",
        "sensor.litter_robot_4_litter_level",
        "sensor.litter_robot_4_waste_drawer",
    ],
}


class HomeAssistantTool(BaseTool):
    name: str = "homeassistant"
    description: str = (
        "Tool to return the latest sensor states from Home Assistant for a given room. Room names: kitty_corner, living_room, backyard. "
    )
    api: HomeAssistantAPI

    def _run(self, room: Room):
        """
        Retrieves the latest sensor states for the specified room from Home Assistant.

        Args:
            room (Room): The room for which to retrieve sensor states.

        Returns:
            str: A formatted string containing the latest sensor states for the specified room.
        """
        room: str = room if isinstance(room, str) else room.value
        if room not in rooms:
            raise ValueError(f"Room {room} not found")
        entity_ids = rooms[room]
        states = [self.api.get_sensor_state(entity_id) for entity_id in entity_ids]
        data = "\n".join([parse_sensor_state(state) for state in states])
        return f"Use the following sensor data from {room} to answer the users question:\n{data}"


async def main():
    parser = argparse.ArgumentParser(description="Get temperature for a specific room")
    parser.add_argument("room", type=str, help="The room to get the temperature for")
    args = parser.parse_args()

    tool = HomeAssistantTool(api=HomeAssistantAPI(token=config.homeassistant.token))
    message = tool.run(args.room)
    print(message)


if __name__ == "__main__":
    import argparse
    import asyncio

    asyncio.run(main())
