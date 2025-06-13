import base64
import io
import logging
import os
import time
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp
from PIL import Image, PngImagePlugin
from pydantic import BaseModel

from neuron_server.util.image_utilities import create_thumbnails
from neuron_server.util.slug import safe_filename


class GenerationSettings(BaseModel):
    """Settings for image generation with Automatic1111."""

    prompt: str
    negative_prompt: str | None = None
    steps: int = 30
    width: int = 1024
    height: int = 1024
    cfg_scale: float = 6
    sampler_name: str = "Euler a"
    sd_model_checkpoint: str = "sdxl\\sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE"
    enable_hr: bool | None = None
    hr_upscaler: str = "Latent"
    hr_scale: float = 1.5
    hr_resize_x: int | None = None
    hr_resize_y: int | None = None
    hr_second_pass_steps: int = 20
    denoising_strength: float = 0.5
    restore_faces: bool | None = None
    styles: list[str] = ["Default Negative Prompts"]
    adetailer_enabled: bool = False
    adetailer_model: str = "face_yolov8s.pt"
    adetailer_denoising_strength: float = 0.5


async def make_post(
    url: str, json: dict[str, Any], timeout: int = 300
) -> dict[str, Any]:
    try:
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                url, json=json, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response,
        ):
            response.raise_for_status()
            return await response.json()
    except aiohttp.ClientResponseError as err:
        body = await response.json()
        logging.error(body)
        raise err


class Automatic1111API:
    endpoint: str
    output_directory: str

    def __init__(
        self,
        output_directory: str,
        endpoint: str = "http://192.168.1.211:7860",
    ) -> None:
        self.endpoint = endpoint
        self.output_directory = os.path.abspath(output_directory)

    async def generate(self, settings: GenerationSettings) -> str:
        """Generate an image using the provided settings.

        Args:
            settings: The settings to use for generation.

        Returns:
            str: The path to the generated image file.
        """
        payload = settings.model_dump(exclude_none=True)
        payload["override_settings"] = {
            "sd_model_checkpoint": settings.sd_model_checkpoint
        }

        if settings.adetailer_enabled:
            payload["alwayson_scripts"] = {
                "ADetailer": {
                    "args": [
                        {
                            "ad_model": settings.adetailer_model,
                            "ad_denoising_strength": (
                                settings.adetailer_denoising_strength
                            ),
                        }
                    ]
                }
            }

        for key, value in payload.items():
            logging.debug(f"{key}={value}")
        logging.info(f"Generating: {settings.prompt}")
        url = f"{self.endpoint}/sdapi/v1/txt2img"
        start_time = time.perf_counter()
        body = await make_post(url, payload, timeout=300)
        logging.debug(f"POST {url} - {round(time.perf_counter() - start_time, 2)}s")
        image = Image.open(
            io.BytesIO(base64.b64decode(body["images"][0].split(",", 1)[0]))
        )
        logging.debug("Looking up image generation settings...")
        url = f"{self.endpoint}/sdapi/v1/png-info"
        logging.debug(f"POST {url}")
        params = await make_post(
            url=url,
            json={"image": "data:image/png;base64," + body["images"][0]},
            timeout=30,
        )
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("Description", settings.prompt)
        pnginfo.add_text("Software", f"Model: {settings.sd_model_checkpoint}")
        pnginfo.add_text(
            "DateTimeOriginal",
            datetime.now(tz=ZoneInfo("America/Los_Angeles")).isoformat(
                timespec="seconds"
            ),
        )
        pnginfo.add_text("Parameters", params.get("info", ""))
        filename = os.path.join(
            self.output_directory,
            safe_filename("automatic1111", "image", "png"),
        )
        image.save(filename, quality=95, pnginfo=pnginfo)
        create_thumbnails(
            filename,
        )
        logging.debug(f"Saved generated image to {filename}")
        return filename


if __name__ == "__main__":
    import argparse

    logging.getLogger("openai").setLevel(logging.INFO)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.basicConfig(level=logging.DEBUG)
    parser = argparse.ArgumentParser("automatic1111")
    parser.add_argument("prompt")
    parser.add_argument("--endpoint", type=str, default="http://192.168.1.211:7860")
    config = parser.parse_args()

    async def main() -> None:
        generator = Automatic1111API(endpoint=config.endpoint, output_directory=".")
        settings = GenerationSettings(prompt=config.prompt)
        await generator.generate(settings=settings)

    import asyncio

    asyncio.run(main())
