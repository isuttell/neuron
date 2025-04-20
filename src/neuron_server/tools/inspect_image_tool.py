import asyncio
import time
from io import BytesIO
from typing import Any, TypeVar

import aiohttp
import pandas as pd
import piexif
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig
from PIL import Image
from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.util.image_utilities import create_image_url

T = TypeVar("T")


class InspectImageToolArgs(BaseModel):
    image_url: str = Field(description=("The URL of the image to inspect."))
    prompt: str = Field(
        description=(
            "This should be a prompt with detailed and specific question(s) to be "
            "answered about the image."
        )
    )


async def get_image_bytes(image_url: str) -> bytes:
    async with aiohttp.ClientSession() as session, session.get(image_url) as response:
        response.raise_for_status()
        return await response.content.read()


# Constants for EXIF decoding
MIN_PRINTABLE_CHAR = 32
RATIONAL_DECIMAL_PLACES = 6
GPS_DECIMAL_PLACES = 6
ALTITUDE_DECIMAL_PLACES = 2
RATIONAL_TUPLE_LENGTH = 2


def decode_exif_value(value: T) -> str | float | list[int] | None:
    """Convert EXIF value to a readable format.

    Args:
        value: The EXIF value to decode, can be bytes, tuple, or other types

    Returns:
        Decoded value in an appropriate Python type (str, float, list, etc.)
    """
    if value is None:
        return None

    # Handle bytes
    if isinstance(value, bytes):
        return _decode_bytes_value(value)

    # Handle tuples
    if isinstance(value, tuple):
        return _decode_tuple_value(value)

    # Default case
    return value


def _decode_bytes_value(value: bytes) -> str | list[int]:
    """Helper function to decode bytes values."""
    try:
        # Try UTF-8 decoding first
        decoded = value.decode("utf-8").rstrip("\x00")
        # Check for control characters (except newline and tab)
        if any(ord(c) < MIN_PRINTABLE_CHAR and c not in "\n\t" for c in decoded):
            return list(value)
        return decoded.strip()
    except UnicodeDecodeError:
        try:
            return value.decode("ascii").strip()
        except Exception:
            return str(value)


def _decode_tuple_value(value: tuple) -> float | tuple:
    """Helper function to decode tuple values."""
    if len(value) == RATIONAL_TUPLE_LENGTH:
        try:
            # Handle rational numbers more safely
            numerator, denominator = float(value[0]), float(value[1])
            if denominator == 0:
                return 0
            return round(numerator / denominator, RATIONAL_DECIMAL_PLACES)
        except (TypeError, ValueError):
            return value
    return value


def get_tag_name(ifd_type: type[Any], tag_id: int) -> str:
    """Get the name of an EXIF tag from its ID."""
    for key, value in vars(ifd_type).items():
        if isinstance(value, int) and value == tag_id:
            return key
    return str(tag_id)


def convert_to_degrees(value: tuple[tuple[int | float, int | float], ...]) -> float:
    """Convert GPS coordinates from degrees/minutes/seconds to decimal degrees."""
    # GPS values come as tuples of tuples like ((x, 1), (y, 1), (z, 1))
    # Need to extract the first number from each tuple
    d = float(value[0][0]) / float(value[0][1])
    m = float(value[1][0]) / float(value[1][1])
    s = float(value[2][0]) / float(value[2][1])
    return d + (m / 60.0) + (s / 3600.0)


