from quart import websocket
from neuron_server.event_router import EventRouter
from neuron_server.logger import logger
from neuron_server.controllers.events.image_events import (
    CreateImage,
    ImageResponse,
    GetImages,
    DeleteImage,
)
from neuron_server.logger import logger
from neuron_server.models import ImageModel
from neuron_server.tools.hugging_face_serverless_image_generation_tool import (
    HuggingFaceServerlessImageGenerationTool,
)

router = EventRouter()

tool = HuggingFaceServerlessImageGenerationTool()


@router.on(GetImages)
async def get_images(event: GetImages):
    for image in ImageModel.list():
        await websocket.send(ImageResponse(image=image).model_dump_json())


@router.on(DeleteImage)
async def delete_image(event: DeleteImage):
    ImageModel.delete(event.image_id)


@router.on(CreateImage)
async def create_image(event: CreateImage):
    # Send initial response so the client knows we're working on it
    record = ImageModel.create(prompt=event.prompt, image="")
    await websocket.send(ImageResponse(image=record).model_dump_json())

    # Generate the image
    record.image = await tool._arun(event.prompt)
    record.save()

    # Send final response
    await websocket.send(ImageResponse(image=record).model_dump_json())
