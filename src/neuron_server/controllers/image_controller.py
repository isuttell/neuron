from quart import Blueprint
from neuron_server.event_router import EventRouter
import os
from PIL import Image
from neuron_server.config import config
from typing import Optional
from pydantic import BaseModel
import json
from datetime import datetime
import mimetypes
import hashlib
import aiofiles
from typing import List

router = EventRouter()


blueprint = Blueprint("image", __name__)


class MediaFile(BaseModel):
    id: str
    path: str
    url: str
    prompt: Optional[str]
    created_at: str
    size: int
    mime_type: str
    media_type: Optional[str]


async def get_media_files(directory: str, limit: int = 100) -> List[MediaFile]:
    results = []
    media_files = [
        (filename, os.stat(os.path.join(directory, filename)))
        for filename in os.listdir(directory)
        if os.path.splitext(filename)[1]
        in [".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mp3", ".wav"]
        and not any(substring in filename for substring in ["_t.", "_x.", "_xl."])
    ]
    # Sort by creation time so the newest are at the top
    media_files.sort(key=lambda x: x[1].st_ctime, reverse=True)
    for filename, stats in media_files[:limit]:
        ext = os.path.splitext(filename)[1]
        file_path = os.path.abspath(os.path.join(directory, filename))
        metadata_path = os.path.abspath(
            os.path.join(directory, filename.replace(ext, ".json"))
        )
        if os.path.exists(metadata_path):
            async with aiofiles.open(metadata_path, "r") as file:
                content = await file.read()
                metadata = json.loads(content)
                results.append(MediaFile(**metadata))
                continue
        prompt: Optional[str] = None
        created_at = datetime.fromtimestamp(stats.st_ctime).isoformat()
        if ext == ".png":
            with Image.open(file_path) as img:
                png_info = img.info
                prompt = png_info.get("Description", "")
                created_at = png_info.get("DateTimeOriginal", "")

        url = f"{config.static_content_url}/{filename}"
        mime_type = mimetypes.guess_type(file_path)[0]
        media_type = mime_type.split("/")[0]
        size = stats.st_size
        data = MediaFile(
            id=hashlib.md5(filename.encode("utf-8")).hexdigest(),
            path=file_path,
            url=url,
            prompt=prompt,
            created_at=created_at,
            mime_type=mime_type,
            media_type=media_type,
            size=size,
        )
        async with aiofiles.open(metadata_path, "w") as file:
            await file.write(data.model_dump_json(indent=4))
        results.append(data)
    return results


@blueprint.get("/")
async def get_images():
    return [
        image.model_dump(exclude={"path"})
        for image in await get_media_files(config.static_folder)
    ]
