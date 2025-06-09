"""Media utility functions for working with media files."""

from pathlib import Path
from typing import Optional

from neuron_server.util.subprocess_runner import run_subprocess


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
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path_str
    ]

    try:
        # Run ffprobe command
        process = await run_subprocess(
            command,
            capture_output=True,
            text=True
        )

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
