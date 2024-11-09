from PIL import Image
from typing import Tuple
import numpy.typing as npt
import numpy as np


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
