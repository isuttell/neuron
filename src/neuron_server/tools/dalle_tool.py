from langchain.tools import BaseTool
import requests
from PIL import Image, PngImagePlugin
from io import BytesIO
from datetime import datetime, timezone
from neuron_server.config import config
from neuron_server.logger import logger
from openai import OpenAI
from typing import Literal


class DalleTool(BaseTool):
    name: str = "dalle"
    description: str = (
        "A tool that generates images based on a given prompt using OpenAI's DALL-E 3.  DALL-E is suited for generating highly detailed, standalone images with precise attributes, especially in realistic or semi-realistic styles. Use this when the user asks for an image. When generating DALL-E prompts, include specific visual details, such as colors, textures, and object placements, to guide the model toward a precise result. Mention the desired style (e.g., photorealistic, cartoonish, or abstract) and add context, like background elements or lighting, for more cohesive images. Focus on clarity and conciseness in each prompt to avoid ambiguity and ensure reproducible results. Returns the url to the generated image which must be displayed using markdown."
    )

    def generate_image(
        self,
        prompt: str,
        style: Literal["natural", "vivid"] = "vivid",
    ) -> Image.Image:
        """
        Generate an image based on the given prompt dalle

        Args:
            prompt (str): The prompt to generate the image from.

        Returns:
            Image.ImageFile: The generated image.
        """

        client = OpenAI(api_key=config.openai_api_key)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            style=style,
            n=1,
        )
        # Download the image so we can save it long term
        image_url = response.data[0].url
        image = response = requests.get(image_url)
        image.raise_for_status()
        return Image.open(BytesIO(image.content))

    def _run(
        self,
        prompt: str,
        style: Literal["natural", "vivid"] = "vivid",
    ) -> str:
        """
        Run the tool to generate an image based on the given prompt.
        Args:
            prompt (str): The prompt to generate the image from.

        Returns:
            str: The URL or path to the generated image.
        """
        try:
            image = self.generate_image(
                prompt=prompt,
                style=style,
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
            file_path = f"{config.static_folder}/images/{filename}"
            image.save(
                file_path,
                format="png",
                pnginfo=pnginfo,
            )
            url = f"{config.static_content_url}/images/{filename}"
            logger.debug(f"Saved generated image to {file_path} <{url}>")
            return url
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
