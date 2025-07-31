"""Media utility functions for working with media files."""

from pathlib import Path
from typing import Optional

from neuron_server.util.subprocess_runner import run_subprocess


def get_media_type_from_extension(extension: str) -> str:  # noqa: PLR0911
    """
    Determine media type from file extension.

    Args:
        extension: File extension including the dot (e.g., ".jpg", ".mp3")

    Returns:
        Media type string: "image", "audio", "video", "html", "code", "text", or "data"
    """
    ext = extension.lower()

    # Image extensions
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg"]:
        return "image"

    # Audio extensions (including .webm for browser audio recordings)
    if ext in [".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".webm"]:
        return "audio"

    # Video extensions
    if ext in [".mp4", ".mov", ".avi", ".mkv", ".flv"]:
        return "video"

    # HTML files
    if ext in [".html", ".htm"]:
        return "html"

    # Code files
    if ext in [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp",
        ".c", ".cs", ".go", ".rb", ".php", ".swift", ".kotlin",
        ".scala", ".rust", ".rs"
    ]:
        return "code"

    # Markdown files (use "text" for markdown preview)
    if ext in [".md", ".markdown"]:
        return "text"

    # Text and data files
    if ext in [
        ".txt", ".json", ".csv", ".xml", ".yaml", ".yml",
        ".toml", ".ini", ".log", ".pdf"
    ]:
        return "data"

    # Default to data for other types (ensures files are at least downloadable)
    return "data"


async def get_media_duration(file_path: str | Path) -> Optional[float]:
    """
    Get the duration of a media file using ffprobe.

    Args:
        file_path: Path to the media file

    Returns:
        Duration in seconds as a float, or None if extraction fails
    """
    # Convert to string if Path object
    file_path_str = str(file_path)

    # Build ffprobe command
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        file_path_str,
    ]

    try:
        # Run ffprobe command
        process = await run_subprocess(command, capture_output=True, text=True)

        if process.returncode == 0 and process.stdout:
            # Parse duration from output
            duration_str = process.stdout.strip()
            return float(duration_str)
        # Log error if available
        if process.stderr:
            print(f"ffprobe error: {process.stderr}")
        return None

    except (ValueError, TypeError) as e:
        # Handle parsing errors
        print(f"Error parsing duration: {e}")
        return None
    except Exception as e:
        # Handle any other errors
        print(f"Unexpected error getting media duration: {e}")
        return None
