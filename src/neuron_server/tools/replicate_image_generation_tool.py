import asyncio
import logging
import os
import random
from datetime import datetime
from io import BufferedReader, BytesIO
from typing import Any, Literal
from uuid import uuid4

import aiofiles
import aiohttp
import replicate
import replicate.helpers
from langchain.schema import HumanMessage
from langchain.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableConfig
from PIL import Image, PngImagePlugin
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.image_utilities import create_image_url, create_thumbnails
from neuron_server.util.slug import safe_filename

logger = logging.getLogger(__name__)

RECRAFT_ASPECT_RATIO_TO_SIZE = {
    "1:1": "1024x1024",
    "16:9": "1820x1024",
    "3:2": "1536x1024",
    "2:3": "1024x1536",
    "4:3": "1365x1024",
    "3:4": "1024x1365",
    "5:4": "1280x1024",
    "4:5": "1024x1280",
    "2:1": "2048x1024",
    "1:2": "1024x2048",
}


class ImageDescription(BaseModel):
    description: str = Field(description="The description of the image")
    caption: str = Field(description="A short caption for the image")
    prompt_comparison: str = Field(
        description=(
            "A description of the differences between the prompt and the generated "
            "image highlighting any unexpected additions or subtractions"
        )
    )


# Initialize the model
model = ChatAnthropic(model="claude-3-7-sonnet-20250219", temperature=0.2)

chain = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """\
You are an intelligent assistant that inspects AI generated images and returns
descriptions of them to better understand what the image what was actually generated.
Be long, descriptive and detailed in your description. Make sure to include the style
of the image, the composition, the lighting, the mood, the subject, and any other
relevant details. Use the prompt give context but do not use it as a direct source
of information as it may not be what was actually generated. Explain your thoughts.

The prompt was: <prompt>{prompt}</prompt>
""".strip(),
        ),
        MessagesPlaceholder(variable_name="messages"),
    ]
) | model.with_structured_output(ImageDescription)


