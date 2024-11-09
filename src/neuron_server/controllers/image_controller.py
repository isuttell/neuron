from quart import websocket
from neuron_server.event_router import EventRouter
from neuron_server.controllers.events.image_events import (
    ImageFromDisk,
    ImageResponse,
    GetImages,
)
import os
from PIL import Image
from neuron_server.config import config

router = EventRouter()


def extract_prompts_from_directory(directory: str):
    images = [
        (filename, os.stat(os.path.join(directory, filename)))
        for filename in os.listdir(directory)
        if filename.endswith(".png")
    ]
    # Sort by creation time so the newest images are at the top
    images.sort(key=lambda x: x[1].st_ctime, reverse=True)
    for filename, _ in images:
        file_path = os.path.abspath(os.path.join(directory, filename))
        with Image.open(file_path) as img:
            png_info = img.info
            prompt = png_info.get("Description", "")
            created_at = png_info.get("DateTimeOriginal", "")
            url = f"{config.static_content_url}/images/{filename}"
            yield ImageFromDisk(
                id=str(abs(hash(os.path.basename(file_path)))),
                path=file_path,
                image=url,
                prompt=prompt,
                created_at=created_at,
            )


@router.on(GetImages)
async def get_images(event: GetImages):
    for image in extract_prompts_from_directory(config.static_folder + "/images"):
        await websocket.send(ImageResponse(image=image).model_dump_json())
