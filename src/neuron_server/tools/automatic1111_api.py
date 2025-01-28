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


class ImageGenerationOverrideSettings(BaseModel):
    sd_model_checkpoint: str | None = None


class ImageGenerationSettings(BaseModel):
    prompt: str | None = None
    negative_prompt: str | None = None
    styles: list[str] | None = None
    seed: int | None = None
    subseed: int | None = None
    subseed_strength: float | None = None
    seed_resize_from_h: int | None = None
    seed_resize_from_w: int | None = None
    sampler_name: str | None = None
    scheduler: str | None = None
    batch_size: int | None = None
    n_iter: int | None = None
    steps: int | None = None
    cfg_scale: float | None = None
    width: int | None = None
    height: int | None = None
    restore_faces: bool | None = None
    tiling: bool | None = None
    do_not_save_samples: bool | None = None
    do_not_save_grid: bool | None = None
    eta: int | None = None
    denoising_strength: float | None = None
    s_min_uncond: int | None = None
    s_churn: int | None = None
    s_tmax: int | None = None
    s_tmin: int | None = None
    s_noise: int | None = None
    override_settings: ImageGenerationOverrideSettings | None = None
    override_settings_restore_afterwards: bool | None = None
    refiner_checkpoint: str | None = None
    refiner_switch_at: bool | None = None
    disable_extra_networks: bool | None = None
    firstpass_image: str | None = None
    comments: dict[str, Any] | None = None
    enable_hr: bool | None = None
    firstphase_width: bool | None = None
    firstphase_height: bool | None = None
    hr_scale: float | None = None
    hr_upscaler: str | None = None
    hr_second_pass_steps: int | None = None
    hr_resize_x: int | None = None
    hr_resize_y: int | None = None
    hr_checkpoint_name: str | None = None
    hr_sampler_name: str | None = None
    hr_scheduler: str | None = None
    hr_prompt: str | None = None
    hr_negative_prompt: str | None = None
    force_task_id: str | None = None
    sampler_index: str | None = None
    script_name: str | None = None
    script_args: dict[str, Any] | None = None
    send_images: bool | None = None
    save_images: bool | None = None
    alwayson_scripts: dict[str, Any] | None = None
    infotext: str | None = None


async def make_post(
    url: str, json: dict[str, Any], timeout: int = 300
) -> dict[str, Any]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=json, timeout=timeout) as response:
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

    async def generate(
        self,
        prompt: str,
        negative_prompt: str | None = None,
        steps: int | None = 30,
        width: int | None = 1024,
        height: int | None = 1024,
        cfg_scale: float | None = 6,
        sampler_name: str | None = "Euler a",
        sd_model_checkpoint: str | None = "sdxl\sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE",
        enable_hr: bool | None = None,
        hr_upscaler: str | None = "Latent",
        hr_scale: float | None = 1.5,
        hr_resize_x: int | None = None,
        hr_resize_y: int | None = None,
        hr_second_pass_steps: int | None = 20,
        denoising_strength: float | None = 0.5,
        restore_faces: bool | None = None,
        styles: list[str] = ["Default Negative Prompts"],
        adetailer_enabled: bool | None = False,
        adetailer_model: str | None = "face_yolov8s.pt",
        adetailer_denoising_strength: float | None = 0.5,
    ) -> str:
        alwayson_scripts = {}

        if adetailer_enabled:
            alwayson_scripts["ADetailer"] = {
                "args": [
                    {
                        "ad_model": adetailer_model,
                        "ad_denoising_strength": adetailer_denoising_strength,
                    }
                ]
            }

        settings = ImageGenerationSettings(
            prompt=prompt,
            negative_prompt=negative_prompt,
            steps=steps,
            cfg_scale=cfg_scale,
            sampler_name=sampler_name,
            width=width,
            height=height,
            restore_faces=restore_faces,
            enable_hr=enable_hr,
            hr_scale=hr_scale,
            hr_resize_x=hr_resize_x,
            hr_resize_y=hr_resize_y,
            hr_upscaler=hr_upscaler,
            denoising_strength=denoising_strength,
            hr_second_pass_steps=hr_second_pass_steps,
            styles=styles,
            override_settings=ImageGenerationOverrideSettings(
                sd_model_checkpoint=sd_model_checkpoint
            ),
            alwayson_scripts=alwayson_scripts,
        )

        for key, value in settings.model_dump(
            exclude_none=True, exclude_unset=True
        ).items():
            logging.debug(f"{key}={value}")
        logging.info(f"Generating: {prompt}")
        url = f"{self.endpoint}/sdapi/v1/txt2img"
        start_time = time.perf_counter()
        body = await make_post(
            url, settings.model_dump(exclude_none=True, exclude_unset=True), timeout=300
        )
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
        pnginfo.add_text("Description", prompt)
        pnginfo.add_text("Software", f"Model: {sd_model_checkpoint}")
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

    generator = Automatic1111API(endpoint=config.endpoint)
    generator.generate(prompt=config.prompt)
