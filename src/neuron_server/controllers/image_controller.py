import hashlib
import json
import logging
import mimetypes
import os
from datetime import datetime

import aiofiles
from PIL import Image
from pydantic import BaseModel
from quart import Blueprint

from neuron_server.config import config
from neuron_server.controllers.auth import requires_auth
from neuron_server.event_router import EventRouter

logger = logging.getLogger(__name__)

router = EventRouter()


blueprint = Blueprint("image", __name__)


class MediaFile(BaseModel):
    id: str
    path: str
    url: str
    prompt: str | None
    created_at: str
    size: int
    mime_type: str
    media_type: str | None


async def get_media_files(directory: str, limit: int = 100) -> list[MediaFile]:
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
        try:
            ext = os.path.splitext(filename)[1]
            if not ext:
                continue
            file_path = os.path.abspath(os.path.join(directory, filename))
            metadata_path = os.path.abspath(
                os.path.join(directory, filename.replace(ext, ".json"))
            )
            if os.path.exists(metadata_path):
                async with aiofiles.open(metadata_path) as file:
                    content = await file.read()
                    metadata = json.loads(content)
                    results.append(MediaFile(**metadata))
                    continue
            prompt: str | None = None
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
        except Exception as e:
            logger.error(f"Error processing media file {filename}: {e}")
    return results


@blueprint.get("/")
@requires_auth
async def get_images():
    return [
        image.model_dump(exclude={"path"})
        for image in await get_media_files(config.static_folder)
    ]
