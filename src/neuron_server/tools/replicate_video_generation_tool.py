import asyncio
import os
import time
from typing import Any, Literal
from uuid import uuid4

import aiofiles
import aiohttp
import replicate
import replicate.helpers
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.slug import safe_filename


class ReplicateVideoGenerationToolArgs(BaseModel):
    image_url: str | None = Field(
        description=(
            "The URL of the image to use for the first frame of the video generation."
        )
    )
    prompt: str = Field(
        description=(
            "To create effective prompts for MiniMax's Video-01 model:\n"
            "1. Define subject, setting, and actions/movements clearly\n"
            "2. Include dynamic camera effects (panning, zooming, handheld)\n"
            "3. Maintain character consistency (clothing, hair, environment)\n\n"
            "Example: A noir detective in a trench coat stands under a dim "
            "streetlight in a rainy alley, with the camera zooming in slowly."
        )
    )
    name: str = Field(
        description=(
            "A unique display name for the video generation less than 256 characters"
        )
    )
    ref: Literal[
        "minimax/video-01",
        "minimax/video-01-live",
    ] = Field(
        description=(
            "The model to use for the video generation. minimax/video-01 is for "
            "general use and minimax/video-01-live is for 2d animation and "
            "digital illustrations"
        ),
        default="minimax/video-01",
    )


class ReplicateVideoGenerationTool(BaseTool):
    name: str = "replicate_video_generation"
    description: str = """
This tool uses the video generation model minimax/video-01 (Hailuo) on
Replicate to generate videos from text prompts or images.

Features:
- 6 seconds long
- 720p resolution at 25fps
- Cinematic camera movement effects
- Facial animation support
- Quick visual content creation

Note: Cannot handle complex scenes/action. Use only when specifically
requested as it incurs additional costs. May take several minutes to
complete.
"""

    args_schema: type[ReplicateVideoGenerationToolArgs] = (
        ReplicateVideoGenerationToolArgs
    )

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        ref: Literal["minimax/video-01", "minimax/video-01-live"],
        prompt: str,
        name: str,
        config: RunnableConfig,
        image_url: str | None = None,
    ) -> str:
        start_time = time.perf_counter()
        source = f" from {image_url}" if image_url else ""
        logger.debug(f"Generating video with prompt{source}: {prompt}")
        tmp_upload_file = os.path.abspath(
            os.path.join(neuron_config.temp_folder, uuid4().hex)
        )
        try:
            if image_url:
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(image_url) as response,
                    aiofiles.open(tmp_upload_file, "wb") as file,
                ):
                    response.raise_for_status()
                    await file.write(await response.content.read())

            input_args = {
                "prompt": prompt,
                "prompt_optimizer": True,
            }
            if os.path.exists(tmp_upload_file):
                async with aiofiles.open(tmp_upload_file, "rb") as f:
                    input_args["first_frame_image"] = await f.read()

            try:
                output: replicate.helpers.FileOutput = await replicate.async_run(
                    ref, input=input_args
                )
                logger.debug(f"Generated <{output.url}>")
            finally:
                if os.path.exists(tmp_upload_file):
                    os.remove(tmp_upload_file)

            filename = safe_filename(ref.replace("/", "_"), name, "mp4")
            file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )
            async with aiofiles.open(file_path, "wb") as file:
                async for chunk in output:
                    await file.write(chunk)
            url = f"{neuron_config.static_content_url}/{filename}"
            create_params = MediaItemModel.CreateParams(
                thread_id=config["configurable"].get("thread_id"),
                user_id=config["configurable"].get("user_id"),
                url=url,
                media_type="video",
                name=name,
                description=prompt,
            )
            media_item = await MediaItemModel.create(params=create_params)
            duration = time.perf_counter() - start_time
            logger.debug(f"Saved video to {file_path} <{url}> - {duration:.2f}s")
            return f"""\
<video id="{media_item.id}">
    <display><video src="{url}"></video></display>
    <filename>{file_path}</filename>
</video>"""
        except Exception as e:
            logger.error(e, exc_info=True)
            raise


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate a video from an image using a prompt."
    )
    parser.add_argument(
        "--image_url",
        type=str,
        help=(
            "The URL of the image to use for the first frame of the video generation."
        ),
        default=(
            "http://192.168.1.211:5002/static/images/"
            "dalle_generated_image_20241222174012.png"
        ),
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="The prompt for video generation after the first frame.",
        default="panda and kitten missing each other",
    )
    args = parser.parse_args()
    tool = ReplicateVideoGenerationTool()
    result = await tool._arun(args.prompt, args.image_url)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
