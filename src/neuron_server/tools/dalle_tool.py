import asyncio
import os
from datetime import UTC, datetime
from io import BytesIO
from typing import Any, Literal

import aiohttp
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI
from PIL import Image, PngImagePlugin
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.image_utilities import create_thumbnails
from neuron_server.util.slug import safe_filename


async def generate_images(
    prompt: str,
    style: Literal["natural", "vivid"] = "vivid",
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
    n: int = 1,
) -> list[Image.Image]:
    """
    Generate an image based on the given prompt dalle

    Args:
        prompt (str): The prompt to generate the image from.

    Returns:
        Image.ImageFile: The generated image.
    """

    client = AsyncOpenAI(api_key=neuron_config.openai_api_key)
    response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="hd",
        style=style,
        n=n,
    )
    # Download the image so we can save it long term
    images = []
    for image in response.data:
        image_url = image.url
        try:
            async with aiohttp.ClientSession() as session:
                logger.debug(f"Downloading image from {image_url}")
                async with session.get(image_url) as response:
                    response.raise_for_status()
                    image_data = await response.content.read()
                    images.append(Image.open(BytesIO(image_data)))
        except aiohttp.ClientError as e:
            logger.error(f"Failed to download image: {str(e)}")
            raise
    return images


class DalleArgs(BaseModel):
    name: str = Field(
        description=(
            "A unique display name for the image generation less than 256 characters"
        )
    )
    prompt: str = Field(
        description=(
            "The prompt to generate the image from.\n\n"
            "When creating prompts for images, include specific visual details, "
            "such as colors, textures, and object placements, to guide the model "
            "toward a precise result. Mention the desired style (e.g., "
            "photorealistic, cartoonish, or abstract) and add context, like "
            "background elements or lighting, for more cohesive images. Focus on "
            "clarity and conciseness in each prompt to avoid ambiguity and ensure "
            "reproducible results. Unless you are trying to maintain a specific "
            "style or look add multiple random modern art styles and artistic "
            "styles to ensure variety."
        )
    )
    style: Literal["natural", "vivid"] = Field(
        description="The style of the image to generate.", default="vivid"
    )
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = Field(
        description=(
            "The size of the image to generate. Default to square. "
            "Use wide images for cinematic effect."
        ),
        default="1024x1024",
    )
    n: int = Field(
        description="The number of images to generate. Default to 1.",
        default=1,
    )


class DalleTool(BaseTool):
    name: str = "dalle"
    description: str = (
        "A tool that generates detailed, realistic or semi-realistic images "
        "and charts based on a text prompt using OpenAI's DALL·E 3. "
        "Returns a markdown image tag for display."
    )
    args_schema: type[DalleArgs] = DalleArgs

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0913
        self,
        name: str,
        prompt: str,
        config: RunnableConfig,
        style: Literal["natural", "vivid"] = "vivid",
        size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
        n: int = 1,
    ) -> str:
        """
        Runs the tool to generate an image based on the given prompt.
        Args:
            prompt (str): The prompt to generate the image from.
            style (Literal["natural", "vivid"]): The style of the image to generate.
            size (Literal["1024x1024", "1792x1024", "1024x1792"]): The size of the image
              to generate.
        Returns:
            str: A markdown string containing the generated image.
        """
        try:
            logger.debug(f"Generating dalle image for prompt: {prompt}")
            images = await generate_images(
                prompt=prompt,
                style=style,
                size=size,
                n=n,
            )
            now = datetime.now(UTC).astimezone()
            results = []
            for i, image in enumerate(images):
                filename = safe_filename("dalle", f"{name}_{i}", "png")
                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("Description", prompt)
                pnginfo.add_text(
                    "DateTimeOriginal",
                    now.isoformat(timespec="seconds"),
                )
                file_path = os.path.abspath(
                    os.path.join(neuron_config.static_folder, filename)
                )
                image.save(
                    file_path,
                    format="png",
                    pnginfo=pnginfo,
                    quality=95,
                )
                create_thumbnails(
                    file_path,
                )
                url = f"{neuron_config.static_content_url}/{filename}"
                create_params = MediaItemModel.CreateParams(
                    thread_id=config["configurable"].get("thread_id"),
                    user_id=config["configurable"].get("user_id"),
                    url=url,
                    media_type="image",
                    name=name,
                    description=prompt,
                )
                media_item = await MediaItemModel.create(params=create_params)
                logger.debug(f"Saved generated image to {file_path} <{url}>")
                results.append(
                    f"""\
<image id="{media_item.id}">
    <display>![{prompt}]({url})</display>
</image>
"""
                )

            return "<images>\n" + "\n".join(results) + "\n</images>"
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error generating image: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate an image using a prompt.")
    parser.add_argument(
        "prompt", type=str, help="The prompt to generate the image from."
    )
    args = parser.parse_args()

    tool = DalleTool()
    results = tool._run(
        prompt=args.prompt,
    )
    print(results)
