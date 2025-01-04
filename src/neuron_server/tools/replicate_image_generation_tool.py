from langchain.tools import BaseTool
from typing import Type, Optional, Literal
from pydantic import BaseModel, Field
import replicate.helpers
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
import time
import logging
from io import BytesIO
import base64
from langchain.schema import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

logger = logging.getLogger(__name__)


class ImageDescription(BaseModel):
    description: str = Field(description="The description of the image")
    caption: str = Field(description="A short caption for the image")
    prompt_comparison: str = Field(
        description="A description of the differences between the prompt and the generated image highlighting any unexpected additions or subtractions"
    )


async def describe_image(
    prompt: str, image: Image.Image, max_tokens: int = 1000
) -> ImageDescription:
    # Get image as base64
    buffered = BytesIO()
    resized = image.copy()
    # Resize image to 1024x1024 to ensure it's not too large
    resized.thumbnail((1024, 1024))
    resized.save(buffered, format="JPEG")
    image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # Inspect the image
    model = ChatAnthropic(
        model="claude-3-5-sonnet-20241022", temperature=0, max_tokens=max_tokens
    )

    chain = (
        ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """\
You are an intelligent assistant that inspects AI generated images and returns descriptions of them to better understand what the image what was actually generated. Be long, descriptive and detailed in your description. Make sure to include the style of the image, the composition, the lighting, the mood, the subject, and any other relevant details. Use the prompt give context but do not use it as a direct source of information as it may not be what was actually generated. Explain your thoughts.

The prompt was: <prompt>{prompt}</prompt>
""".strip(),
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        | model.with_structured_output(ImageDescription)
    )

    return await chain.ainvoke(
        {
            "prompt": prompt,
            "messages": [
                HumanMessage(
                    content=[
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            },
                        },
                    ],
                ),
            ],
        }
    )


class ReplicateImageGenerationToolArgs(BaseModel):
    prompt: str = Field(
        description="""
Craft prompts that are detailed and specific. Clearly describe the subject, style, composition, lighting, and mood. For instance, specifying camera settings and environmental details can enhance realism. If you need to generate an image of Isaac you must include the TOK keyword. This has no additional context or history access so include all relevant details.

Prompt Tips:
- Use Artistic References: "Create an image in the style of Vincent van Gogh's 'Starry Night,' but replace the village with a futuristic cityscape"
- Specify Technical Details: "Capture a street food vendor in Tokyo at night, shot with a wide-angle lens (24mm) at f/1.8"
- Blend Concepts: "Illustrate 'The Last Supper' by Leonardo da Vinci, but reimagine it with robots in a futuristic setting."
- Use Contrast and Juxtaposition: "Create an image that juxtaposes the delicate beauty of nature with the harsh reality of urban decay."
- Incorporate Mood and Atmosphere: "Depict a cozy, warmly lit bookstore cafe on a rainy evening."
- Experiment with Unusual Perspectives: "Illustrate a 'bug's-eye view' of a picnic in a lush garden."
""".strip(),
    )
    slug: str = Field(
        description="A unique identifier. Must be all lower case with no special characters or spaces. Use dashes for spaces. Keep it short and descriptive. Must be less than 256 characters",
    )
    model: Optional[
        Literal[
            "isuttell/flux-lora-isaac:c2c37f42d4f435bd70a75479e241890f07459b0b1828ede06a6030b21768ad2f",
            "black-forest-labs/flux-1.1-pro-ultra",
            "black-forest-labs/flux-1.1-pro",
            "recraft-ai/recraft-20b",
            "ideogram-ai/ideogram-v2",
        ]
    ] = Field(
        description="The model to use for the image generation. Use the flux-1.1-pro-ultra model by default for the highest quality and resolution image, flux-1.1-pro produces the same quality but at a lower resolution and faster, and flux-lora-isaac when you need to generate images of Isaac. Use recraft-20b when trying to replicate a specific style. ideogram-v2 excels at creating captivating designs, innovative logos and posters with unique text rendering capabilities. Use ideogram-v2 when you need to create a logo or poster or need to generate clean looking text.",
        default="black-forest-labs/flux-1.1-pro-ultra",
    )
    aspect_ratio: Optional[
        Literal[
            "1:1",
            "16:9",
            "21:9",
            "3:2",
            "2:3",
            "4:5",
            "5:4",
            "3:4",
            "4:3",
            "9:16",
            "9:21",
        ]
    ] = Field(
        description="The aspect ratio to use for the image generation.",
        default="3:2",
    )
    num_inference_steps: Optional[int] = Field(
        description="The number of inference steps to use for the image generation",
        default=25,
    )
    style: Optional[
        Literal[
            "realistic_image",
            "realistic_image/b_and_w",
            "realistic_image/enterprise",
            "realistic_image/hard_flash",
            "realistic_image/hdr",
            "realistic_image/motion_blur",
            "realistic_image/natural_light",
            "realistic_image/studio_portrait",
            "digital_illustration",
            "digital_illustration/2d_art_poster",
            "digital_illustration/2d_art_poster_2",
            "digital_illustration/3d",
            "digital_illustration/80s",
            "digital_illustration/engraving_color",
            "digital_illustration/glow",
            "digital_illustration/grain",
            "digital_illustration/hand_drawn",
            "digital_illustration/hand_drawn_outline",
            "digital_illustration/handmade_3d",
            "digital_illustration/infantile_sketch",
            "digital_illustration/kawaii",
            "digital_illustration/pixel_art",
            "digital_illustration/psychedelic",
            "digital_illustration/seamless",
            "digital_illustration/voxel",
            "digital_illustration/watercolor",
        ]
    ] = Field(
        description="The style to use for the image generation. This only works with the recraft-20b model.",
        default="realistic_image",
    )
    image_url: Optional[str] = Field(
        description="Use this to generate an image based on an existing image. e.g. when the user wants to iterate on an existing image or generate a variation of an existing image. This only works with the flux-1.1-pro-ultra model.",
        default=None,
    )
    image_prompt_strength: Optional[float] = Field(
        description="The strength of the image prompt. 0.4 will closely follow the image and allow minor changes while 0.1 will allow more drastic and creative changes. This only works with the flux-1.1-pro-ultra model.",
        default=0.1,
        ge=0.0,
        le=1.0,
    )
    raw: Optional[bool] = Field(
        description="If true then image will be returned with less processing which can make people and places look more realistic. Use this when trying to enhance realism. This only works with the flux-1.1-pro-ultra model.",
        default=False,
    )
    seed: Optional[int] = Field(
        description="Random seed. Set for reproducible generation",
        default=None,
    )
    update_tablet: Optional[bool] = Field(
        description="Whether to update the smart home tablet dashboard with the generated image. Only use this if the user explicitly asks for it",
        default=False,
    )
    describe: Optional[bool] = Field(
        description="Whether to describe the image in detail. Use this when you want to understand better what generated image looks like. Use this while telling stories to better incorporate the image into the story.",
        default=True,
    )


