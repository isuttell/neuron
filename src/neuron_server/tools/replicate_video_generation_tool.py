from langchain.tools import BaseTool
from typing import Type, Optional, Literal
from pydantic import BaseModel, Field
import replicate.helpers
from neuron_server.logger import logger
import asyncio
import time
import replicate
import aiohttp
from uuid import uuid4
import os
from neuron_server.config import config as neuron_config
import aiofiles
import re
from langchain_core.runnables import RunnableConfig
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.slug import safe_filename


class ReplicateVideoGenerationToolArgs(BaseModel):
    image_url: Optional[str] = Field(
        description="The URL of the image to use for the first frame of the video generation."
    )
    prompt: str = Field(
        description="To create effective prompts for MiniMax's Video-01 model, define the subject, setting, and any actions or movements clearly. Include dynamic camera effects like panning, zooming, or handheld motion to enhance engagement. Combine these elements for complex scenes while maintaining character consistency by specifying attributes like clothing, hair, and environment. Example: A noir detective in a trench coat stands under a dim streetlight in a rainy alley, with the camera zooming in slowly."
    )
    name: str = Field(
        description="A unique display name for the video generation less than 256 characters"
    )
    ref: Literal[
        "minimax/video-01",
        "minimax/video-01-live",
    ] = Field(
        description="The model to use for the video generation. minimax/video-01 is for general use and minimax/video-01-live is for 2d animation and digital illustrations",
        default="minimax/video-01",
    )


class ReplicateVideoGenerationTool(BaseTool):
    name: str = "replicate_video_generation"
    description: str = (
        """
This tool uses the video generation model minimax/video-01, also known as Hailuo, on Replicate to generate a video from a text prompt, or from an image, that is 6 seconds long. This model supports high-definition videos at 720p resolution and 25fps, featuring cinematic camera movement effects. It can quickly create visually striking content based on text descriptions and supports facial animation. This tool can't handle overly complex scenes or action. Only use this tool when the user specifically asks for it as it costs extra each time to run. This tool may take several minutes or more to complete.
""".strip()
    )

    args_schema: Type[ReplicateVideoGenerationToolArgs] = (
        ReplicateVideoGenerationToolArgs
    )

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        ref: Literal["minimax/video-01", "minimax/video-01-live"],
        prompt: str,
        name: str,
        config: RunnableConfig,
        image_url: Optional[str] = None,
    ) -> str:
        start_time = time.perf_counter()
        source = f" from {image_url}" if image_url else ""
        logger.debug(f"Generating video with prompt{source}: {prompt}")
        tmp_upload_file = os.path.abspath(
            os.path.join(neuron_config.temp_folder, uuid4().hex)
        )
        try:
            if image_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        response.raise_for_status()
                        async with aiofiles.open(tmp_upload_file, "wb") as file:
                            await file.write(await response.content.read())

            input_args = {
                "prompt": prompt,
                "prompt_optimizer": True,
            }
            if os.path.exists(tmp_upload_file):
                input_args["first_frame_image"] = open(tmp_upload_file, "rb")
            try:
                output: replicate.helpers.FileOutput = await replicate.async_run(
                    ref, input=input_args
                )
                logger.debug(f"Generated <{output.url}>")
            finally:
                if (
                    "first_frame_image" in input_args
                    and input_args["first_frame_image"]
                ):
                    input_args["first_frame_image"].close()

            filename = safe_filename(ref.replace("/", "_"), name, "mp4")
            file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )
            async with aiofiles.open(file_path, "wb") as file:
                async for chunk in output:
                    await file.write(chunk)
            url = f"{neuron_config.static_content_url}/{filename}"
            media_item = await MediaItemModel.create(
                thread_id=config["configurable"].get("thread_id"),
                user_id=config["configurable"].get("user_id"),
                url=url,
                type="video",
                name=name,
                description=f"Prompt: {prompt}",
            )
            logger.debug(
                f"Saved generated video to {file_path} <{url}> - {time.perf_counter() - start_time:.2f}s"
            )
            return f"""\
<video id="{media_item.id}">
    <display><video src="{url}"></video></display>
    <filename>{file_path}</filename>
</video>"""
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
        default="http://192.168.1.211:5002/static/images/dalle_generated_image_20241222174012.png",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="The prompt to use for the video generation for everything after the first frame.",
        default="panda and kitten missing each other",
    )
    args = parser.parse_args()
    tool = ReplicateVideoGenerationTool()
    result = await tool._arun(args.prompt, args.image_url)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
