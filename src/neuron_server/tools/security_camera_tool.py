from langchain_core.tools import BaseTool
from enum import Enum
import cv2
import numpy as np
from PIL import Image
import time
import asyncio
from neuron_server.logger import logger
from neuron_server.config import config
import PIL.PngImagePlugin as PngImagePlugin
from datetime import datetime, timezone


class CameraName(Enum):
    FRONT_DOOR = "front_door"
    BACKYARD = "backyard"
    GARAGE = "garage"
    KITTY_CAM = "kitty_cam"


devices = {
    CameraName.KITTY_CAM.value: "rtsps://192.168.1.1:7441/pLwvHCxMHH1xFCml?enableSrtp",
    CameraName.FRONT_DOOR.value: "rtsps://192.168.1.1:7441/Mmq8vE8VsAX4QxCk?enableSrtp",
    CameraName.BACKYARD.value: "rtsps://192.168.1.1:7441/Kw3HNdMJ60PvW204?enableSrtp",
    CameraName.GARAGE.value: "rtsps://192.168.1.1:7441/DKhbHhasEUaEYMMD?enableSrtpp",
}

device_descriptions = {
    CameraName.KITTY_CAM.value: "Kitty Cam (Master Bathroom)",
    CameraName.FRONT_DOOR.value: "Front Door & Yard (Outside)",
    CameraName.BACKYARD.value: "Backyard (Outside)",
    CameraName.GARAGE.value: "Garage (Indoors)",
}


class SecurityCameraTool(BaseTool):
    name: str = "security_camera"
    description: str = (
        "Returns a URL to an image captured from a security camera: front yard and door, backyard, inside the garage, and kitty cam in the master bathroom. This can either be used to show the user what is happening or to answer a question about what is happening when used with the inspect_image tool. Camera Names: front_door, backyard, garage, kitty_cam."
    )

    def _run(
        self,
        camera_name: CameraName,
    ) -> str:
        """
        Captures an image from the specified security camera and returns a URL to the image.

        Args:
            camera (str): The camera identifier to capture the image from. Must be one of the predefined cameras.

        Returns:
            str: The URL to the captured image.

        Raises:
            Exception: If the specified camera is not found or if there are issues opening the camera or reading frames.
        """
        camera: str = camera_name if isinstance(camera_name, str) else camera_name.value
        if camera not in devices:
            raise Exception(f"Camera {camera} not found")
        cap = cv2.VideoCapture(devices[camera])
        if not cap.isOpened():
            raise Exception("Could not open webcam.")

        start_time = time.perf_counter()
        frame = np.zeros((1, 1, 3), dtype=np.uint8)
        while np.mean(frame) < 10:
            ret, frame = cap.read()
            if not ret:
                raise Exception("Could not read frame")
            if time.perf_counter() - start_time > 10:
                raise Exception("Unable to read valid frame within 10s timeout")
            time.sleep(0.1)
        cap.release()
        frame = cv2.resize(frame.astype(np.uint8), (1024, 1024))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame)
        filename = f"{camera}_capture_{int(time.time())}.png"
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("Description", device_descriptions[camera])
        pnginfo.add_text(
            "Parameters",
            f"camera={camera}",
        )
        pnginfo.add_text(
            "DateTimeOriginal",
            datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        )
        file_path = f"{config.static_folder}/images/{filename}"
        image.save(file_path, format="png", pnginfo=pnginfo)
        url = f"{config.static_content_url}/images/{filename}"
        logger.debug(f"Saved camera image to {file_path} available at <{url}>")
        return url


async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the CameraTool to capture images from specified cameras."
    )
    parser.add_argument(
        "prompt", type=str, help="The prompt to send to the camera tool."
    )
    parser.add_argument(
        "--camera",
        type=str,
        choices=[camera.value for camera in CameraName],
        help="The camera to use.",
    )

    args = parser.parse_args()

    camera_tool = SecurityCameraTool()

    result = await camera_tool.run(prompt=args.prompt, camera=args.camera)
    print(result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
