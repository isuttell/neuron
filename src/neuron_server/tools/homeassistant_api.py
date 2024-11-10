from pydantic import BaseModel, Field
import requests
from typing import Dict, Any, List
from neuron_server.logger import logger


class State(BaseModel):
    entity_id: str
    state: str
    attributes: Dict[str, Any]
    last_changed: str


class SensorState(State):
    last_reported: str
    last_updated: str
    context: Dict[str, Any]


class HomeAssistantAPI(BaseModel):
    server: str = Field(
        description="The server URL for Home Assistant", default="https://ha.zaks.io"
    )
    token: str = Field(description="The API key for Home Assistant")

    def get_sensor_state(self, entity_id: str) -> SensorState:
        url = f"{self.server}/api/states/{entity_id}"
        logger.debug(f"GET {url}")
        res = requests.get(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        res.raise_for_status()
        return SensorState(**res.json())

    def get_sensor_states(self) -> List[SensorState]:
        url = f"{self.server}/api/states"
        logger.debug(f"GET {url}")
        res = requests.get(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
        )
        res.raise_for_status()
        return [SensorState(**state) for state in res.json()]

    def call_service(self, domain: str, service: str, entity_id: str) -> List[State]:
        url = f"{self.server}/api/services/{domain}/{service}"
        logger.debug(f"POST {url}")
        res = requests.post(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            json={"entity_id": entity_id},
        )
        res.raise_for_status()
        logger.debug(f"Response: {res.text}")
        return [State(**state) for state in res.json()]


def parse_sensor_state(state: State) -> str:
    unit_of_measurement = state.attributes.get("unit_of_measurement", "")
    friendly_name = state.attributes.get("friendly_name", None)
    last_updated = state.attributes.get("last_updated", None)
    measurement = f"{state.state} {unit_of_measurement}".strip()
    name = f"{friendly_name} ({state.entity_id})" if friendly_name else state.entity_id
    message = f'The {name} sensor is reporting "{measurement}"'.strip()
    if last_updated:
        message += f" (Last updated: {last_updated})"
    return message
