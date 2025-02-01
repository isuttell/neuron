import asyncio
import base64
import time
from datetime import datetime
from io import BytesIO
from threading import Thread
from typing import Literal

import cv2
import numpy as np
from cv2.typing import MatLike
from langchain.tools import BaseTool
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from PIL import Image
from pydantic import BaseModel, Field

from neuron_server.logger import logger

# Constants
MINIMUM_FRAME_BRIGHTNESS = 10  # Threshold for determining if a frame is valid
TIMEOUT_SECONDS = 10  # Maximum time to wait for a frame
FRAME_CHECK_INTERVAL = 0.25  # Time to wait between frame checks
FRAME_SLEEP_INTERVAL = 0.1  # Time to sleep between frame availability checks
CAMERA_UPDATE_INTERVAL = 0.5  # Time between camera frame updates
DEFAULT_IMAGE_DIMENSIONS = (1024, 1024)  # Default dimensions for frame resizing


class Camera:
    def __init__(self, device: int = 0) -> None:
        self.capture = cv2.VideoCapture(device)
        self.thread = Thread(target=self._update, args=())
        self.thread.daemon = True
        self.frame = None
        self.status = False
        self.thread.start()

    def _update(self) -> None:
        while True:
            if self.capture.isOpened():
                (self.status, self.frame) = self.capture.read()
            time.sleep(CAMERA_UPDATE_INTERVAL)

    def get_frame(self) -> tuple[bool, MatLike | None]:
        return self.status, self.frame

    def stop(self) -> None:
        self.capture.release()


def convert_frame_to_base64(
    frame: MatLike, dimensions: tuple[int, int] = DEFAULT_IMAGE_DIMENSIONS
) -> str:
    frame = cv2.resize(frame.astype(np.uint8), dimensions)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame)
    image_byte_array = BytesIO()
    image.save(image_byte_array, format="JPEG")
    return base64.b64encode(image_byte_array.getvalue()).decode("utf-8")


class InspectWebcamToolArgs(BaseModel):
    prompt: str = Field(
        description="A question or prompt that guides the inspection of the image."
    )
    frame_count: int = Field(description="The number of frames to inspect.", default=2)
    fps: float = Field(
        description="The frames per second of the webcam feed.", default=0.5
    )


class InspectWebcamTool(BaseTool):
    name: str = "inspect_webcam"
    description: str = (
        "Answer live questions about what is happening in a webcam showing the "
        "user using OpenAI GPT-4o multi-modal vision capabilities. The prompt "
        "must include any relevant context that helps the model understand the "
        "question."
    )

    args_schema: type[InspectWebcamToolArgs] = InspectWebcamToolArgs

    camera: Camera

    class Config:
        arbitrary_types_allowed = True

    def _run(self, prompt: str, max_tokens: int = 300) -> str:
        return asyncio.run(self._arun(prompt, max_tokens))

    async def wait_for_frame(self) -> None:
        start_time = time.perf_counter()
        while True:
            if time.perf_counter() - start_time > TIMEOUT_SECONDS:
                raise Exception(
                    f"Timeout: No frame found after {TIMEOUT_SECONDS} seconds"
                )
            status, frame = self.camera.get_frame()
            if not status:
                time.sleep(FRAME_CHECK_INTERVAL)
                continue
            if np.mean(frame) > MINIMUM_FRAME_BRIGHTNESS:
                return
            await asyncio.sleep(FRAME_SLEEP_INTERVAL)

    async def get_frames(self, count: int, fps: float) -> list[MatLike]:
        logger.debug("Waiting for frames to be available...")
        await self.wait_for_frame()
        logger.debug(f"Frames are available, getting {count} frames...")
        frames = []
        while len(frames) < count:
            status, frame = self.camera.get_frame()
            if not status:
                raise Exception("Camera disconnected")
            frames.append(frame)
            await asyncio.sleep(1 / fps)
        return frames

    async def _arun(
        self,
        prompt: str,
        frame_count: int,
        fps: float,
        max_tokens: int = 1000,
        provider: Literal["openai", "anthropic"] = "anthropic",
    ) -> str:
        try:
            start_time = time.perf_counter()
            frames = await self.get_frames(count=frame_count, fps=fps)
            image_base64s = [convert_frame_to_base64(frame) for frame in frames]
            model = (
                ChatAnthropic(
                    model="claude-3-5-sonnet-20241022",
                    temperature=0.7,
                )
                if provider == "anthropic"
                else ChatOpenAI(
                    model="gpt-4o",
                    temperature=0.7,
                )
            )
            chain = model | StrOutputParser()

            system_prompt = (
                "You are a tool that inspects a series of sequential images of a "
                "live webcam feed taken at {fps:.3f} fps. First give a general "
                "description of the scene in detail to provide context and then "
                "return a detailed response based on the given prompt. Be "
                "descriptive and detailed and include novel and related "
                "information another tool might need to know. Just return the "
                "description, no other text. Do not ask for clarification. The "
                "time is {time}"
            ).format(
                fps=round(fps, 3),
                time=datetime.now().astimezone().isoformat(timespec="seconds"),
            )

            content: str = await chain.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=[
                            {"type": "text", "text": prompt},
                            *[
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_base64}"
                                    },
                                }
                                for image_base64 in image_base64s
                            ],
                        ],
                    ),
                ],
                {
                    "run_name": "inspect_webcam",
                },
                max_tokens=max_tokens,
            )
            duration = time.perf_counter() - start_time
            logger.debug(f"Response: {content} - {duration:.2f}s")
            return content
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"I'm sorry, I couldn't inspect the webcam feed. {str(e)}"


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run the CameraTool to capture images from specified cameras."
    )
    parser.add_argument(
        "prompt", type=str, help="The prompt to send to the camera tool."
    )

    args = parser.parse_args()
    camera = Camera()
    camera_tool = InspectWebcamTool(camera=camera)

    result = camera_tool._run(prompt=args.prompt)
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
