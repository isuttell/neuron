import subprocess

# Removed List, Type from typing import
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.util.subprocess_runner import run_subprocess


# Define the input schema for the tool
class FFprobeToolArgs(BaseModel):
    args: list[str] = Field(  # Changed List to list
        description=(
            "List of arguments to pass to ffprobe after 'ffprobe -hide_banner'"
        )
    )


class FFprobeTool(BaseTool):
    name: str = "ffprobe"
    args_schema: type[FFprobeToolArgs] = FFprobeToolArgs  # Changed Type to type
    description: str = """
This tool is designed to analyze video and audio using ffprobe. Starting with a fixed
base of arguments (ffprobe -hide_banner), the LLM generates all additional arguments
required to do tasks such inspect the duration, bitrate, and other metadata of a
video or audio file. The tool avoids duplicating the initial arguments and focuses
on creating the following functional set of arguments. Use this to determine the
actual duration of a generated piece of audio or video.
""".strip()

    def _run(self, args: list[str]) -> str:  # Changed List to list
        """Run ffprobe synchronously."""
        # This might require adjusting run_subprocess or using a sync alternative
        # For now, delegate to async version or raise error if sync isn't supported
        # Removed commented-out line: # return asyncio.run(self._arun(args=args))
        raise NotImplementedError("Synchronous execution not implemented for ffprobe")

    async def _arun(self, args: list[str]) -> str:  # Changed List to list
        """Run ffprobe asynchronously."""
        process: subprocess.CompletedProcess[str] | None = None
        try:
            args = [
                "ffprobe",
                "-hide_banner",
            ] + args
            command = [
                "ffprobe",
                "-hide_banner",
            ] + args
            process = await run_subprocess(
                command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout = process.stdout.decode("utf-8").strip()
            return f"""
ffprobe STDOUT:
{stdout}
""".strip()
        except Exception as e:
            logger.error(e, exc_info=True)
            stderr_output = process.stderr.decode("utf-8") if process else "None"
            return f"Error executing ffprobe: {str(e)}\n\nSTDERR:\n{stderr_output}"
