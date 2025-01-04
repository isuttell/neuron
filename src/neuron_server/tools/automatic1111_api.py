import requests
import logging
from typing import List, Dict, Any, Optional
import base64
import io
from PIL import Image, PngImagePlugin
from pydantic import BaseModel
from uuid import uuid4
import os
from zoneinfo import ZoneInfo
from datetime import datetime
import time
import aiohttp
from neuron_server.util.image_utilities import create_thumbnails


class ImageGenerationOverrideSettings(BaseModel):
    sd_model_checkpoint: Optional[str] = None


class ImageGenerationSettings(BaseModel):
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    styles: Optional[List[str]] = None
    seed: Optional[int] = None
    subseed: Optional[int] = None
    subseed_strength: Optional[float] = None
    seed_resize_from_h: Optional[int] = None
    seed_resize_from_w: Optional[int] = None
    sampler_name: Optional[str] = None
    scheduler: Optional[str] = None
    batch_size: Optional[int] = None
    n_iter: Optional[int] = None
    steps: Optional[int] = None
    cfg_scale: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    restore_faces: Optional[bool] = None
    tiling: Optional[bool] = None
    do_not_save_samples: Optional[bool] = None
    do_not_save_grid: Optional[bool] = None
    eta: Optional[int] = None
    denoising_strength: Optional[float] = None
    s_min_uncond: Optional[int] = None
    s_churn: Optional[int] = None
    s_tmax: Optional[int] = None
    s_tmin: Optional[int] = None
    s_noise: Optional[int] = None
    override_settings: Optional[ImageGenerationOverrideSettings] = None
    override_settings_restore_afterwards: Optional[bool] = None
    refiner_checkpoint: Optional[str] = None
    refiner_switch_at: Optional[bool] = None
    disable_extra_networks: Optional[bool] = None
    firstpass_image: Optional[str] = None
    comments: Optional[Dict[str, Any]] = None
    enable_hr: Optional[bool] = None
    firstphase_width: Optional[bool] = None
    firstphase_height: Optional[bool] = None
    hr_scale: Optional[float] = None
    hr_upscaler: Optional[str] = None
    hr_second_pass_steps: Optional[int] = None
    hr_resize_x: Optional[int] = None
    hr_resize_y: Optional[int] = None
    hr_checkpoint_name: Optional[str] = None
    hr_sampler_name: Optional[str] = None
    hr_scheduler: Optional[str] = None
    hr_prompt: Optional[str] = None
    hr_negative_prompt: Optional[str] = None
    force_task_id: Optional[str] = None
    sampler_index: Optional[str] = None
    script_name: Optional[str] = None
    script_args: Optional[Dict[str, Any]] = None
    send_images: Optional[bool] = None
    save_images: Optional[bool] = None
    alwayson_scripts: Optional[Dict[str, Any]] = None
    infotext: Optional[str] = None


async def make_post(
    url: str, json: Dict[str, Any], timeout: int = 300
) -> Dict[str, Any]:
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
        self.output_directory = output_directory

    async def generate(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        steps: Optional[int] = 30,
        width: Optional[int] = 1024,
        height: Optional[int] = 1024,
        cfg_scale: Optional[float] = 6,
        sampler_name: Optional[str] = "Euler a",
        sd_model_checkpoint: Optional[
            str
        ] = "sdxl\sdxlNuclearGeneralPurposeV3Semi_v30BakedVAE",
        enable_hr: Optional[bool] = None,
        hr_upscaler: Optional[str] = "Latent",
        hr_scale: Optional[float] = 1.5,
        hr_resize_x: Optional[int] = None,
        hr_resize_y: Optional[int] = None,
        hr_second_pass_steps: Optional[int] = 20,
        denoising_strength: Optional[float] = 0.5,
        restore_faces: Optional[bool] = None,
        styles: List[str] = ["Default Negative Prompts"],
        adetailer_enabled: Optional[bool] = False,
        adetailer_model: Optional[str] = "face_yolov8s.pt",
        adetailer_denoising_strength: Optional[float] = 0.5,
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
        filename = os.path.join(self.output_directory, f"{uuid4()}.png")
        image.save(filename, quality=95, pnginfo=pnginfo)
        create_thumbnails(
            filename,
            os.path.dirname(filename),
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
