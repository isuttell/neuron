import asyncio
import os
import shutil
from typing import Any
from uuid import uuid4

import aiohttp
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field, validator

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
    format: str | None = Field(
        default="mp3", description="Audio format for the output file"
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
            "Faster for snappy sarcastic delivery"
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
        description=("Voice pitch (0.5-2.0). Default: 1.0 - Standard GLaDOS pitch"),
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
    style_weight: float | None = Field(
        default=1.0,
        description=(
            "Style intensity (0.0-1.0). Default: 1.0 - Full GLaDOS voice style"
        ),
        ge=0.0,
        le=1.0,
    )
    split_interval: float | None = Field(
        default=0.6,
        description=(
            "Pause length between lines (0.0-2.0 seconds). Default: 0.6 - "
            "Longer pauses for dramatic effect"
        ),
        ge=0.0,
        le=2.0,
    )


# Maximum line length constant
MAX_LINE_LENGTH = 500


class GladosTTSToolArgs(BaseModel):
    lines: list[str] = Field(
        description=(
            "List of text lines to be spoken by GLaDOS. Each line must be less "
            "than 500 characters. Spell out percentages, numbers, decimals, and other "
            "special characters that should be pronounced out loud. 'AI' is hard to "
            "hear spoken out loud. Try to spell it out as 'A I'."
        )
    )

    name: str = Field(
        description=(
            "A unique informative display title for the audio file to be generated. "
            "Must be less than 256 characters. Should not include GLaDOS in the name."
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
            "Pause length between lines (0.0-2.0 seconds). Default: 0.6 - "
            "Longer pauses for dramatic effect"
        ),
        ge=0.0,
        le=2.0,
    )

    @validator("lines")
    @classmethod
    def validate_lines(cls, lines: list[str]) -> list[str]:
        if not lines:
            raise ValueError("At least one line must be provided")
        for line in lines:
            if len(line) > MAX_LINE_LENGTH:
                raise ValueError(
                    f"Line exceeds {MAX_LINE_LENGTH} characters: {line[:50]}..."
                )
        return lines


class GladosTTSTool(BaseTool):
    name: str = "glados_tts"
    description: str = """
This tool generates audio using GLaDOS's voice from Portal with customizable voice
parameters:

- noise: Voice consistency (0.0-1.0, default 0.4) - More mechanical for deadpan
- noise_w: Pronunciation clarity (0.0-1.0, default 0.8) - Keep clear pronunciation
- length: Speech pace (0.1-3.0, default 0.85) - Faster for snappy sarcastic
- sdp_ratio: Tempo variation (0.0-1.0, default 0.4) - Higher for dramatic pauses
- pitch_scale: Voice pitch (0.5-2.0, default 1.0) - Standard GLaDOS pitch
- intonation_scale: Expression range (0.5-2.0, default 1.2) - Enhanced sarcasm
- split_interval: Pause length (0.0-2.0s, default 0.6) - Longer dramatic pauses

Returns an audio tag to be shown to the user so they can play it.
""".strip()
    args_schema: type[GladosTTSToolArgs] = GladosTTSToolArgs

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    # ruff: noqa: PLR0913
    async def _arun(
        self,
        lines: list[str],
        name: str,
        config: RunnableConfig,
        noise: float | None = 0.4,
        noise_w: float | None = 0.8,
        length: float | None = 0.85,
        sdp_ratio: float | None = 0.4,
        pitch_scale: float | None = 1.0,
        intonation_scale: float | None = 1.2,
    ) -> str:
        try:
            logger.debug("Generating GLaDOS TTS audio...")
            working_dir = os.path.abspath(
                os.path.join(neuron_config.temp_folder, uuid4().hex)
            )
            os.makedirs(working_dir)
            audio_files: list[str] = []

            async with aiohttp.ClientSession() as session:
                # HTTP status codes
                http_ok = 200

                for index, line in enumerate(lines):
                    logger.debug(f"Generating GLaDOS audio for line: {line[:50]}...")

                    # Make request to GLaDOS API with voice parameters
                    async with session.post(
                        f"{neuron_config.glados_endpoint}/api/v1/tts",
                        json={
                            "content": line,
                            "style": "glados",
                            "format": "mp3",
                            "noise": noise,
                            "noise_w": noise_w,
                            "length": length,
                            "sdp_ratio": sdp_ratio,
                            "pitch_scale": pitch_scale,
                            "intonation_scale": intonation_scale,
                        },
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
                    temp_audio_path = os.path.join(working_dir, f"line-{index}.mp3")
                    audio_files.append(temp_audio_path)

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

            # Concatenate audio files if needed
            filename = safe_filename("glados_tts", name, "mp3")
            output = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )

            if len(audio_files) > 1:
                import subprocess

                from neuron_server.util.subprocess_runner import run_subprocess

                ffmpeg_command = [
                    "ffmpeg",
                    "-hide_banner",
                    "-nostats",
                    "-loglevel",
                    "error",
                    "-i",
                    "concat:" + "|".join(audio_files),
                    "-c",
                    "copy",
                    output,
                ]
                await run_subprocess(
                    ffmpeg_command,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            else:
                shutil.copy(audio_files[0], output)

            # Create media item
            url = neuron_config.static_content_url + "/" + filename
            create_params = MediaItemModel.CreateParams(
                url=url,
                media_type="audio",
                user_id=config["configurable"].get("user_id"),
                thread_id=config["configurable"].get("thread_id"),
                name=name,
                description="\n\n".join(lines),
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