def get_exif_data(image: Image.Image) -> dict[str, Any]:
    """Extract EXIF data from an image."""
    metadata = {}
    exif = image.info.get("exif")

    if not exif:
        return metadata

    exif_dict = piexif.load(exif)

    if "Exif" in exif_dict and isinstance(exif_dict["Exif"], dict):
        for tag_id, value in exif_dict["Exif"].items():
            tag_name = get_tag_name(piexif.ExifIFD, tag_id)
            if tag_name == "MakerNote":
                continue
            try:
                decoded_value = decode_exif_value(value)
                metadata[f"EXIF {tag_name}"] = decoded_value
            except Exception as e:
                logger.error(f"Error decoding EXIF value for {tag_name}: {e}")

    # Extract GPS coordinates if available
    gps_info: dict[str, Any] = exif_dict.get("GPS", {})
    if gps_info:
        latitude = gps_info.get(piexif.GPSIFD.GPSLatitude)
        latitude_ref = gps_info.get(piexif.GPSIFD.GPSLatitudeRef)
        longitude = gps_info.get(piexif.GPSIFD.GPSLongitude)
        longitude_ref = gps_info.get(piexif.GPSIFD.GPSLongitudeRef)

        if latitude and latitude_ref and longitude and longitude_ref:
            lat = convert_to_degrees(latitude)
            if latitude_ref != b"N":
                lat = -lat

            lon = convert_to_degrees(longitude)
            if longitude_ref != b"E":
                lon = -lon
            metadata["GPS Latitude (Degrees)"] = round(lat, GPS_DECIMAL_PLACES)
            metadata["GPS Longitude (Degrees)"] = round(lon, GPS_DECIMAL_PLACES)

        altitude = gps_info.get(piexif.GPSIFD.GPSAltitude)
        altitude_ref = gps_info.get(piexif.GPSIFD.GPSAltitudeRef)
        # Convert altitude from rational number tuple
        if altitude:
            alt = float(altitude[0]) / float(altitude[1])
            # If altitude_ref is 1, altitude is below sea level
            if altitude_ref and altitude_ref == 1:
                alt = -alt
            metadata["GPS Altitude (m)"] = round(alt, ALTITUDE_DECIMAL_PLACES)

    return metadata


class InspectImageTool(BaseTool):
    name: str = "inspect_image"
    description: str = (
        "This tool uses multi-modal vision capabilities to inspect an image and "
        "return a detailed description along with any metadata that is available "
        "such as EXIF data. Use this tool when you need to answer a question "
        "about an image. For images generated with Neuron you can use this tool "
        "to find the original prompt and generation parameters."
    )
    args_schema: type[InspectImageToolArgs] = InspectImageToolArgs

    def _run(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        image_url: str,
        prompt: str,
        config: RunnableConfig,
    ) -> str:
        """
        Inspect an image using multi-modal vision capabilities.

        Args:
            image_url: The URL of the image to be inspected.
            prompt: A question or prompt that guides the inspection of the image.
            config: The runnable configuration.

        Returns:
            A description of the image based on the provided prompt.
        """
        try:
            start_time = time.perf_counter()
            logger.debug(f"Inspecting image {image_url} with prompt: {prompt}")
            # Download the image
            data = await get_image_bytes(image_url)
            image = Image.open(BytesIO(data))

            # Get metadata
            metadata = {
                "Filename": image_url.rsplit("/")[-1],
                "Image Height": image.height,
                "Image Width": image.width,
                "Image Format": image.format,
                "Image Mode": image.mode,
                "Image is Animated": getattr(image, "is_animated", False),
                "Frames in Image": getattr(image, "n_frames", 1),
            }
            if getattr(image, "text", None) and isinstance(image.text, dict):
                for key, value in image.text.items():
                    metadata[key] = value

            exif = get_exif_data(image)
            metadata.update(exif)

            df = pd.DataFrame(metadata.items(), columns=["Key", "Value"])
            image_url = create_image_url(image)

            from neuron_server.models.provider_model import ProviderModelModel

            # Inspect the image
            llm = await ProviderModelModel.get_active_llm()
            model = llm.model | StrOutputParser()
            system_prompt = (
                "You inspect images and return a description of the image based on "
                "a given prompt. Be long, descriptive and detailed. Another agent "
                "will handle the metadata, your job is to just return the "
                "description and not other text. Do not ask for clarification."
            )
            content: str = await model.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(
                        content=[
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": image_url},
                            },
                        ],
                    ),
                ],
                {
                    **(config or {}),
                    "run_name": "inspect_image",
                    "metadata": {
                        **(config or {}).get("metadata", {}),
                        "image_url": image_url,
                    },
                },
            )
            duration = time.perf_counter() - start_time
            logger.debug(f"Response: {content} - {duration:.2f}s")

            metadata_table = df.to_markdown(index=False)
            return (
                f"<description>{content}</description>\n"
                f"<metadata>\n{metadata_table}\n</metadata>"
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Inspect an image and return a description."
    )

    parser.add_argument(
        "--prompt",
        type=str,
        help="The prompt to guide the inspection.",
        default="Describe what you see in the image.",
    )
    parser.add_argument(
        "--image_url",
        type=str,
        help="The URL of the image to inspect.",
        default="http://192.168.1.211:5002/static/replicate_image_236f48a1b9e74382bb2013af8c45d850_xl.png",
    )
    args = parser.parse_args()

    # Call the model to get the description
    tool = InspectImageTool()
    results = await tool._arun(args.image_url, args.prompt, None)
    # Print the response
    print(results)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