class ReplicateImageGenerationTool(BaseTool):
    name: str = "replicate_image_generation"
    description: str = (
        """
Use this tool to generate an image using a text prompt on replicate.com and has access to a range of models. flux-1.1-pro is the best model for most use cases, from realistic or semi-realistic images to illustrations. It outputs very high resolution images and has the best consistency between images. The ultra variant outputs at a higher resolution at the cost of speed. flux-lora-isaac a fined tuned flux dev model for generating images of Isaac. Use ideogram-v2 for logos and posters. When generating personality logos they must use a square aspect ratio and work well on a dark background.
""".strip()
    )

    args_schema: Type[ReplicateImageGenerationToolArgs] = (
        ReplicateImageGenerationToolArgs
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
        prompt: str,
        slug: str,
        model: str = "black-forest-labs/flux-1.1-pro-ultra",
        aspect_ratio: str = "3:2",
        num_inference_steps: int = 25,
        style: Optional[str] = None,
        image_url: Optional[str] = None,
        raw: bool = False,
        image_prompt_strength: Optional[float] = None,
        seed: Optional[int] = None,
        update_tablet: bool = False,
        describe: bool = True,
    ) -> str:
        start_time = time.perf_counter()
        logger.debug(f"Generating image using {model}")
        tmp_upload_file = os.path.join(neuron_config.temp_folder, uuid4().hex)
        try:
            if image_url:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        response.raise_for_status()

                        async with aiofiles.open(tmp_upload_file, "wb") as file:
                            await file.write(await response.content.read())

            image_prompt = (
                open(tmp_upload_file, "rb") if os.path.exists(tmp_upload_file) else None
            )
            input_args = {
                "raw": raw,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "output_format": "png",
                "safety_tolerance": 6,
                "disable_safety_checker": True,
                "num_inference_steps": num_inference_steps,
            }
            if image_prompt:
                input_args["image_prompt"] = image_prompt
                input_args["image_prompt_strength"] = image_prompt_strength

            if seed:
                input_args["seed"] = seed

            if style:
                input_args["style"] = style

            for key, value in input_args.items():
                logger.debug(
                    f"{key}={True if key == 'image_prompt' and value else value}"
                )
            try:
                output: replicate.helpers.FileOutput = await replicate.async_run(
                    model,
                    input=input_args,
                )
            finally:
                if image_prompt:
                    image_prompt.close()
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
                described_image: Optional[ImageDescription] = None
                if describe:
                    described_image = await describe_image(prompt, image)
                    pnginfo.add_text("Description", described_image.description)
                    pnginfo.add_text("Caption", described_image.caption)
                image.save(file_path, format="png", pnginfo=pnginfo, quality=95)
                create_thumbnails(
                    file_path,
                    neuron_config.static_folder,
                )
                url = f"{neuron_config.static_content_url}/{filename}"
                if update_tablet and i == 0:
                    shutil.copy(file_path, neuron_config.tablet_image_filename)
                    logger.debug(
                        f"Copied generated image to {neuron_config.tablet_image_filename}"
                    )
                if described_image:
                    results.append(
                        f"""\
<image>
    <display>![{described_image.caption}]({url})</display>
    <description>{described_image.description}</description>
    <prompt_comparison>{described_image.prompt_comparison}</prompt_comparison>
</image>
"""
                    )
                else:
                    results.append(
                        f"""\
<image>
    <display>![{prompt}]({url})</display>
</image>
"""
                    )
            end_time = time.perf_counter()
            logger.debug(
                f"Image generation job took {end_time - start_time:.2f} seconds"
            )
            return f"<images>\n" + "\n".join(results) + "\n</images>"
        except Exception as e:
            logger.exception(e)
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
