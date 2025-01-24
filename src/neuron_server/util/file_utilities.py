import os
import hashlib
from typing import Tuple
import aiofiles
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest
from PIL import Image
from neuron_server.config import config as neuron_config
from neuron_server.util.image_utilities import create_thumbnails


async def process_uploaded_file(file: FileStorage) -> Tuple[str, str, str]:
    """
    Process an uploaded file, handling validation, saving, and image conversion.

    Args:
        file: The uploaded file from the request

    Returns:
        Tuple containing (filename, file extension, public URL)

    Raises:
        BadRequest: If file type is invalid or file is too large
    """
    ext: str | None = os.path.splitext(file.filename)[1]
    ext = ext.lower() if ext else None
    if ext is None or ext not in neuron_config.allowed_file_types:
        raise BadRequest(f"Invalid file type: {ext}")

    # Create hash of file contents
    hasher = hashlib.sha256()
    file_contents: bytes = file.read()
    assert isinstance(file_contents, bytes)
    if len(file_contents) > neuron_config.max_file_size:
        raise BadRequest("File too large")
    hasher.update(file_contents)
    content_hash = hasher.hexdigest()

    filename = f"{content_hash}{ext}"
    file_path = os.path.abspath(
        os.path.join(neuron_config.static_folder, "user", filename)
    )

    # Only save if file doesn't already exist
    if not os.path.exists(file_path):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_contents)

        # Convert heic/heif to jpeg
        if ext in [".heic", ".heif"]:
            image = Image.open(file_path)
            filename = filename.replace(ext, ".jpg")
            file_path = file_path.replace(ext, ".jpg")
            ext = ".jpg"
            # Preserve EXIF data and use high quality for JPEG conversion
            exif = image.info.get("exif")
            image.save(file_path, format="JPEG", quality=95, exif=exif)

        if ext in [".jpg", ".jpeg", ".png", ".webp"]:
            create_thumbnails(
                file_path,
            )

    url = f"{neuron_config.static_content_url}/user/{filename}"
    return file_path, ext, url
