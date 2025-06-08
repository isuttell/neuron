import asyncio
import os
import random
import re
import subprocess
from typing import Any
from uuid import uuid4

import aiofiles
import aiohttp
import replicate
import replicate.helpers
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.util.subprocess_runner import run_subprocess


async def join_video_audio(
    video_file: str, audio_file: str, output_file: str
) -> tuple[str | None, str | None]:
    """Join video and audio files using ffmpeg."""
    logger.debug(f"Joining video {video_file} with audio {audio_file} to {output_file}")
    process: subprocess.CompletedProcess[str] = await run_subprocess(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-loglevel",
            "error",
            "-y",
            "-i",
            video_file,
            "-i",
            audio_file,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            "-f",
            "mp4",
            output_file,
        ],
        text=True,
        stdout=None,
        stderr=None,
    )
    return (
        process.stdout,
        process.stderr,
    )


class ReplicateSoundEffectGenerationToolArgs(BaseModel):
    video_url: str = Field(description="The URL of the video to add the audio to")
    prompt: str = Field(
        description="""
Text prompt to guide audio generation. Give technical details about the sound you want
to generate.

Example prompts:
- Blackbird song, summer, dusk in the forest
- Motorcycle driving by
"""
    )
    seed: int | None = Field(description="Random seed for audio generation", default=-1)
    steps: int | None = Field(description="Number of inference steps", default=100)
    cfg_scale: float | None = Field(
        description="Classifier-free guidance scale", default=6.0
    )
    slug: str = Field(
        description=(
            "A unique identifier. Must be all lower case with no special characters "
            "or spaces. Use dashes for spaces. Keep it short and descriptive. "
            "Must be less than 256 characters"
        )
    )
    seconds_total: int | None = Field(
        description="Total duration in seconds", default=6
    )
    negative_prompt: str | None = Field(
        description="Text prompt to avoid in generation"
    )


class ReplicateSoundEffectGenerationTool(BaseTool):
    name: str = "replicate_sound_effect_generation"
    description: str = """
This tool generates short audio samples, sound effects, and production elements using
text prompts with the stackadoc/stable-audio-open-1.0 model. Ideal for:
- Creating drum beats and instrument riffs
- Generating ambient sounds and audio samples
- Adding sound effects and jingles to videos (note: audio is not synced)
"""

    args_schema: type[ReplicateSoundEffectGenerationToolArgs] = (
        ReplicateSoundEffectGenerationToolArgs
    )

    ref: str = (
        "stackadoc/stable-audio-open-1.0:"
        "9aff84a639f96d0f7e6081cdea002d15133d0043727f849c40abdd166b7c75a8"
    )

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0913
        self,
        video_url: str,
        prompt: str,
        slug: str,
        seed: int = -1,
        steps: int = 25,
        cfg_scale: float = 4.5,
        sigma_max: int = 500,
        sigma_min: float = 0.03,
        batch_size: int = 1,
        sampler_type: str = "dpmpp-3m-sde",
        seconds_start: int = 0,
        seconds_total: int = 6,
        negative_prompt: str = "",
        init_noise_level: float = 1,
    ) -> str:
        logger.debug(f"Generating audio with prompt: {prompt}")

        tmp_files: list[str] = []
        try:
            tmp_video_file = os.path.abspath(
                os.path.join(neuron_config.temp_folder, f"{uuid4().hex}.mp4")
            )
            tmp_files.append(tmp_video_file)

            # Generate proper signed session cookie for internal tool access
            cookies = None
            if neuron_config.static_require_auth:
                from neuron_server.controllers.csrf import create_session_cookie

                session_cookie, _ = create_session_cookie("system", include_csrf=False)
                cookies = {"neuron_session": session_cookie}

            async with (
                aiohttp.ClientSession(cookies=cookies) as session,
                session.get(video_url) as response,
                aiofiles.open(tmp_video_file, "wb") as file,
            ):
                response.raise_for_status()
                await file.write(await response.content.read())

            # Ensure a seed is set for reproducible results at a later date
            input_args = {
                "seed": (
                    seed
                    if seed is not None and seed != -1
                    else random.randint(0, 2147483647)
                ),
                "steps": steps,
                "prompt": prompt,
                "cfg_scale": cfg_scale,
                "sigma_max": sigma_max,
                "sigma_min": sigma_min,
                "batch_size": batch_size,
                "sampler_type": sampler_type,
                "seconds_start": seconds_start,
                "seconds_total": seconds_total,
                "negative_prompt": negative_prompt,
                "init_noise_level": init_noise_level,
            }

            for key, value in input_args.items():
                logger.debug(f"{key}={value}")

            output: replicate.helpers.FileOutput = await replicate.async_run(
                self.ref,
                input=input_args,
            )
            logger.debug(f"Generated <{output.url}>")

            tmp_audio_file = os.path.abspath(
                os.path.join(neuron_config.temp_folder, f"{uuid4().hex}.wav")
            )
            tmp_files.append(tmp_audio_file)
            async with aiofiles.open(tmp_audio_file, "wb") as file:
                async for chunk in output:
                    await file.write(chunk)

            # Create safe filename from slug
            safe_name = re.sub(r"[^a-z0-9-_]", "", slug)[:255].lower().replace(" ", "-")
            output_filename = (
                f"{self.ref.split(':')[0].replace('/', '_')}_"
                f"{uuid4().hex[:8]}_{safe_name}.mp4"
            )
            output_file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, output_filename)
            )

            await join_video_audio(tmp_video_file, tmp_audio_file, output_file_path)

            url = f"{neuron_config.static_content_url}/{output_filename}"
            logger.debug(f"Saved generated video to {output_file_path} <{url}>")
            return f'<video src="{url}"></video>\nFilename: {output_file_path}'
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
        finally:
            for file in tmp_files:
                if os.path.exists(file):
                    os.remove(file)
