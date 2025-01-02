from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import replicate.helpers
from neuron_server.logger import logger
import asyncio
import replicate
import aiohttp
from uuid import uuid4
import os
from neuron_server.config import config as neuron_config
import aiofiles
import subprocess
import re


def join_video_audio(video_file: str, audio_file: str, output_file: str):
    logger.debug(f"Joining video {video_file} with audio {audio_file} to {output_file}")
    process = subprocess.run(
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
        check=True,
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
Text prompt to guide audio generation. Give technical details about the sound you want to generate.

Example prompts:
- Blackbird song, summer, dusk in the forest
- Motorcycle driving by
                    """.strip()
    )
    seed: Optional[int] = Field(
        description="Random seed for audio generation", default=-1
    )
    steps: Optional[int] = Field(description="Number of inference steps", default=100)
    cfg_scale: Optional[float] = Field(
        description="Classifier-free guidance scale", default=6.0
    )
    slug: str = Field(
        description="A unique identifier. Must be all lower case with no special characters or spaces. Use dashes for spaces. Keep it short and descriptive. Must be less than 256 characters",
    )
    # sigma_max: Optional[int] = Field(description="Maximum noise level", default=500)
    # sigma_min: Optional[float] = Field(description="Minimum noise level", default=0.03)
    # batch_size: Optional[int] = Field(
    #     description="Number of samples to generate", default=1
    # )
    # sampler_type: Optional[str] = Field(
    #     description="Type of sampler to use", default="dpmpp-3m-sde"
    # )
    # seconds_start: Optional[int] = Field(description="Start time in seconds")
    seconds_total: Optional[int] = Field(
        description="Total duration in seconds", default=6
    )
    negative_prompt: Optional[str] = Field(
        description="Text prompt to avoid in generation"
    )
    # init_noise_level: Optional[float] = Field(
    #     description="Initial noise level", default=1.0
    # )


class ReplicateSoundEffectGenerationTool(BaseTool):
    name: str = "replicate_sound_effect_generation"
    description: str = (
        """
This tool is optimized for generating short audio samples, sound effects, and production elements using text prompts using the model stackadoc/stable-audio-open-1.0. Ideal for creating drum beats, instrument riffs, ambient sounds, and other audio samples. Use this to add sound effects and other jingles to a video. Audio is not synced to the video.
""".strip()
    )

    args_schema: Type[ReplicateSoundEffectGenerationToolArgs] = (
        ReplicateSoundEffectGenerationToolArgs
    )

    ref: str = (
        "stackadoc/stable-audio-open-1.0:9aff84a639f96d0f7e6081cdea002d15133d0043727f849c40abdd166b7c75a8"
    )

    def _run(
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
        seconds_total: int = 8,
        negative_prompt: str = "",
        init_noise_level: float = 1,
    ) -> str:
        return asyncio.run(
            self._arun(
                video_url,
                prompt,
                seed,
                steps,
                cfg_scale,
                sigma_max,
                sigma_min,
                batch_size,
                sampler_type,
                seconds_start,
                seconds_total,
                negative_prompt,
                init_noise_level,
            )
        )

    async def _arun(
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

        tmp_files = []
        try:
            tmp_video_file = os.path.abspath(
                os.path.join(neuron_config.temp_folder, f"{uuid4().hex}.mp4")
            )
            tmp_files.append(tmp_video_file)
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(tmp_video_file, "wb") as file:
                        await file.write(await response.content.read())

            input_args = {
                "seed": seed,
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

            slug = re.sub(r"[^a-z0-9-_]", "", slug)[:255].lower().replace(" ", "-")
            output_filename = f"{self.ref.split(':')[0].replace('/', '_')}_{uuid4().hex[:8]}_{slug}.mp4"
            output_file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, output_filename)
            )

            join_video_audio(tmp_video_file, tmp_audio_file, output_file_path)

            url = f"{neuron_config.static_content_url}/{output_filename}"
            logger.debug(f"Saved generated video to {output_file_path} <{url}>")
            return f'<video src="{url}"></video>\nFilename: {output_file_path}'
        except Exception as e:
            logger.exception(e)
            raise
        finally:
            for file in tmp_files:
                if os.path.exists(file):
                    os.remove(file)
