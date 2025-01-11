from PIL import Image
from typing import Tuple, List, Dict
import os
import logging

logger = logging.getLogger(__name__)


def resize_with_padding(
    image: Image.Image, target_size: Tuple[int, int]
) -> Image.Image:
    # Calculate scaling factor to fit within target size
    ratio = min(target_size[0] / image.width, target_size[1] / image.height)
    new_size = (int(image.width * ratio), int(image.height * ratio))

    # Resize image maintaining aspect ratio
    resized = image.resize(new_size)

    # Create new image with padding
    padded = Image.new("RGB", target_size, (0, 0, 0))

    # Calculate padding
    left = (target_size[0] - new_size[0]) // 2
    top = (target_size[1] - new_size[1]) // 2

    # Paste resized image onto padded background
    padded.paste(resized, (left, top))
    return padded


def create_thumbnails(
    filename: str,
    directory: str,
    sizes: Dict[str, int] = {"t": 512, "l": 768, "xl": 1024},
):
    logger.debug(f"Creating thumbnails for {filename} in {directory}")
    image = Image.open(filename)
    ext = os.path.splitext(filename)[1]
    basename = os.path.splitext(os.path.basename(filename))[0]
    for suffix, size in sizes.items():
        # Create a new image so we can strip
        # the extra metadata
        thumbnail = image.copy()
        thumbnail.thumbnail((size, size))
        thumbnail_filename = os.path.abspath(
            os.path.join(
                directory,
                f"{basename}_{suffix}{ext}",
            )
        )
        thumbnail.save(
            thumbnail_filename,
            optimize=True,
            quality=85,
        )
