from langchain.tools import BaseTool
from typing import Type, Optional, Literal
from pydantic import BaseModel, Field
import replicate.helpers
from neuron_server.logger import logger
import asyncio
import replicate
from uuid import uuid4
import os
from neuron_server.config import config as neuron_config
import aiofiles
import aiohttp
from PIL import PngImagePlugin, Image
from datetime import datetime, timezone
import re
import shutil
from neuron_server.util.image_utilities import create_thumbnails
from neuron_server.cache import set_cache_key
from neuron_server.pubsub import pubsub
from neuron_server.controllers.events.app_events import SidebarImageEvent


class ReplicateImageGenerationToolArgs(BaseModel):
    image_url: str = Field(description="The URL of the image to replace.")
    mask_prompt: str = Field(description="The prompt to use for the mask generation.")
    negative_mask_prompt: Optional[str] = Field(
        description="The negative prompt to use for the mask generation."
    )
    mask_adjustment_factor: Optional[int] = Field(
        0, description="Mask Adjustment Factor (-ve for erosion, +ve for dilation)"
    )


class ReplicateImageGenerationTool(BaseTool):
    name: str = "replicate_image_generation"
    description: str = (
        """
Use this tool to generate an image using a text prompt on replicate.com and has access to a range of models. flux-1.1-pro-ultra is the best model for most use cases, from realistic or semi-realistic images to illustrations. It outputs the highest resolution and has the best consistency between images. flux-lora-isaac a fined tuned flux dev model for generating images of Isaac. Use ideogram-v2 for logos and posters. When generating personality logos they must use a square aspect ratio and work well on a dark background.
""".strip()
    )

    args_schema: Type[ReplicateImageGenerationToolArgs] = (
        ReplicateImageGenerationToolArgs
    )

    mask_ref: str = (
        "schananas/grounded_sam:ee871c19efb1941f55f66a3d7d960428c8a5afcb77449547fe8e5a3ab9ebc21c",
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
        image_url: str,
        mask_prompt: str,
        negative_mask_prompt: Optional[str] = "",
        mask_adjustment_factor: Optional[int] = 0,
    ) -> str:
        tmp_upload_file = os.path.join(neuron_config.temp_folder, uuid4().hex)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    response.raise_for_status()

                    async with aiofiles.open(tmp_upload_file, "wb") as file:
                        await file.write(await response.content.read())

            try:
                with open(tmp_upload_file, "rb") as image:
                    input_args = {
                        "image": image,
                        "mask_prompt": mask_prompt,
                        "negative_mask_prompt": negative_mask_prompt,
                        "adjustment_factor": mask_adjustment_factor,
                    }
                    output: replicate.helpers.FileOutput = await replicate.async_run(
                        self.mask_ref,
                        input=input_args,
                    )
            finally:
                if os.path.exists(tmp_upload_file):
                    os.remove(tmp_upload_file)
            now = datetime.now().astimezone()
            if not isinstance(output, list):
                output = [output]
            results = []

            # Remove any non-alphanumeric characters and limit to 255 characters
            slug = re.sub(r"[^a-z0-9-_]", "", slug)[:255].lower().replace(" ", "-")

            for i, result in enumerate(output):
                # Ensure a unique filename
                filename = f"replicate_{uuid4().hex[:8]}_{slug}.png"
                file_path = os.path.abspath(
                    os.path.join(neuron_config.static_folder, filename)
                )
                async with aiofiles.open(file_path, "wb") as file:
                    async for chunk in result:
                        await file.write(chunk)

                # Embed the prompt and datetime in the image
                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("Description", prompt)
                pnginfo.add_text("Software", f"Model: {model}")
                pnginfo.add_text(
                    "DateTimeOriginal",
                    now.isoformat(timespec="seconds"),
                )
                pnginfo.add_text(
                    "Parameters",
                    "\n".join(
                        [
                            f"{key}={True if key == 'image_prompt' and value else value}"
                            for key, value in input_args.items()
                        ]
                    ),
                )
                image = Image.open(file_path)
                image.save(file_path, format="png", pnginfo=pnginfo, quality=95)
                url = f"{neuron_config.static_content_url}/{filename}"

                results.append(f"![{prompt}]({url})")
            return "\n".join(results)
        except Exception as e:
            logger.error(e, exc_info=True)
            raise


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate an image using a prompt.")
    parser.add_argument(
        "--prompt",
        type=str,
        help="The prompt to use for the image generation.",
        default="A beautiful sunset over a calm ocean with a clear sky and a few clouds.",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="The model ID to use for the image generation.",
        default="black-forest-labs/flux-1.1-pro-ultra",
    )
    parser.add_argument(
        "--aspect_ratio",
        type=str,
        help="The aspect ratio to use for the image generation.",
        default="3:2",
    )
    args = parser.parse_args()
    tool = ReplicateImageGenerationTool()
    result = await tool._arun(args.prompt, args.model, args.aspect_ratio)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
