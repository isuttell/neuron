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


class ReplicateLipSyncToolArgs(BaseModel):
    image_url: str = Field(
        description="The URL of the image to use for the video generation."
    )
    audio_url: str = Field(
        description="The URL of the audio to use for the video generation."
    )
    inference_steps: Optional[int] = Field(
        description="Diffusion inference steps.",
        default=20,
        ge=1,
        le=200,
    )
    cfg_scale: Optional[float] = Field(
        description="Classifier-free guidance scale.",
        default=3.5,
        ge=1,
        le=20,
    )
    max_audio_seconds: Optional[int] = Field(
        description="Max audio duration (in seconds).",
        default=60,
        ge=1,
        le=10,
    )
    resolution: Optional[int] = Field(
        description="Resolution for generation (square)",
        default=512,
        ge=64,
        le=2048,
    )


class ReplicateLipSyncTool(BaseTool):
    name: str = "replicate_lipsync_tool"
    description: str = (
        """
Use this tool to generate a video with realistic lip sync from a still image.

MEMO can generate highly realistic talking head videos with the following capabilities:
- Audio-Driven Animation: Generate talking videos from a single portrait image and an audio clip
- Multi-Language Support: Works with various languages including English, Mandarin, Spanish, Japanese, Korean, and Cantonese
- Versatile Image Input: Handles different image styles including portraits, sculptures, digital art, and animations
- Audio Flexibility: Compatible with different audio types including speech, singing, and rap
- Expression Control: Generates natural facial expressions aligned with audio emotional content
- Identity Preservation: Maintains consistent identity throughout generated videos
- Head Pose Variation: Supports various head poses while maintaining stability

This is very slow so confirm with the user that they want to use this tool.
""".strip()
    )

    args_schema: Type[ReplicateLipSyncToolArgs] = ReplicateLipSyncToolArgs

    def _run(
        self,
        image_url: str,
        audio_url: str,
        prompt: Optional[str] = None,
        duration: Optional[int] = 6,
        inference_steps: Optional[int] = 20,
        cfg_scale: Optional[float] = 3.5,
        max_audio_seconds: Optional[int] = 8,
        resolution: Optional[int] = 512,
    ) -> str:
        return asyncio.run(
            self._arun(
                image_url,
                audio_url,
                prompt,
                duration,
                inference_steps,
                cfg_scale,
                max_audio_seconds,
                resolution,
            )
        )

    async def _arun(
        self,
        image_url: str,
        audio_url: str,
        prompt: Optional[str] = None,
        duration: Optional[int] = 6,
        inference_steps: Optional[int] = 0,
        cfg_scale: Optional[float] = 3.5,
        max_audio_seconds: Optional[int] = 8,
        resolution: Optional[int] = 512,
    ) -> str:
        logger.debug(f"Generating video from {image_url} and {audio_url}")
        tmp_image_file = os.path.join(neuron_config.temp_folder, uuid4().hex)
        tmp_audio_file = os.path.join(neuron_config.temp_folder, uuid4().hex)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(tmp_image_file, "wb") as file:
                        await file.write(await response.content.read())
                async with session.get(audio_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(tmp_audio_file, "wb") as file:
                        await file.write(await response.content.read())

            with open(tmp_image_file, "rb") as image:
                with open(tmp_audio_file, "rb") as audio:
                    output: replicate.helpers.FileOutput = await replicate.async_run(
                        "zsxkib/memo:b9950fa2007ee3647dceaa3dd8e133be75c7f822bb1b84b7bb92aa2c1bc135b",
                        input={
                            "image": image,
                            "audio": audio,
                            "prompt": prompt,
                            "duration": duration,
                            "inference_steps": inference_steps,
                            "cfg_scale": cfg_scale,
                            "max_audio_seconds": max_audio_seconds,
                            "resolution": resolution,
                        },
                    )
                logger.debug(f"Generated <{output.url}>")

            filename = f"zsxkib_memo_{uuid4().hex}.mp4"
            file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )
            async with aiofiles.open(file_path, "wb") as file:
                async for chunk in output:
                    await file.write(chunk)
            url = f"{neuron_config.static_content_url}/{filename}"
            logger.debug(f"Saved generated video to {file_path} <{url}>")
            return f'<video src="{url}"></video>\nFilename: {file_path}'
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
        finally:
            if os.path.exists(tmp_image_file):
                os.remove(tmp_image_file)
            if os.path.exists(tmp_audio_file):
                os.remove(tmp_audio_file)
