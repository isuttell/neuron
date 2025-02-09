import asyncio
import os
import shutil
from typing import Any
from uuid import uuid4

import aiohttp
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.slug import safe_filename


class GladosToolset:
    """Toolset for GLaDOS TTS functionality."""

    def __init__(self) -> None:
        self.tools = [GladosTTSTool()]


class TTSRequest(BaseModel):
    content: str = Field(description="Text content to convert to speech")
    style: str | None = Field(
        default="glados", description="Voice style to use for synthesis"
    )


class GladosTTSToolArgs(BaseModel):
    text: str = Field(description="The text to be spoken by GLaDOS.")

    name: str = Field(
        description=(
            "A unique display title for the audio file to be generated. "
            "Must be less than 256 characters"
        ),
    )


class GladosTTSTool(BaseTool):
    name: str = "glados_tts"
    description: str = """
This tool generates audio using GLaDOS's voice from Portal. Use this tool when you want
text to be spoken in GLaDOS's signature sarcastic and passive-aggressive style. This
returns an audio tag to be shown to the user so they can play it.
""".strip()
    args_schema: type[GladosTTSToolArgs] = GladosTTSToolArgs

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        text: str,
        name: str,
        config: RunnableConfig,
    ) -> str:
        try:
            logger.debug("Generating GLaDOS TTS audio...")
            working_dir = os.path.abspath(
                os.path.join(neuron_config.temp_folder, uuid4().hex)
            )
            os.makedirs(working_dir)

            # Make request to GLaDOS API
            async with aiohttp.ClientSession() as session:
                # HTTP status codes
                http_ok = 200

                async with session.post(
                    f"{neuron_config.glados_endpoint}/api/v1/tts",
                    json={"content": text, "style": "glados"},
                ) as response:
                    if response.status != http_ok:
                        error_text = await response.text()
                        raise ValueError(
                            "GLaDOS API returned status "
                            f"{response.status}: {error_text}"
                        )
                    data = await response.json()
                    audio_url = data["url"]

                # Download the audio file
                temp_audio_path = os.path.join(working_dir, "audio.mp3")
                async with session.get(audio_url) as response:
                    if response.status != http_ok:
                        raise ValueError(
                            f"Failed to download audio file: {response.status}"
                        )
                    with open(temp_audio_path, "wb") as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)

            # Move to static folder with safe filename
            filename = safe_filename("glados_tts", name, "mp3")
            output = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )
            shutil.copy(temp_audio_path, output)

            # Create media item
            url = neuron_config.static_content_url + "/" + filename
            create_params = MediaItemModel.CreateParams(
                url=url,
                media_type="audio",
                user_id=config["configurable"].get("user_id"),
                thread_id=config["configurable"].get("thread_id"),
                name=name,
                description=f"GLaDOS TTS: {text}",
            )
            media_item = await MediaItemModel.create(params=create_params)
            logger.info(f"Generated GLaDOS audio file saved to {output} <{url}>")

            return f"""\
<audio id="{media_item.id}">
    <display><audio src="{url}"></audio></display>
</audio>"""

        except Exception as e:
            logger.error(e, exc_info=True)
            raise
        finally:
            shutil.rmtree(working_dir)
