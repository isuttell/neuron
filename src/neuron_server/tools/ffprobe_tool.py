import asyncio
import subprocess
from typing import Any

from langchain.tools import BaseTool

from neuron_server.logger import logger
from neuron_server.util.subprocess_runner import run_subprocess


class FFprobeTool(BaseTool):
    name: str = "ffprobe"
    description: str = """
This tool is designed to analyze video and audio using ffprobe. Starting with a fixed
base of arguments (ffprobe -hide_banner), the LLM generates all additional arguments
required to do tasks such inspect the duration, bitrate, and other metadata of a
video or audio file. The tool avoids duplicating the initial arguments and focuses
on creating the following functional set of arguments. Use this to determine the
actual duration of a generated piece of audio or video.
""".strip()

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, args: list[str]) -> str:
        process: subprocess.CompletedProcess[str]
        try:
            args = [
                "ffprobe",
                "-hide_banner",
            ] + args
            process = await run_subprocess(
                args,
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
