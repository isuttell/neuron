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
import re
import random
from neuron_server.util.slug import safe_filename


class ReplicateAudioGenerationToolArgs(BaseModel):
    video_url: str = Field(description="The URL of the video to add the audio to")
    slug: str = Field(
        description="A unique identifier. Must be all lower case with no special characters or spaces. Use dashes for spaces. Keep it short and descriptive. Must be less than 256 characters",
    )
    prompt: Optional[str] = Field(
        description="Keywords to guide the audio generation. Only use if the model is not generating the audio you want.",
        default=None,
    )
    duration: Optional[int] = Field(
        description="The duration of the video in seconds. The default is the image to video duration of 6 seconds.",
        default=6,
    )
    num_steps: Optional[int] = Field(
        description="The number of steps to use for the audio generation.",
        default=25,
    )
    cfg_strength: Optional[float] = Field(
        description="The CFG strength to use for the audio generation", default=4.5
    )
    seed: Optional[int] = Field(
        description="The seed to use for the audio generation", default=-1
    )
    negative_prompt: Optional[str] = Field(
        description="Negative prompt to avoid certain sounds",
        default="music, voice, ethereal",
    )


class ReplicateAudioGenerationTool(BaseTool):
    name: str = "replicate_audio_generation"
    description: str = (
        """
Use this tool to add realistic foley sound effects synced to a video using the zsxkib/mmaudio model on Replicate. It can even do speech, if you're not too worried about the words making sense. It uses an advanced AI model that synthesizes high-quality audio from video content, enabling seamless video-to-audio transformation. Use this tool to add foley sounds to a video. Avoid ethereal sounds.
""".strip()
    )

    args_schema: Type[ReplicateAudioGenerationToolArgs] = (
        ReplicateAudioGenerationToolArgs
    )

    ref: str = (
        "zsxkib/mmaudio:4b9f801a167b1f6cc2db6ba7ffdeb307630bf411841d4e8300e63ca992de0be9"
    )

    def _run(
        self,
        *args,
        **kwargs,
    ) -> str:
        return asyncio.run(
            self._arun(
                *args,
                **kwargs,
            )
        )

    async def _arun(
        self,
        video_url: str,
        slug: str,
        prompt: str = "",
        duration: int = 6,
        num_steps: int = 25,
        cfg_strength: float = 4.5,
        seed: Optional[int] = None,
        negative_prompt: str = "music, voice, ethereal",
    ) -> str:
        logger.debug(f"Generating audio for {video_url} with prompt: {prompt}")
        tmp_upload_file = os.path.abspath(
            os.path.join(neuron_config.temp_folder, uuid4().hex)
        )
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(video_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(tmp_upload_file, "wb") as file:
                        await file.write(await response.content.read())

            input_args = {
                "prompt": prompt,
                "duration": duration,
                "num_steps": num_steps,
                "cfg_strength": cfg_strength,
                "seed": seed if seed else random.randint(0, 2147483647),
                "negative_prompt": negative_prompt,
            }

            for key, value in input_args.items():
                logger.debug(f"{key}={value}")

            with open(tmp_upload_file, "rb") as video:
                output: replicate.helpers.FileOutput = await replicate.async_run(
                    self.ref,
                    input={
                        **input_args,
                        "video": video,
                    },
                )
                logger.debug(f"Generated <{output.url}>")
            slug = re.sub(r"[^a-z0-9-_]", "", slug)[:255].lower().replace(" ", "-")
            filename = safe_filename(
                self.ref.split(":")[0].replace("/", "_"), slug, "mp4"
            )
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
            if os.path.exists(tmp_upload_file):
                os.remove(tmp_upload_file)


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a video from an image using a prompt."
    )
    parser.add_argument(
        "--image_url",
        type=str,
        help="The URL of the image to use for the first frame of the video generation.",
        default="http://192.168.1.211:5002/static/dalle_generated_image_20241222174012_t_t.png",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="The prompt to use for the video generation for everything after the first frame.",
        default="panda and kitten missing each other",
    )
    args = parser.parse_args()
    tool = ReplicateAudioGenerationTool()
    result = await tool._arun(args.image_url, args.prompt)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
