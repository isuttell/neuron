import asyncio
import base64
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from io import BytesIO
from typing import Any
from uuid import uuid4

import cv2
import numpy as np
from cv2.typing import MatLike
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from PIL import Image, PngImagePlugin
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.util.image_utilities import create_thumbnails


class CameraName(Enum):
    FRONT_DOOR = "front_door"
    BACKYARD = "backyard"
    GARAGE = "garage"
    KITTY_CAM = "kitty_cam"
    KITTY_CAM_2 = "kitty_cam_2"


devices = {
    CameraName.KITTY_CAM.value: "rtsps://192.168.1.1:7441/pLwvHCxMHH1xFCml?enableSrtp",
    CameraName.KITTY_CAM_2.value: "rtsps://192.168.1.1:7441/9dUHahBi84TK0EJ5?enableSrtp",
    CameraName.FRONT_DOOR.value: "rtsps://192.168.1.1:7441/Mmq8vE8VsAX4QxCk?enableSrtp",
    CameraName.BACKYARD.value: "rtsps://192.168.1.1:7441/Kw3HNdMJ60PvW204?enableSrtp",
    CameraName.GARAGE.value: "rtsps://192.168.1.1:7441/DKhbHhasEUaEYMMD?enableSrtpp",
}

device_descriptions = {
    CameraName.KITTY_CAM.value: "Kitty Cam (Master Bathroom)",
    CameraName.KITTY_CAM_2.value: "Kitty Cam II (Office)",
    CameraName.FRONT_DOOR.value: "Front Door & Yard (Outside)",
    CameraName.BACKYARD.value: "Backyard (Outside)",
    CameraName.GARAGE.value: "Garage (Indoors)",
}

# Constants for magic numbers
FRAME_BRIGHTNESS_THRESHOLD = 10
CAMERA_TIMEOUT_SECONDS = 10
JPEG_QUALITY = 80


@dataclass
class ImageInspectionConfig:
    """Configuration for image inspection."""

    prompt: str
    model: Runnable
    image_urls: list[str]
    start_time: datetime
    fps: float
    config: RunnableConfig | None = None


