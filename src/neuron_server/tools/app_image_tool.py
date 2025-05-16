import asyncio
import logging
import os
import shutil
from typing import Any, Literal
from uuid import uuid4

import aiofiles
import aiohttp
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.cache import set_cache_key
from neuron_server.config import config as neuron_config
from neuron_server.controllers.events.app_events import SidebarImageEvent
from neuron_server.controllers.events.personality_events import GetPersonalityResponse
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.pubsub import pubsub

logger = logging.getLogger(__name__)


class AppImageToolArgs(BaseModel):
    url: str = Field(description="The URL of the image")
    key: Literal["sidebar_image", "dashboard_image", "personality_logo"] = Field(
        description=(
            "The key to update. The sidebar image is updated with the key "
            "'sidebar_image', the smart home dashboard image is updated with the key "
            "'dashboard_image', and the personality logo is updated with the key "
            "'personality_logo'"
        )
    )


class AppImageTool(BaseTool):
    name: str = "app_image"
    description: str = """This tool allows you to update the image of the sidebar,
    the smart home dashboard, or the active personality logo."""

    args_schema: type[AppImageToolArgs] = AppImageToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        key: str,
        url: str,
        config: RunnableConfig,
    ) -> str:
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
                        f"Invalid image URL. The image URL must end with "
                        f"{required_extension}"
                    )
                try:
                    # Generate a random session token
                    session_token = str(uuid4())
                    
                    # Set the cookie in the session
                    cookies = (
                        {"neuron_session": session_token} 
                        if neuron_config.static_require_auth else None
                    )
                    
                    async with (
                        aiohttp.ClientSession(cookies=cookies) as session,
                        session.get(url) as response,
                        aiofiles.open(tmp_upload_file, "wb") as file,
                    ):
                        response.raise_for_status()
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
                    personality_id=personality_id, key="logo", value=url
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
