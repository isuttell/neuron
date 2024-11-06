from typing import Literal, Optional
from neuron_server.event_router import OutgoingEvent, IncomingEvent
from pydantic import BaseModel


class GetImages(IncomingEvent):
    pass


class DeleteImage(IncomingEvent):
    image_id: str


class CreateImage(IncomingEvent):
    prompt: str
    guidance_scale: Optional[float] = None
    num_inference_steps: Optional[int] = None


class ImageFromDisk(BaseModel):
    id: str
    path: str
    image: str
    prompt: str
    created_at: str


class ImageResponse(OutgoingEvent):
    type: Literal["image"] = "image"
    image: ImageFromDisk
