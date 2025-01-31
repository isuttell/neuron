import asyncio
import os
import shutil

import aiofiles
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.slug import safe_filename

client = AsyncOpenAI(api_key=neuron_config.openai_api_key)


class WhisperSTTToolArgs(BaseModel):
    audio_path: str = Field(description="The path to the audio file to transcribe")
    name: str = Field(
        description="A unique display title for the audio file. Must be less than 256 characters"
    )


class WhisperSTTTool(BaseTool):
    name: str = "whisper_stt"
    description: str = (
        """
Transcribes speech from an audio file using OpenAI's Whisper model. Returns both the transcription and a link to the audio file.
""".strip()
    )
    args_schema: type[WhisperSTTToolArgs] = WhisperSTTToolArgs

    async def _arun(
        self,
        audio_path: str,
        name: str,
        config: RunnableConfig,
    ) -> str:
        try:
            # Copy audio file to static folder
            filename = safe_filename(
                "whisper_stt", name, os.path.splitext(audio_path)[1]
            )
            output = os.path.join(neuron_config.static_folder, filename)
            shutil.copy(audio_path, output)
            url = neuron_config.static_content_url + "/" + filename

            # Transcribe audio using Whisper
            logger.debug(f"Transcribing audio file: {audio_path}")
            async with aiofiles.open(audio_path, "rb") as f:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1", file=await f.read(), response_format="text"
                )

            # Create media item
            create_params = MediaItemModel.CreateParams(
                url=url,
                media_type="text",
                name=name,
                description=transcript,
                thread_id=config["configurable"].get("thread_id"),
                user_id=config["configurable"].get("user_id"),
            )
            media_item = await MediaItemModel.create(params=create_params)

            return f"""\
<audio id="{media_item.id}">
    <display><audio src="{url}"></audio></display>
    <transcription>{transcript}</transcription>
</audio>""".strip()

        except Exception as e:
            logger.error(e, exc_info=True)
            raise e

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))
