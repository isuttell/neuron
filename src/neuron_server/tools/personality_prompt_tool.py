from langchain.tools import BaseTool
from typing import Literal, Type
from pydantic import BaseModel, Field
import asyncio
from neuron_server.pubsub import pubsub
import logging
from langchain_core.runnables import RunnableConfig
from neuron_server.controllers.events.prompt_events import GetPromptResponse
from neuron_server.models.prompt_model import PromptModel

logger = logging.getLogger(__name__)


class PersonalityPromptToollArgs(BaseModel):
    name: str = Field(description="A short informative title for the prompt")
    prompt: str = Field(
        description="The reusable prompt for later use. It should be in second person explaining to an assistant what it needs to do."
    )


class PersonalityPromptTool(BaseTool):
    name: str = "personality_prompt"
    description: str = (
        """This tools lets you save a prompt for the active personality making it available to the user to use at any time. Only use this tool when the user has explictly asked for it."""
    )

    args_schema: Type[PersonalityPromptToollArgs] = PersonalityPromptToollArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, name: str, prompt: str, config: RunnableConfig) -> str:
        try:
            personality_id = config["configurable"].get("personality_id")
            if not personality_id:
                raise ValueError("Personality ID is required")
            model = await PromptModel.create(
                name=name,
                text=prompt,
                personality_id=personality_id,
            )
            await pubsub.publish("app", GetPromptResponse(prompt=model))
            logger.debug(f"Prompt saved: {model.name}")
            return f"Prompt saved: {model.name}"
        except Exception as e:
            logger.error(f"Failed to save prompt: {e}", exc_info=True)
            raise
