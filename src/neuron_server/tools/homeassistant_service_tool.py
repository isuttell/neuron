from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.config import config
from neuron_server.logger import logger
from neuron_server.tools.homeassistant_api import HomeAssistantAPI, parse_sensor_state


class ServiceCallParameters(BaseModel):
    description: str = Field(description="The description of the service call")
    entity_id: str = Field(description="The entity ID to call the service on")
    domain: str = Field(description="The domain of the service to call")
    service: str = Field(description="The service to call")

    def __str__(self) -> str:
        return (
            f"{self.description}: entity_id={self.entity_id} "
            f"domain={self.domain} service={self.service}"
        )


calls = [
    ServiceCallParameters(
        entity_id="all",
        domain="light",
        service="turn_off",
        description="Turn off all lights",
    ),
    ServiceCallParameters(
        entity_id="light.office",
        domain="light",
        service="turn_off",
        description="Turn off the office lights",
    ),
    ServiceCallParameters(
        entity_id="light.office",
        domain="light",
        service="turn_on",
        description="Turn on the office lights",
    ),
    ServiceCallParameters(
        entity_id="light.living_room",
        domain="light",
        service="turn_off",
        description="Turn off the living room lights",
    ),
    ServiceCallParameters(
        entity_id="light.living_room",
        domain="light",
        service="turn_on",
        description="Turn on the living room lights",
    ),
    ServiceCallParameters(
        entity_id="",
        domain="light",
        service="turn_off",
        description="Turn off the master bedroom lights",
    ),
    ServiceCallParameters(
        entity_id="light.bedroom",
        domain="light",
        service="turn_on",
        description="Turn on the master bedroom lights",
    ),
]

available_calls = "\n".join([str(call) for call in calls])


class HomeAssistantServiceTool(BaseTool):
    name: str = "homeassistant_service"
    description: str = f"""\
Tool to call services on Home Assistant to control lights and other
devices. Only call this if the user explicitly asks you to control
something.

Available calls:
\"\"\"
{available_calls}
\"\"\"
"""
    api: HomeAssistantAPI

    def _run(self, entity_id: str, domain: str, service: str) -> str:
        try:
            states = self.api.call_service(domain, service, entity_id)
            return "\n".join([parse_sensor_state(state) for state in states])
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error calling service: {str(e)}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Get temperature for a specific room")
    parser.add_argument("room", type=str, help="The room to get the temperature for")
    tool = HomeAssistantServiceTool(
        api=HomeAssistantAPI(token=config.homeassistant.token)
    )
    message = tool._run("light.office", "light", "turn_on")
    print(message)


if __name__ == "__main__":
    import argparse
    import asyncio

    asyncio.run(main())
