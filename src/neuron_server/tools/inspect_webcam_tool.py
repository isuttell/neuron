import numpy as np
import cv2
from PIL import Image
import time
from threading import Thread
from neuron_server.logger import logger
from langchain.tools import BaseTool
from openai import OpenAI
import base64
from io import BytesIO


class Camera:
    def __init__(self, device=0):
        self.capture = cv2.VideoCapture(device)
        self.thread = Thread(target=self._update, args=())
        self.thread.daemon = True
        self.frame = None
        self.status = False
        self.thread.start()

    def _update(self):
        while True:
            if self.capture.isOpened():
                (self.status, self.frame) = self.capture.read()
            time.sleep(0.5)

    def get_frame(self):
        return self.status, self.frame

    def stop(self):
        self.capture.release()


class InspectWebcamTool(BaseTool):
    name: str = "inspect_webcam"
    description: str = (
        "Answer live questions about is happening in a webcam showing the user using OpenAI GPT-4o multi-modal vision capabilities. The prompt must include any relevant context that helps the model understand the question."
    )

    camera: Camera

    class Config:
        arbitrary_types_allowed = True

    def _run(self, prompt: str, max_tokens: int = 300) -> str:
        """
        Inspect an image from a webcam using OpenAI's GPT-4o multi-modal vision capabilities.

        Args:
            prompt (str): A question or prompt that guides the inspection of the image.
            max_tokens (int, optional): The maximum number of tokens to generate in the response. Defaults to 300.

        Returns:
            str: A description of the image based on the provided prompt.
        """
        try:
            start_time = time.perf_counter()
            while True:
                if time.perf_counter() - start_time > 10:
                    raise Exception("Timeout: No frame found after 10 seconds")
                status, frame = self.camera.get_frame()
                if not status:
                    time.sleep(0.25)
                    continue
                if np.mean(frame) > 10:
                    break
                time.sleep(0.1)
            logger.debug(f"Captured frame")
            frame = cv2.resize(frame.astype(np.uint8), (1024, 1024))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame)
            image_byte_array = BytesIO()
            image.save(image_byte_array, format="JPEG")
            image_base64 = base64.b64encode(image_byte_array.getvalue()).decode("utf-8")

            client: OpenAI = OpenAI()
            response = client.chat.completions.create(
                model="gpt-4o",
                temperature=0.7,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a tool that inspects a live webcam feed of the user and returns a description of the image based on a given prompt. Be descriptive and detailed. Just return the description, no other text. Do not ask for clarification.",
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                },
                            },
                        ],
                    },
                ],
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            logger.debug(
                f"Response: {content} - {round(time.perf_counter() - start_time, 2)}s"
            )
            return content
        except Exception as e:
            logger.exception(e)
            return f"I'm sorry, I couldn't inspect the webcam feed. {str(e)}"


async def main():
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
