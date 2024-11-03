from typing import Literal, Optional
from neuron_server.event_router import OutgoingEvent, IncomingEvent
from neuron_server.models import ImageModel


class GetImages(IncomingEvent):
    pass


class DeleteImage(IncomingEvent):
    image_id: str


class CreateImage(IncomingEvent):
    prompt: str
    guidance_scale: Optional[float] = None
    num_inference_steps: Optional[int] = None


class ImageResponse(OutgoingEvent):
    type: Literal["image"] = "image"
    image: ImageModel
