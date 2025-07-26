import asyncio
import os
from typing import Any, Literal
from uuid import uuid4

import aiohttp
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.tools.automatic1111_api import Automatic1111API, GenerationSettings

# HTTP status codes
HTTP_OK = 200

Automatic1111Checkpoints = Literal[
    "sdxl\\sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE",
    "sdxl\\betterThanWords_v30",
    "sdxl\\STOIQOAfroditexl_XL31",
    "sdxl\\dreamshaperXL_v21TurboDPMSDE",
]


class Automatic1111ToolArgs(BaseModel):
    name: str = Field(
        description=(
            "The title of the image. This will be used as the name of the media "
            "item in the database."
        )
    )
    prompt: str = Field(
        description=(
            "The prompt to generate the image from. When generating prompts, "
            "include specific visual details, such as colors, textures, and "
            "object placements, to guide the model toward a precise result. "
            "Mention the desired style (e.g., photorealistic, cartoonish, or "
            "abstract) and add context, like background elements or lighting, "
            "for more cohesive images. Focus on clarity and conciseness in "
            "each prompt to avoid ambiguity and ensure reproducible results."
        )
    )
    negative_prompt: str | None = Field(
        description="The negative prompt to use for generation."
    )
    steps: int | None = Field(
        description="The number of steps to use for generation", default=30
    )
    sd_model_checkpoint: Automatic1111Checkpoints | None = Field(
        description=(
            "The model checkpoint to use for generation. "
            "sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE is a general purpose model. "
            "betterThanWords_v30 is a realistic model for nudity. "
            "STOIQOAfroditexl_XL31 is a more photorealistic model. "
            "dreamshaperXL_v21TurboDPMSDE is the most creative model."
        ),
        default="sdxl\\sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE",
    )
    cfg_scale: float | None = Field(
        description="The CFG scale to use for generation.", default=4
    )
    enable_hr: bool | None = Field(
        description=(
            "Whether to enable high resolution (HR) upscaling. May introduce "
            "artifacts. Defaults to False."
        )
    )
    adetailer_enabled: bool | None = Field(
        description=(
            "Whether to enable ADetailer to improve details in faces. Enable when "
            "generating faces to improve details in faces. Defaults to False."
        )
    )


async def check_http_connection(url: str) -> bool:
    try:
        async with (
            aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session,
            session.head(url) as response,
        ):
            return response.status == HTTP_OK
    except Exception as e:
        logger.error(f"Connection to {url} failed: {str(e)}")
        return False


class Automatic1111Tool(BaseTool):
    name: str = "automatic1111"
    description: str = (
        "A tool that generates an image based on a given prompt using Automatic1111 "
        "hosted on the machine called Kepler on the local network. Use this when the "
        "user asks for an image. Do not use to generate charts. Returns a markdown "
        "image tag."
    )
    args_schema: type[Automatic1111ToolArgs] = Automatic1111ToolArgs
    response_format: str = "content_and_artifact"

    api: Automatic1111API

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0913
        self,
        prompt: str,
        name: str,
        config: RunnableConfig,
        negative_prompt: str | None = None,
        steps: int | None = 30,
        cfg_scale: float | None = 4,
        sd_model_checkpoint: Automatic1111Checkpoints | None = None,
        adetailer_enabled: bool | None = False,
        enable_hr: bool | None = False,
    ) -> str:
        """
        Runs the tool to generate an image based on the given prompt.
        Args:
            prompt (str): The prompt to generate the image from.
        Returns:
            str: A markdown string containing the generated image.
        """
        try:
            if not await check_http_connection(self.api.endpoint):
                raise Exception(
                    "Failed to connect to the Automatic1111 API. Ask the user to "
                    "verify Automatic1111 is running."
                )

            settings = GenerationSettings(
                prompt=prompt,
                negative_prompt=negative_prompt,
                sd_model_checkpoint=sd_model_checkpoint,
                steps=steps,
                cfg_scale=cfg_scale,
                adetailer_enabled=adetailer_enabled,
                enable_hr=enable_hr,
            )
            file_path = await self.api.generate(settings=settings)
            url = f"{neuron_config.static_content_url}/{os.path.basename(file_path)}"
            
            # Generate a real UUID for consistent ID between artifact and media_item
            media_id = uuid4()
            
            logger.debug(f"Saved generated image to {file_path} <{url}>")

            # Prepare artifact for UI using typed models
            from neuron_server.tools.artifact_types import (
                ToolArtifactMetadata,
                ToolMediaArtifact,
                ToolMediaItem,
            )

            metadata = ToolArtifactMetadata(
                model="automatic1111/stable-diffusion",
                prompt=prompt,
                negative_prompt=negative_prompt,
                num_inference_steps=steps,
                cfg_strength=cfg_scale,
            )

            artifact_item = ToolMediaItem(
                id=media_id,
                url=url,
                caption=name,
                description=prompt,
                metadata=metadata,
            )

            artifact = ToolMediaArtifact(media_type="image", items=[artifact_item])

            xml_content = f"""<image>
    <id>{media_id}</id>
    <url>{url}</url>
    <caption>{name}</caption>
    <description>{prompt}</description>
</image>"""

            return xml_content, [artifact.model_dump()]
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

    tool = Automatic1111Tool(
        api=Automatic1111API(
            output_directory=os.path.join(neuron_config.static_folder, "images")
        )
    )
    results = tool._run(
        prompt=args.prompt,
    )
    print(results)