async def describe_image(prompt: str, image: Image.Image) -> ImageDescription:
    image_url = create_image_url(image)

    return await chain.ainvoke(
        {
            "prompt": prompt,
            "messages": [
                HumanMessage(
                    content=[
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                ),
            ],
        },
    )


class ReplicateImageGenerationToolArgs(BaseModel):
    name: str = Field(
        description=(
            "A unique display title for the image generation less than 256 characters"
        )
    )
    prompt: str = Field(
        description="""
Craft prompts that are detailed and specific. Clearly describe the subject, style,
composition, lighting, and mood. For instance, specifying camera settings and
environmental details can enhance realism. If you need to generate an image of Isaac
you must include the TOK keyword. This has no additional context or history access
so include all relevant details.

Prompt Tips:
- Use Artistic References: "Create an image in the style of Vincent van Gogh's
  'Starry Night,' but replace the village with a futuristic cityscape"
- Specify Technical Details: "Capture a street food vendor in Tokyo at night, shot
  with a wide-angle lens (24mm) at f/1.8"
- Blend Concepts: "Illustrate 'The Last Supper' by Leonardo da Vinci, but reimagine
  it with robots in a futuristic setting."
- Use Contrast and Juxtaposition: "Create an image that juxtaposes the delicate
  beauty of nature with the harsh reality of urban decay."
- Incorporate Mood and Atmosphere: "Depict a cozy, warmly lit bookstore cafe on a
  rainy evening."
- Experiment with Unusual Perspectives: "Illustrate a 'bug's-eye view' of a picnic
  in a lush garden."
""".strip(),
    )
    model: (
        Literal[
            "isuttell/flux-lora-isaac:c2c37f42d4f435bd70a75479e241890f07459b0b1828ede06a6030b21768ad2f",
            "black-forest-labs/flux-1.1-pro-ultra",
            "black-forest-labs/flux-1.1-pro",
            "recraft-ai/recraft-20b",
            "recraft-ai/recraft-v3",
            "ideogram-ai/ideogram-v2",
            "google/imagen-4",
        ]
        | None
    ) = Field(
        description=(
            "The model to use for the image generation. Use the flux-1.1-pro-ultra "
            "model by default for the highest quality and resolution image, "
            "flux-1.1-pro produces the same quality but at a lower resolution and "
            "faster, and flux-lora-isaac when you need to generate images of Isaac. "
            "Use recraft-20b when trying to replicate a specific style. ideogram-v2 "
            "excels at creating captivating designs, innovative logos and posters "
            "with unique text rendering capabilities. Use ideogram-v2 when you need "
            "to create a logo or poster or need to generate clean looking text. "
            "google/imagen-4 excels at fine detail rendering, typography, and both "
            "photorealistic and abstract styles with up to 2K resolution."
        ),
        default="black-forest-labs/flux-1.1-pro-ultra",
    )
    aspect_ratio: (
        Literal["1:1", "16:9", "3:2", "2:3", "4:5", "5:4", "3:4", "4:3", "9:16"] | None
    ) = Field(
        description="The aspect ratio to use for the image generation.",
        default="3:2",
    )
    num_inference_steps: int | None = Field(
        description="The number of inference steps to use for the image generation",
        default=25,
    )
    style: (
        Literal[
            "any",
            "realistic_image"
            "digital_illustration"
            "realistic_image/b_and_w"
            "realistic_image/enterprise"
            "realistic_image/hard_flash"
            "realistic_image/hdr"
            "realistic_image/motion_blur"
            "realistic_image/natural_light"
            "realistic_image/studio_portrait"
            "digital_illustration/2d_art_poster"
            "digital_illustration/2d_art_poster_2"
            "digital_illustration/engraving_color"
            "digital_illustration/grain"
            "digital_illustration/hand_drawn"
            "digital_illustration/hand_drawn_outline"
            "digital_illustration/handmade_3d"
            "digital_illustration/infantile_sketch"
            "digital_illustration/pixel_art",
        ]
        | None
    ) = Field(
        description=(
            "The style to use for the image generation. This only works with the "
            "recraft-20b and recraft-v3 models."
        ),
        default="any",
    )
    image_url: str | None = Field(
        description=(
            "Use this to generate an image based on an existing image. e.g. when "
            "the user wants to iterate on an existing image or generate a variation "
            "of an existing image. This only works with the flux-1.1-pro-ultra model."
        ),
        default=None,
    )
    image_prompt_strength: float | None = Field(
        description=(
            "The strength of the image prompt. 0.5 will closely follow the image "
            "and allow minor changes while 0.1 will allow more drastic and creative "
            "changes. This only works with the flux-1.1-pro-ultra model."
        ),
        default=0.1,
        ge=0.0,
        le=1.0,
    )
    raw: bool | None = Field(
        description=(
            "If true then image will be returned with less processing which can "
            "make people and places look more realistic. Use this when trying to "
            "enhance realism. This only works with the flux-1.1-pro-ultra model."
        ),
        default=False,
    )
    seed: int | None = Field(
        description=(
            "Random seed. Set when trying to exactly reproduce a generation. "
            "Set to -1 to use a random seed."
        ),
        default=-1,
    )
    describe: bool | None = Field(
        description=(
            "Whether to describe the image in detail. Use this when you want to "
            "understand better what generated image looks like. Use this while "
            "telling stories to better incorporate the image into the story."
        ),
        default=True,
    )


class ReplicateImageGenerationTool(BaseTool):
    name: str = "replicate_image_generation"
    description: str = (
        "Use this tool to generate an image using a text prompt on replicate.com "
        "and has access to a range of models. flux-1.1-pro is the best model for "
        "most use cases, from realistic or semi-realistic images to illustrations. "
        "It outputs very high resolution images and has the best consistency "
        "between images. The ultra variant outputs at a higher resolution at the "
        "cost of speed. flux-lora-isaac a fined tuned flux dev model for "
        "generating images of Isaac. Use ideogram-v2 for logos and posters. "
        "google/imagen-4 excels at fine detail rendering and typography with "
        "excellent photorealistic and abstract styles. When generating personality "
        "logos they must use a square aspect ratio and work well on a dark background."
    )

    args_schema: type[ReplicateImageGenerationToolArgs] = (
        ReplicateImageGenerationToolArgs
    )

    async def _process_image_prompt(
        self, image_url: str | None
    ) -> tuple[str | None, BufferedReader | None]:
        """Process the image prompt if provided."""
        tmp_upload_file = None
        image_prompt: BufferedReader | None = None
        if image_url:
            tmp_upload_file = os.path.join(neuron_config.temp_folder, uuid4().hex)
            # Generate proper signed session cookie for internal tool access
            cookies = None
            if neuron_config.static_require_auth:
                from neuron_server.controllers.csrf import create_session_cookie

                session_cookie, _ = create_session_cookie("system", include_csrf=False)
                cookies = {"neuron_session": session_cookie}

            async with (
                aiohttp.ClientSession(cookies=cookies) as session,
                session.get(image_url) as response,
            ):
                response.raise_for_status()
                image_data = BytesIO(await response.content.read())
                image = Image.open(image_data)
                image.save(tmp_upload_file, format="jpeg", quality=90)
            image_prompt = open(tmp_upload_file, "rb")  # noqa: SIM115
        return tmp_upload_file, image_prompt

    def _prepare_input_args(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str,
        num_inference_steps: int,
        image_options: dict[str, Any],
    ) -> dict[str, Any]:
        """Prepare input arguments for the model."""
        # Handle Google Imagen 4 specifically
        if model == "google/imagen-4":
            return {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "safety_filter_level": "block_only_high",
            }

        # Default arguments for other models
        input_args = {
            "prompt": prompt,
            "output_format": "png",
            "safety_tolerance": 6,
            "disable_safety_checker": True,
            "num_inference_steps": num_inference_steps,
            "raw": image_options.get("raw", False),
        }

        if "recraft" in model:
            input_args["size"] = RECRAFT_ASPECT_RATIO_TO_SIZE.get(
                aspect_ratio, "1024x1024"
            )
        else:
            input_args["aspect_ratio"] = aspect_ratio

        if image_options.get("image_prompt") is not None:
            input_args["image_prompt"] = image_options.get("image_prompt")
            input_args["image_prompt_strength"] = image_options.get(
                "image_prompt_strength"
            )

        input_args["seed"] = (
            image_options.get("seed")
            if image_options.get("seed") is not None and image_options.get("seed") != -1
            else random.randint(0, 2147483647)
        )

        if image_options.get("style") is not None:
            input_args["style"] = image_options.get("style")

        return input_args

    from dataclasses import dataclass

    @dataclass
    class ImageProcessingParams:
        model: str
        name: str
        input_args: dict[str, Any]
        prompt: str
        describe: bool
        config: RunnableConfig
        index: int

    async def _save_and_process_image(
        self,
        result: replicate.helpers.FileOutput,
        params: ImageProcessingParams,
    ) -> str:
        """Save and process a single generated image."""
        filename = safe_filename(
            params.model.replace("/", "_").split(":")[0],
            params.name,
            "png",
        )
        file_path = os.path.abspath(os.path.join(neuron_config.static_folder, filename))
        async with aiofiles.open(file_path, "wb") as file:
            async for chunk in result:
                await file.write(chunk)

        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("Description", params.name)
        pnginfo.add_text("Software", f"Model: {params.model}")
        pnginfo.add_text(
            "DateTimeOriginal",
            datetime.now().astimezone().isoformat(timespec="seconds"),
        )
        pnginfo.add_text(
            "Parameters",
            "\n".join(
                f"{key}={True if key == 'image_prompt' and value else value}"
                for key, value in params.input_args.items()
            ),
        )

        image = Image.open(file_path)
        described_image: ImageDescription | None = None
        if params.describe:
            logger.debug(f"Describing image #{params.index + 1}")
            described_image = await describe_image(params.prompt, image)
            pnginfo.add_text("Description", described_image.description)
            pnginfo.add_text("Caption", described_image.caption)

        image.save(file_path, format="png", pnginfo=pnginfo, quality=90, optimize=True)
        create_thumbnails(file_path)

        url = f"{neuron_config.static_content_url}/{filename}"
        create_params = MediaItemModel.CreateParams(
            thread_id=params.config["configurable"].get("thread_id"),
            user_id=params.config["configurable"].get("user_id"),
            url=url,
            media_type="image",
            name=described_image.caption if described_image else params.name,
            description=described_image.description if described_image else "",
        )
        media_item = await MediaItemModel.create(params=create_params)

        if described_image:
            return f"""\
<image id="{media_item.id}">
    <display>![{described_image.caption}]({url})</display>
    <description>{described_image.description}</description>
    <prompt_comparison>{described_image.prompt_comparison}</prompt_comparison>
</image>
"""
        return f"""\
<image id="{media_item.id}">
    <display>![{params.prompt}]({url})</display>
</image>
"""

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(
            self._arun(
                *args,
                **kwargs,
            )
        )

    async def _arun(  # noqa: PLR0913
        self,
        prompt: str,
        name: str,
        config: RunnableConfig,
        model: str = "black-forest-labs/flux-1.1-pro-ultra",
        aspect_ratio: str = "3:2",
        num_inference_steps: int = 25,
        style: str | None = None,
        image_url: str | None = None,
        raw: bool = False,
        image_prompt_strength: float | None = None,
        seed: int | None = None,
        describe: bool = True,
    ) -> str:
        logger.debug(f"Generating image using {model}")
        try:
            # Process image prompt if provided
            tmp_upload_file, image_prompt = await self._process_image_prompt(image_url)

            # Prepare input arguments
            image_options = {
                "style": style,
                "image_prompt": image_prompt,
                "raw": raw,
                "image_prompt_strength": image_prompt_strength,
                "seed": seed,
            }
            input_args = self._prepare_input_args(
                prompt=prompt,
                model=model,
                aspect_ratio=aspect_ratio,
                num_inference_steps=num_inference_steps,
                image_options=image_options,
            )

            output = await replicate.async_run(
                model,
                input=input_args,
            )
            if not isinstance(output, list):
                output = [output]

            results = []
            for i, result in enumerate(output):
                assert isinstance(result, replicate.helpers.FileOutput)
                params = self.ImageProcessingParams(
                    model=model,
                    name=name,
                    input_args=input_args,
                    prompt=prompt,
                    describe=describe,
                    config=config,
                    index=i,
                )
                results.append(await self._save_and_process_image(result, params))

            return "<images>\n" + "\n".join(results) + "\n</images>"
        except Exception as error:
            logger.error(error, exc_info=True)
            raise error
        finally:
            if tmp_upload_file and os.path.exists(tmp_upload_file):
                os.remove(tmp_upload_file)
