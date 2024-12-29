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
    model: Optional[
        Literal[
            "isuttell/flux-lora-isaac:c2c37f42d4f435bd70a75479e241890f07459b0b1828ede06a6030b21768ad2f",
            "black-forest-labs/flux-1.1-pro-ultra",
            "recraft-ai/recraft-20b",
        ]
    ] = Field(
        description="The model to use for the image generation. Use the flux-1.1-pro-ultra model for the best results and highest resolution images, and flux-lora-isaac when you need to generate images of Isaac. Use recraft-20b when trying to replicate a specific style",
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


class ReplicateImageGenerationTool(BaseTool):
    name: str = "replicate_image_generation"
    description: str = (
        """
Use this tool to generate an image using a text prompt on replicate.com. flux-1.1-pro-ultra is the best model for most use cases as it generates the highest quality results and typically matches the prompt the best. flux-lora-isaac a fined tuned flux dev model for generating images of Isaac.
""".strip()
    )

    args_schema: Type[ReplicateImageGenerationToolArgs] = (
        ReplicateImageGenerationToolArgs
    )

    def _run(
        self,
        prompt: str,
        model: str,
        aspect_ratio: str = "3:2",
        num_inference_steps: int = 25,
        style: Optional[str] = None,
        image_url: Optional[str] = None,
        raw: bool = False,
        image_prompt_strength: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> str:
        return asyncio.run(
            self._arun(
                prompt,
                model,
                aspect_ratio,
                num_inference_steps,
                style,
                image_url,
                raw,
                image_prompt_strength,
                seed,
            )
        )

    async def _arun(
        self,
        prompt: str,
        model: str = "black-forest-labs/flux-1.1-pro-ultra",
        aspect_ratio: str = "3:2",
        num_inference_steps: int = 25,
        style: Optional[str] = None,
        image_url: Optional[str] = None,
        raw: bool = False,
        image_prompt_strength: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> str:
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
            now = datetime.now(timezone.utc).astimezone()
            if not isinstance(output, list):
                output = [output]
            results = []
            for result in output:
                filename = f"replicate_image_{uuid4().hex}.png"
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
                image.save(file_path, format="png", pnginfo=pnginfo)

                url = f"{neuron_config.static_content_url}/{filename}"
                results.append(f"![{prompt}]({url})")
            return "\n".join(results)
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
