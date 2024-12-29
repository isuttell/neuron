from quart import Blueprint
from neuron_server.event_router import EventRouter
import os
from PIL import Image
from neuron_server.config import config
from pydantic import BaseModel
import json

router = EventRouter()


blueprint = Blueprint("image", __name__)


class ImageFromDisk(BaseModel):
    id: str
    path: str
    image: str
    prompt: str
    created_at: str


def extract_prompts_from_directory(directory: str, max_images: int = 100):
    images = [
        (filename, os.stat(os.path.join(directory, filename)))
        for filename in os.listdir(directory)
        if filename.endswith(".png")
        and not any(substring in filename for substring in ["_t.", "_x.", "_xl."])
    ]
    # Sort by creation time so the newest images are at the top
    images.sort(key=lambda x: x[1].st_ctime, reverse=True)
    for filename, _ in images[:max_images]:
        file_path = os.path.abspath(os.path.join(directory, filename))
        metadata_path = os.path.abspath(
            os.path.join(directory, filename.replace(".png", ".json"))
        )
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as file:
                metadata = json.load(file)
                yield ImageFromDisk(**metadata)
                continue
        with Image.open(file_path) as img:
            png_info = img.info
            prompt = png_info.get("Description", "")
            created_at = png_info.get("DateTimeOriginal", "")
            url = f"{config.static_content_url}/{filename}"
            data = ImageFromDisk(
                id=str(abs(hash(os.path.basename(file_path)))),
                path=file_path,
                image=url,
                prompt=prompt,
                created_at=created_at,
            )
            with open(metadata_path, "w") as file:
                json.dump(data.model_dump(), file)
            yield data


@blueprint.get("/")
async def get_images():
    return [
        image.model_dump()
        for image in extract_prompts_from_directory(config.static_folder)
    ]
