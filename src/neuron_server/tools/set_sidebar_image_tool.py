from langchain.tools import BaseTool
from typing import Literal, Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
from langchain_core.runnables import RunnableConfig
from neuron_server.cache import set_cache_key
from neuron_server.pubsub import pubsub
from neuron_server.controllers.events.app_events import SidebarImageEvent


class SetImageToolArgs(BaseModel):
    url: str = Field(description="The URL of the image")
    key: Literal["sidebar_image"] = Field(
        description="The key to update. The sidebar image is updated with the key 'sidebar_image'"
    )


class SetImageTool(BaseTool):
    name: str = "set_image"
    description: str = (
        """This tool allows you to update the image of the sidebar. Only use this tool after confirming with the user that they want to update the sidebar image."""
    )

    args_schema: Type[SetImageToolArgs] = SetImageToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, key: str, url: str) -> str:
        try:
            if key != "sidebar_image":
                raise ValueError(f"Invalid key: {key}")
            await set_cache_key(
                key,
                url,
            )
            if key == "sidebar_image":
                await pubsub.publish("app", SidebarImageEvent(url=url))
            logger.debug(f"Updated {key} image to {url}")
            return f"Updated {key} image to {url}"
        except Exception as e:
            logger.error(f"Failed to update sidebar: {e}")
            return f"Failed to update sidebar image: {e}"
