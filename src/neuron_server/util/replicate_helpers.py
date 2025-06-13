import asyncio
import os
from typing import BinaryIO, Union

import aiofiles
import aiohttp


async def save_replicate_output(
    output: Union[str, bytes, BinaryIO, object],
    file_path: str,
) -> None:
    """
    Save Replicate output to a file, handling different output types.

    Args:
        output: The output from replicate.async_run()
        file_path: The absolute path where the file should be saved

    Raises:
        ValueError: If the output type is not supported
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # Handle different output types from Replicate
    if hasattr(output, "read"):
        # If output is a file-like object, read its content
        content = output.read()
        if asyncio.iscoroutine(content):
            content = await content
        async with aiofiles.open(file_path, "wb") as file:
            await file.write(content)
    elif isinstance(output, str) and output.startswith(("http://", "https://")):
        # If output is a URL, download it
        async with aiohttp.ClientSession() as session:  # noqa: SIM117
            async with session.get(output) as response:
                content = await response.read()
                async with aiofiles.open(file_path, "wb") as file:
                    await file.write(content)
    elif isinstance(output, bytes):
        # If output is already bytes, write directly
        async with aiofiles.open(file_path, "wb") as file:
            await file.write(output)
    else:
        raise ValueError(f"Unexpected output type from Replicate: {type(output)}")
