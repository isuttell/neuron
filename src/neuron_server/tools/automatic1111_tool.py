from langchain.tools import BaseTool
from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from typing import Literal, Type, Optional
from pydantic import BaseModel, Field
import asyncio
from neuron_server.tools.automatic1111_api import Automatic1111API
import os
from neuron_server.logger import logger
import aiohttp
from neuron_server.models.media_item_model import MediaItemModel
from langchain_core.runnables import RunnableConfig

Automatic1111Checkpoints = Literal[
    "sdxl\\sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE",
    "sdxl\\betterThanWords_v30",
    "sdxl\\STOIQOAfroditexl_XL31",
    "sdxl\\dreamshaperXL_v21TurboDPMSDE",
]


class Automatic1111ToolArgs(BaseModel):
    name: str = Field(
        description="The title of the image. This will be used as the name of the media item in the database."
    )
    prompt: str = Field(
        description="The prompt to generate the image from. When generating prompts, include specific visual details, such as colors, textures, and object placements, to guide the model toward a precise result. Mention the desired style (e.g., photorealistic, cartoonish, or abstract) and add context, like background elements or lighting, for more cohesive images. Focus on clarity and conciseness in each prompt to avoid ambiguity and ensure reproducible results."
    )
    negative_prompt: Optional[str] = Field(
        description="The negative prompt to use for generation."
    )
    steps: Optional[int] = Field(
        description="The number of steps to use for generation", default=30
    )
    sd_model_checkpoint: Optional[Automatic1111Checkpoints] = Field(
        description="The model checkpoint to use for generation. sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE is a general purpose model. betterThanWords_v30 is a realistic model for nudity. STOIQOAfroditexl_XL31 is a more photorealistic model. dreamshaperXL_v21TurboDPMSDE is the most creative model.",
        default="sdxl\\sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE",
    )
    cfg_scale: Optional[float] = Field(
        description="The CFG scale to use for generation.", default=4
    )
    enable_hr: Optional[bool] = Field(
        description="Whether to enable high resolution (HR) upscaling. May introduce artifacts. Defaults to False."
    )
    adetailer_enabled: Optional[bool] = Field(
        description="Whether to enable ADetailer to improve details in faces. Enable when generating faces to improve details in faces. Defaults to False."
    )


async def check_http_connection(url: str) -> bool:
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=5)
        ) as session:
            async with session.head(url) as response:
                return response.status == 200
    except Exception as e:
        logger.error(f"Connection to {url} failed: {str(e)}")
        return False


class Automatic1111Tool(BaseTool):
    name: str = "automatic1111"
    description: str = (
        "A tool that generates an image based on a given prompt using Automatic1111 hosted on the machine called Kepler on the local network. Use this when the user asks for an image. Do not use to generate charts. Returns a markdown image tag."
    )
    args_schema: Type[Automatic1111ToolArgs] = Automatic1111ToolArgs

    api: Automatic1111API

    def _run(
        self,
        *args,
        **kwargs,
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        prompt: str,
        name: str,
        config: RunnableConfig,
        negative_prompt: Optional[str] = None,
        steps: Optional[int] = 30,
        cfg_scale: Optional[float] = 4,
        sd_model_checkpoint: Optional[Automatic1111Checkpoints] = None,
        adetailer_enabled: Optional[bool] = False,
        enable_hr: Optional[bool] = False,
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
                    "Failed to connect to the Automatic1111 API. Ask the user to verify Automatic1111 is running."
                )

            file_path = await self.api.generate(
                prompt=prompt,
                negative_prompt=negative_prompt,
                sd_model_checkpoint=sd_model_checkpoint,
                steps=steps,
                cfg_scale=cfg_scale,
                adetailer_enabled=adetailer_enabled,
                enable_hr=enable_hr,
            )
            url = f"{neuron_config.static_content_url}/{os.path.basename(file_path)}"
            await MediaItemModel.create(
                thread_id=config["configurable"].get("thread_id"),
                user_id=config["configurable"].get("user_id"),
                url=url,
                type="image",
                name=name,
                description=prompt,
            )
            logger.debug(f"Saved generated image to {file_path} <{url}>")
            return f"<image>![{name}]({url})</image>"
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