async def inspect_images(config: ImageInspectionConfig) -> str:
    """Inspect a series of images using an AI model."""
    logger.debug(
        f"Inspecting {len(config.image_urls)} images with prompt: {config.prompt}"
    )

    chain = config.model | StrOutputParser()
    return await chain.ainvoke(
        [
            SystemMessage(
                content=(
                    "You are a tool that inspects a sequential series of images and "
                    "returns a detailed description of the images for context and then "
                    "answers a given user's prompt. Be descriptive "
                    "and detailed as possible. Include related descriptions to the "
                    "prompt and include novel or unexpected information. Just return "
                    "the description, no other text. Do not ask for clarification."
                )
            ),
            HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": f"""
{config.prompt}

Parameters:
    Start Time: {config.start_time.astimezone().isoformat(timespec="seconds")}
    FPS: {config.fps}
                     """.strip(),
                    },
                    *[
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        }
                        for image_url in config.image_urls
                    ],
                ],
            ),
        ],
        {
            **(config.config or {}),
            "run_name": "inspect_camera_feed",
        },
    )


async def get_frames_from_camera(
    camera: str, frame_count: int = 1, fps: float = 1
) -> list[str]:
    """Capture frames from a security camera."""
    logger.debug(f"Getting {frame_count} frames from {camera} at {fps} FPS")
    cap = cv2.VideoCapture(devices[camera])
    if not cap.isOpened():
        raise Exception("Could not open webcam.")
    try:
        start_time = time.perf_counter()
        frame = np.zeros((1, 1, 3), dtype=np.uint8)
        # Wait for the camera to warm up and capture a valid frame
        while np.mean(frame) < FRAME_BRIGHTNESS_THRESHOLD:
            ret, frame = cap.read()
            if not ret:
                raise Exception("Could not read frame")
            if time.perf_counter() - start_time > CAMERA_TIMEOUT_SECONDS:
                raise Exception("Unable to read valid frame within 10s timeout")
            await asyncio.sleep(0.1)
        tasks = []
        while len(tasks) < frame_count:
            ret, frame = cap.read()
            if not ret:
                raise Exception("Could not read frame")
            logger.debug(f"Captured {camera} frame #{len(tasks)}")
            tasks.append(asyncio.create_task(convert_frame_to_image_url(frame)))
            await asyncio.sleep(1 / fps)
        return await asyncio.gather(*tasks)
    finally:
        cap.release()


async def convert_frame_to_image_url(
    frame: MatLike, max_dimensions: tuple[int, int] = (768, 2000)
) -> str:
    """Convert a camera frame to a base64 encoded image URL."""
    img = frame.astype(np.uint8)
    height, width, _ = img.shape
    max_height, max_width = max_dimensions
    if height > max_height or width > max_width:
        scaling_factor = min(max_height / height, max_width / width)
        new_dimensions = (int(width * scaling_factor), int(height * scaling_factor))
        img = cv2.resize(img, new_dimensions, interpolation=cv2.INTER_CUBIC)
    _, buffer = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])
    image_base64 = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{image_base64}"


@dataclass
class SaveImagesConfig:
    """Configuration for saving camera images."""

    image_urls: list[str]
    description: str
    camera: str
    start_time: datetime
    fps: float
    config: RunnableConfig


async def save_images(config: SaveImagesConfig) -> tuple[list[str], list[dict]]:
    """Save captured images to disk and return markdown URLs and artifacts."""
    results: list[str] = []
    artifacts: list[dict] = []
    
    for i, data_url in enumerate(config.image_urls):
        capture_time = config.start_time + timedelta(seconds=i / config.fps)
        image_data = base64.b64decode(data_url.split(",")[1])
        image = Image.open(BytesIO(image_data))
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("Description", config.description)
        pnginfo.add_text("Parameters", f"camera={config.camera}")
        pnginfo.add_text(
            "DateTimeOriginal",
            capture_time.astimezone().isoformat(timespec="seconds"),
        )

        timestamp = capture_time.strftime("%Y-%m-%d_%H-%M-%S-%f")
        filename = f"{config.camera}_capture_{timestamp}.png"
        file_path = os.path.abspath(os.path.join(neuron_config.static_folder, filename))
        image.save(file_path, format="png", pnginfo=pnginfo)
        url = f"{neuron_config.static_content_url}/{filename}"
        create_thumbnails(file_path)

        # Generate a real UUID for consistent ID between artifact and media_item
        media_id = uuid4()

        # Prepare artifact for UI using typed models
        from neuron_server.tools.artifact_types import (
            ToolArtifactMetadata,
            ToolMediaArtifact,
            ToolMediaItem,
        )

        metadata = ToolArtifactMetadata(
            model="security-camera",
            prompt=config.description,
            camera=config.camera,
            capture_time=capture_time.astimezone().isoformat(timespec='seconds'),
        )

        artifact_item = ToolMediaItem(
            id=media_id,
            url=url,
            caption=f"{device_descriptions[config.camera]} #{i + 1}",
            description=(
                f"Security camera capture from {config.camera} at "
                f"{capture_time.astimezone().isoformat(timespec='seconds')}"
                f"\n\nDescription:\n{config.description}"
            ),
            metadata=metadata,
        )

        artifact = ToolMediaArtifact(media_type="image", items=[artifact_item])
        artifacts.append(artifact.model_dump())

        timestamp = capture_time.astimezone().isoformat(timespec="seconds")
        results.append(
            f"""<image id="{media_id}">
    <display>![{config.camera} at {timestamp}]({url})</display>
</image>"""
        )

    return results, artifacts


class SecurityCameraToolArgs(BaseModel):
    prompt: str = Field(
        description=(
            "This prompt that tells the AI what to look for in the images. "
            "Be descriptive and detailed as possible."
        )
    )
    camera_name: CameraName = Field(
        description=(
            "The camera to use. Must be one of: front_door, backyard, garage, "
            "kitty_cam, kitty_cam_2"
        )
    )
    frame_count: int | None = Field(
        description="The number of frames to capture. Defaults to 1. Max is 10.",
        default=1,
    )
    fps: float | None = Field(
        description="The number of frames per second to capture. Defaults to 1.",
        default=1,
    )


@dataclass
class CameraConfig:
    """Configuration for camera operations."""

    prompt: str
    camera_name: CameraName
    config: RunnableConfig
    frame_count: int = 1
    fps: float = 1


class SecurityCameraTool(BaseTool):
    name: str = "security_camera"
    description: str = (
        "This tool captures a series of images from live security cameras and uses "
        "an AI to answer questions about them. The security cameras are located at: "
        "front yard and door, backyard, inside the garage, kitty cam in the "
        "master bathroom, and kitty cam 2 in the office. Use this tool to "
        "answer questions about what is happening outside or inside the house. "
        "For example, you can use this tool to answer questions like 'Is a "
        "package being delivered?' or 'Is anyone in the backyard?'. Show the most "
        "relevant image in your response."
    )
    args_schema: type[SecurityCameraToolArgs] = SecurityCameraToolArgs
    response_format: str = "content_and_artifact"

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0913
        self,
        prompt: str,
        camera_name: CameraName,
        config: RunnableConfig,
        frame_count: int | None = 1,
        fps: float | None = 1,
    ) -> str:
        try:
            camera: str = camera_name.value
            if camera not in devices:
                raise Exception(f"Camera {camera} not found")

            start_time = datetime.now()
            image_urls = await get_frames_from_camera(
                camera, frame_count=frame_count, fps=fps
            )
            from neuron_server.models.provider_model import ProviderModelModel

            llm = await ProviderModelModel.get_active_llm()

            # Ask the AI to analyze the images and save the results while we wait

            content = await inspect_images(
                ImageInspectionConfig(
                    prompt=prompt,
                    model=llm.model,
                    image_urls=image_urls,
                    start_time=start_time,
                    fps=fps,
                    config=config,
                )
            )

            markdown_urls, artifacts = await save_images(
                SaveImagesConfig(
                    image_urls=image_urls,
                    description=content,
                    camera=camera,
                    start_time=start_time,
                    fps=fps,
                    config=config,
                )
            )
            markdown_urls_str = "\n".join(markdown_urls)
            xml_content = f"""
{content}

<images>
{markdown_urls_str}
</images>
    """.strip()
            
            return xml_content, artifacts
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error capturing images from {camera}: {e}"


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the CameraTool to capture images from specified cameras."
    )
    parser.add_argument(
        "prompt", type=str, help="The prompt to send to the camera tool."
    )
    parser.add_argument(
        "--camera_name",
        type=str,
        choices=[camera.value for camera in CameraName],
        help="The camera to use.",
    )

    args = parser.parse_args()

    camera_tool = SecurityCameraTool()

    result = await camera_tool.ainvoke(
        {"camera_name": args.camera_name, "prompt": args.prompt, "frame_count": 1},
    )
    print(result)


if __name__ == "__main__":
    main()
