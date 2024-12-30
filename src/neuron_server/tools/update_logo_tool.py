from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
from langchain_core.runnables import RunnableConfig
from neuron_server.models.personality_model import PersonalityModel


class UpdateLogoToolArgs(BaseModel):
    logo_url: str = Field(
        description="The URL of the logo to update the personality with."
    )


class UpdateLogoTool(BaseTool):
    name: str = "update_logo"
    description: str = (
        """This tool allows you to update the logo of the active personality. Only use this tool after confirming with the user that they want to update the logo."""
    )

    args_schema: Type[UpdateLogoToolArgs] = UpdateLogoToolArgs

    def _run(self, logo_url: str, config: RunnableConfig) -> str:
        return asyncio.run(self._arun(logo_url, config))

    async def _arun(self, logo_url: str, config: RunnableConfig) -> str:
        personality_id = config["configurable"].get("personality_id")
        if not personality_id:
            raise ValueError("Personality ID is required")
        personality = await PersonalityModel.get(id=personality_id)
        if not personality:
            raise ValueError(f"Personality with ID {personality_id} not found")
        logger.debug(f"Updating logo for {personality.id} to {logo_url}...")
        personality.logo = logo_url
        await personality.save()
        return f"Updated logo for {personality.id}"
