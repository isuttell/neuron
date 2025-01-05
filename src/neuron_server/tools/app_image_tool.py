from langchain.tools import BaseTool
from typing import Literal, Type
from pydantic import BaseModel, Field
import asyncio
from neuron_server.cache import set_cache_key
from neuron_server.pubsub import pubsub
from neuron_server.controllers.events.app_events import SidebarImageEvent
import shutil
from neuron_server.config import config as neuron_config
import os
from uuid import uuid4
import aiohttp
import aiofiles
import logging
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.controllers.events.personality_events import GetPersonalityResponse


class AppImageToolArgs(BaseModel):
    url: str = Field(description="The URL of the image")
    key: Literal["sidebar_image", "dashboard_image", "personality_logo"] = Field(
        description="The key to update. The sidebar image is updated with the key 'sidebar_image', the smart home dashboard image is updated with the key 'dashboard_image', and the personality logo is updated with the key 'personality_logo'"
    )


class AppImageTool(BaseTool):
    name: str = "app_image"
    description: str = (
        """This tool allows you to update the image of the sidebar, the smart home dashboard, or the active personality logo."""
    )

    args_schema: Type[AppImageToolArgs] = AppImageToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, key: str, url: str, config: RunnableConfig) -> str:
        try:
            if key == "sidebar_image":
                await set_cache_key(
                    key,
                    url,
                )
                await pubsub.publish("app", SidebarImageEvent(url=url))
            elif key == "dashboard_image":
                tmp_upload_file = os.path.join(neuron_config.temp_folder, uuid4().hex)
                required_extension = neuron_config.tablet_image_filename.rsplit(".")[-1]
                if not url.endswith(required_extension):
                    # Ensure the image we're setting is the same type as the extension
                    # we're writing to so the mime types don't get confused. Basically
                    # We're trying to prevent a jpeg being saved as a.png.
                    raise Exception(
                        f"Invalid image URL. The image URL must end with {required_extension}"
                    )
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url) as response:
                            response.raise_for_status()

                            async with aiofiles.open(tmp_upload_file, "wb") as file:
                                await file.write(await response.content.read())

                    shutil.copy(tmp_upload_file, neuron_config.tablet_image_filename)
                    logger.debug(
                        f"Copied {url} to {neuron_config.tablet_image_filename}"
                    )
                finally:
                    if os.path.exists(tmp_upload_file):
                        os.remove(tmp_upload_file)
            elif key == "personality_logo":
                personality_id = config["configurable"].get("personality_id")
                if not personality_id:
                    raise ValueError("Personality ID is required")
                personality = await PersonalityModel.set(
                    id=personality_id, key="logo", value=url
                )
                await pubsub.publish(
                    "personality", GetPersonalityResponse(personality=personality)
                )
            else:
                raise ValueError(f"Invalid key: {key}")
            logger.debug(f"Updated {key} image to {url}")
            return f"Updated {key} image to {url}"
        except Exception as e:
            logger.error(f"Failed to update {key} image: {e}", exc_info=True)
            raise
