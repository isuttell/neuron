from langchain.tools import BaseTool
import requests
from PIL import Image, PngImagePlugin
from io import BytesIO
from datetime import datetime, timezone
from neuron_server.config import config
from neuron_server.logger import logger
from openai import AsyncOpenAI
from typing import Literal, Type
from pydantic import BaseModel, Field
import asyncio
import aiohttp
import shutil
import os


async def generate_image(
    prompt: str,
    style: Literal["natural", "vivid"] = "vivid",
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
) -> Image.Image:
    """
    Generate an image based on the given prompt dalle

    Args:
        prompt (str): The prompt to generate the image from.

    Returns:
        Image.ImageFile: The generated image.
    """

    client = AsyncOpenAI(api_key=config.openai_api_key)
    response = await client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size=size,
        quality="hd",
        style=style,
        n=1,
    )
    # Download the image so we can save it long term
    image_url = response.data[0].url
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            response.raise_for_status()
            return Image.open(BytesIO(await response.content.read()))


class DalleArgs(BaseModel):
    prompt: str = Field(
        description="""
The prompt to generate the image from.

When creating prompts for images, include specific visual details, such as colors, textures, and object placements, to guide the model toward a precise result. Mention the desired style (e.g., photorealistic, cartoonish, or abstract) and add context, like background elements or lighting, for more cohesive images. Focus on clarity and conciseness in each prompt to avoid ambiguity and ensure reproducible results. Unless you are trying to maintain a specific style or look add multiple random modern art styles and artistic styles to ensure variety.
        """.strip()
    )
    style: Literal["natural", "vivid"] = Field(
        description="The style of the image to generate.", default="vivid"
    )
    size: Literal["1024x1024", "1792x1024", "1024x1792"] = Field(
        description="The size of the image to generate. Default to square. Use wide images for cinematic effect.",
        default="1024x1024",
    )
    update_tablet: bool = Field(
        description="Whether to update the smart home tablet dashboard with the generated image. Only use this if the user explicitly asks for it.",
        default=False,
    )


class DalleTool(BaseTool):
    name: str = "dalle"
    description: str = (
        "A tool that generates highly detailed, realistic or semi-realistic images and charts based on a text prompt using OpenAI's DALL·E 3. Returns a markdown image tag for display."
    )
    args_schema: Type[DalleArgs] = DalleArgs

    def _run(
        self,
        prompt: str,
        style: Literal["natural", "vivid"] = "vivid",
        size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
    ) -> str:
        return asyncio.run(self._arun(prompt, style, size))

    async def _arun(
        self,
        prompt: str,
        style: Literal["natural", "vivid"] = "vivid",
        size: Literal["1024x1024", "1792x1024", "1024x1792"] = "1024x1024",
        update_tablet: bool = False,
    ) -> str:
        """
        Runs the tool to generate an image based on the given prompt.
        Args:
            prompt (str): The prompt to generate the image from.
            style (Literal["natural", "vivid"]): The style of the image to generate.
            size (Literal["1024x1024", "1792x1024", "1024x1792"]): The size of the image to generate.
        Returns:
            str: A markdown string containing the generated image.
        """
        try:
            logger.debug(f"Generating dalle image for prompt: {prompt}")
            image = await generate_image(
                prompt=prompt,
                style=style,
                size=size,
            )
            now = datetime.now(timezone.utc).astimezone()
            timestamp = now.strftime("%Y%m%d%H%M%S")
            filename = f"dalle_generated_image_{timestamp}.png"
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text("Description", prompt)
            pnginfo.add_text(
                "DateTimeOriginal",
                now.isoformat(timespec="seconds"),
            )
            file_path = os.path.abspath(
                os.path.join(config.static_folder, "images", filename)
            )
            image.save(
                file_path,
                format="png",
                pnginfo=pnginfo,
            )
            url = f"{config.static_content_url}/images/{filename}"
            logger.debug(f"Saved generated image to {file_path} <{url}>")
            if update_tablet:
                shutil.copy(file_path, config.tablet_image_filename)
                logger.debug(
                    f"Copied generated image to {config.tablet_image_filename}"
                )
            return f"![{prompt}]({url})"
        except Exception as e:
            logger.exception(e)
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
