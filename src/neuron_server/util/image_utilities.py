from typing import Tuple, Dict, Optional, List
import os
import logging
import base64
from io import BytesIO
from PIL import Image
from pi_heif import register_heif_opener

register_heif_opener()

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


def apply_exif_rotation(image: Image.Image) -> Image.Image:
    if hasattr(image, "_getexif"):  # Check if image has EXIF
        exif: Optional[Dict[int, int]] = image._getexif()
        if exif is not None:
            orientation = exif.get(274)  # 274 is the orientation tag
            if orientation is not None:
                # Rotation mapping
                rotate_values = {3: 180, 6: 270, 8: 90}
                if orientation in rotate_values:
                    return image.rotate(rotate_values[orientation], expand=True)
                elif orientation == 2:
                    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
                elif orientation == 4:
                    return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
                elif orientation == 5:
                    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT).rotate(
                        270, expand=True
                    )
                elif orientation == 7:
                    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT).rotate(
                        90, expand=True
                    )
    return image


ThumbnailSizeMap = {
    "t": 512,
    "l": 768,
    "xl": 1024,
    "xxl": 1536,
    "o": None,
}


def create_thumbnails(
    image_path: str,
    sizes: List[str] = [
        "t",
        "l",
        "xl",
        "xxl",
        "o",
    ],
) -> None:
    """
    Create thumbnails for an image in different sizes.

    Args:
        image_path: Path to the original image
        output_dir: Directory to save thumbnails
    """
    with Image.open(image_path) as image:
        # Calculate new dimensions maintaining aspect ratio
        width, height = image.size
        # Get base filename without extension
        base_path = os.path.splitext(image_path)[0]

        # Create thumbnails for each size
        for suffix in sizes:
            thumb = image.copy()
            max_size = ThumbnailSizeMap[suffix]
            if max_size:
                ratio = min(max_size / width, max_size / height)
                new_size = (int(width * ratio), int(height * ratio))
                # Only resize if the image is larger than target size
                if ratio < 1:
                    thumb = image.resize(new_size, Image.Resampling.LANCZOS)

            # Save as WebP with good quality
            thumb.save(
                f"{base_path}_{suffix}.webp",
                "webp",
                quality=85,
                method=6,
                lossless=False,
            )


def create_image_url(
    image: Image.Image,
    size: int = 1024,
) -> str:
    logger.debug(f"Creating base64 thumbnail")
    thumbnail = image.copy()

    # Resize image to ensure it's not too large
    thumbnail.thumbnail((size, size))

    # Convert to RGB if image has alpha channel
    if thumbnail.mode in ("RGBA", "LA") or (
        thumbnail.mode == "P" and "transparency" in thumbnail.info
    ):
        # Create a white background image
        background = Image.new("RGB", thumbnail.size, (255, 255, 255))
        if thumbnail.mode == "P":
            thumbnail = thumbnail.convert("RGBA")
        # Composite the image onto the background
        background.paste(thumbnail, mask=thumbnail.split()[-1])
        thumbnail = background

    thumbnail = apply_exif_rotation(thumbnail)

    buffered = BytesIO()
    thumbnail.save(
        buffered,
        format="jpeg",
        optimize=True,
        quality=85,
    )
    return f"data:image/jpeg;base64,{base64.b64encode(buffered.getvalue()).decode('utf-8')}"
