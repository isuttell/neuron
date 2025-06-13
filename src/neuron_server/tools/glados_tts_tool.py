import asyncio
import os

import aiohttp
from aiohttp import ClientConnectorError
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


class GladosTTSToolArgs(BaseModel):
    content: str = Field(
        description=(
            "Text content to convert to speech. Spell out percentages, numbers, "
            "decimals, and other special characters that should be pronounced out loud "
            "for clarity. For example, 'AI' is hard to hear spoken out loud with this "
            "tool. Try to spell it out as 'A I' or use the full words."
        )
    )

    name: str = Field(
        description=(
            "A unique informative display title for the audio file to be generated. "
            "Must be less than 256 characters. Should not include GLaDOS in the name. "
            "Show to the user preceeding the subtitles to be spoken. Keep in character "
        ),
    )

    noise: float | None = Field(
        default=0.4,
        description=(
            "Voice consistency (0.0-1.0). Default: 0.4 - "
            "More mechanical for deadpan delivery"
        ),
        ge=0.0,
        le=1.0,
    )
    noise_w: float | None = Field(
        default=0.8,
        description=(
            "Pronunciation clarity (0.0-1.0). Default: 0.8 - Keep clear pronunciation"
        ),
        ge=0.0,
        le=1.0,
    )
    length: float | None = Field(
        default=0.85,
        description=(
            "Speech pace (0.1-3.0). Default: 0.85 - "
            "0.8 is faster for snappy sarcastic delivery"
        ),
        ge=0.1,
        le=3.0,
    )
    sdp_ratio: float | None = Field(
        default=0.4,
        description=(
            "Tempo variation (0.0-1.0). Default: 0.4 - Higher for dramatic pauses"
        ),
        ge=0.0,
        le=1.0,
    )
    pitch_scale: float | None = Field(
        default=1.0,
        description=(
            "Voice pitch (0.5-2.0). Default: 1.0 - Standard GLaDOS pitch. "
            "Highly distorts voice at extremes. Make small adjustments."
        ),
        ge=0.5,
        le=2.0,
    )
    intonation_scale: float | None = Field(
        default=1.2,
        description=(
            "Expression range (0.5-2.0). Default: 1.2 - Enhanced for sarcastic emphasis"
        ),
        ge=0.5,
        le=2.0,
    )
    split_interval: float | None = Field(
        default=0.6,
        description=(
            "Pause length between lines separated by line breaks' (0.0-2.0 seconds). "
            "Default: 0.6"
        ),
        ge=0.0,
        le=2.0,
    )


class GladosTTSTool(BaseTool):
    name: str = "glados_tts"
    description: str = """
This tool converts text to speech in the style of GLaDOS from Portal.

Returns an audio tag to be shown to the user so they can play it.
""".strip()
    args_schema: type[GladosTTSToolArgs] = GladosTTSToolArgs
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args: tuple,  # Removed Any
        **kwargs: dict[str, any],  # Changed Any to any
    ) -> str:
        # Note: Might need `dict[str, Any]` if `any` isn't recognized by type checker
        # Keeping `any` for now as `Any` import was removed.
        return asyncio.run(self._arun(*args, **kwargs))

    # ruff: noqa: PLR0913
    async def _arun(  # noqa: C901 Too complex
        self,
        content: str,
        name: str,
        config: RunnableConfig,
        noise: float | None = 0.4,
        noise_w: float | None = 0.8,
        length: float | None = 0.85,
        sdp_ratio: float | None = 0.4,
        pitch_scale: float | None = 1.0,
        intonation_scale: float | None = 1.2,
        split_interval: float | None = 0.6,
        output_format: str = "wav",
    ) -> tuple[str, dict]:
        output_path = None
        try:
            logger.debug("Generating GLaDOS TTS audio...")

            # Prepare the final destination path
            filename = safe_filename("glados_tts", name, output_format)
            output_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )

            # Make the request and download directly to the final location
            async with aiohttp.ClientSession() as session:
                http_ok = 200
                logger.debug(f"Generating GLaDOS audio for content: {content[:100]}...")
                try:
                    # Make single request to GLaDOS API with voice parameters
                    async with session.post(
                        f"{neuron_config.glados_endpoint}/api/v1/tts",
                        json={
                            "content": content.replace("%", " percent"),
                            "style": "glados",
                            "format": output_format,
                            "noise": noise,
                            "noise_w": noise_w,
                            "length": length,
                            "sdp_ratio": sdp_ratio,
                            "pitch_scale": pitch_scale,
                            "intonation_scale": intonation_scale,
                            "split_interval": split_interval,
                        },
                    ) as response:
                        if response.status != http_ok:
                            error_text = await response.text()
                            raise ValueError(
                                "GLaDOS API returned status "
                                f"{response.status}: {error_text}"
                            )
                        data = await response.json()

                        # Download the audio file directly to the final destination
                        # ONLY if audio_url is valid
                        if data["url"]:
                            async with session.get(data["url"]) as response_download:
                                if response_download.status != http_ok:
                                    raise ValueError(
                                        "Failed to download audio file: "
                                        f"{response_download.status}"
                                    )
                                with open(output_path, "wb") as f:
                                    while True:
                                        chunk = await response_download.content.read(
                                            8192
                                        )
                                        if not chunk:
                                            break
                                        f.write(chunk)

                except ClientConnectorError as e:
                    logger.error("GLaDOS TTS server is unavailable.")
                    # Raise the specific exception
                    raise Exception(
                        "The GLaDOS TTS server is currently unavailable. "
                        "Please ensure it is running."
                    ) from e

            url = neuron_config.static_content_url + "/" + filename
            if os.path.exists(output_path):
                create_params = MediaItemModel.CreateParams(
                    url=url,
                    media_type="tts",
                    user_id=config["configurable"].get("user_id"),
                    thread_id=config["configurable"].get("thread_id"),
                    name=name,
                    description=content,
                )
                media_item = await MediaItemModel.create(params=create_params)
                logger.info(
                    f"Generated GLaDOS audio file saved to {output_path} <{url}>"
                )

                # Prepare artifact for UI using typed models
                from neuron_server.tools.artifact_types import (
                    ToolArtifactMetadata,
                    ToolMediaArtifact,
                    ToolMediaItem,
                )
                from neuron_server.util.media_utilities import get_media_duration

                # Get actual duration from the generated file
                duration = await get_media_duration(output_path)

                metadata = ToolArtifactMetadata(
                    model="glados-tts",
                    prompt=name,
                    duration=duration,
                    output_format=output_format,
                )

                artifact_item = ToolMediaItem(
                    id=str(media_item.id),
                    url=url,
                    caption=name,
                    description=content,
                    metadata=metadata,
                )

                artifact = ToolMediaArtifact(media_type="audio", items=[artifact_item])

                return artifact.to_xml(), [artifact.model_dump()]
            # Handle case where audio URL was not present or download failed silently
            # before file creation but after API call succeeded
            raise Exception("Failed to generate or download GLaDOS audio file.")

        except Exception as e:
            # Handle other general exceptions
            logger.error(f"Error during GLaDOS TTS generation: {e}", exc_info=True)
            # Remove the output file if it exists to avoid leaving partial files
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError as remove_error:
                    logger.error(
                        f"Error removing partial file {output_path}: {remove_error}"
                    )
            raise  # Re-raise other exceptions
