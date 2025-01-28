from typing import Literal

from pydantic import BaseModel

from neuron_server.event_router import IncomingEvent, OutgoingEvent


class GetImages(IncomingEvent):
    pass


class DeleteImage(IncomingEvent):
    image_id: str


class CreateImage(IncomingEvent):
    prompt: str
    guidance_scale: float | None = None
    num_inference_steps: int | None = None


class ImageFromDisk(BaseModel):
    id: str
    path: str
    image: str
    prompt: str
    created_at: str


class ImageResponse(OutgoingEvent):
    type: Literal["image"] = "image"
    image: ImageFromDisk
