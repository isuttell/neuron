import hashlib
import os

import aiofiles
from PIL import Image
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.tools.document_utils import count_tokens
from neuron_server.util.image_utilities import create_thumbnails


async def process_uploaded_file(file: FileStorage) -> tuple[str, str, str]:
    """
    Process an uploaded file, handling validation, saving, and image conversion.

    Args:
        file: The uploaded file from the request

    Returns:
        Tuple containing (filename, file extension, public URL)

    Raises:
        BadRequest: If file type is invalid or file is too large
    """
    if file.filename is None:
        raise BadRequest("File has no filename")
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
            create_thumbnails(file_path)

    url = f"{neuron_config.static_content_url}/user/{filename}"
    return file_path, ext, url


async def extract_text_file_excerpt(
    file_path: str, max_tokens: int = 500, max_chars: int = 2000
) -> str:
    """
    Extract an excerpt from a text file for preview purposes.

    Args:
        file_path: Path to the text file
        max_tokens: Maximum number of tokens to extract (default: 500)
        max_chars: Maximum characters as a fallback limit (default: 2000)

    Returns:
        Excerpt of the file content, or empty string if unable to read
    """
    try:
        # Try reading with UTF-8 encoding first
        content = ""
        try:
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                # Read more than needed for token counting
                content = await f.read(max_chars * 2)
        except UnicodeDecodeError:
            # Fallback to latin-1 for files with encoding issues
            try:
                async with aiofiles.open(file_path, encoding="latin-1") as f:
                    content = await f.read(max_chars * 2)
            except Exception:
                content = ""

        if not content:
            return ""

        # Store original content length to detect truncation
        original_length = len(content)

        # If content is short enough, return it as-is
        if len(content) <= max_chars:
            token_count = count_tokens(content)
            if token_count <= max_tokens:
                return content

        # Extract excerpt based on token count
        return _extract_token_based_excerpt(
            content, max_tokens, max_chars, original_length
        )

    except Exception as e:
        logger.error(f"Error extracting text file excerpt from {file_path}: {e}")
        return ""


def _extract_token_based_excerpt(
    content: str, max_tokens: int, max_chars: int, original_length: int
) -> str:
    """Helper function to extract excerpt based on token count."""
    chunk_size = min(max_chars, len(content))
    min_chunk_size = 100

    while chunk_size > min_chunk_size:
        excerpt = content[:chunk_size]
        token_count = count_tokens(excerpt)

        if token_count <= max_tokens:
            # Try to end at a natural boundary (newline or sentence)
            for boundary in ["\n", ". ", "! ", "? "]:
                last_boundary = excerpt.rfind(boundary)
                if last_boundary > chunk_size * 0.8:  # Within 20% of the end
                    excerpt = excerpt[: last_boundary + len(boundary)].strip()
                    break
            else:
                excerpt = excerpt.strip()

            # Add truncation indicator if content was truncated
            was_truncated = len(excerpt) < original_length
            if was_truncated:
                return f"[EXCERPT - Truncated to {max_tokens} tokens]\n\n{excerpt}"
            return excerpt

        # Reduce chunk size for next iteration
        # Estimate based on token density
        avg_chars_per_token = chunk_size / token_count
        # 95% to ensure under limit
        chunk_size = int(max_tokens * avg_chars_per_token * 0.95)

    # Fallback to character limit if token counting fails
    excerpt = content[:max_chars].strip()
    if len(excerpt) < original_length:
        return f"[EXCERPT - Truncated to {max_chars} characters]\n\n{excerpt}"
    return excerpt
