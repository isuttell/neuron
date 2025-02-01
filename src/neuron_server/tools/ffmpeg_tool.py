import asyncio
import os
import subprocess
from typing import Any, Literal

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.slug import safe_filename
from neuron_server.util.subprocess_runner import run_subprocess


class FFmpegToolError(Exception):
    def __init__(self, message: str, stderr: str) -> None:
        self.message = message
        self.stderr = stderr

    def __str__(self) -> str:
        return f"Error generating audio: {self.message}\n\nSTDERR:\n{self.stderr}"


class FFmpegToolArgs(BaseModel):
    name: str = Field(
        description=(
            "A unique display title for the audio file to be generated. "
            "Must be less than 256 characters"
        ),
    )
    args: list[str] = Field(
        description="""\
ffmpeg arguments. Starting with a fixed base of arguments (ffmpeg -hide_banner
-nostats -loglevel error), include all arguments required to do tasks such as join
audio clips and integrate sound effects based on the user's specifications. The
tool avoids duplicating the initial arguments and focuses on creating a cohesive
output according to the user's input for sequence, timing, and effects. The output
filename and URL is automatically generated, appended to the args, and returned in
the tool's response, ready for use.

Example concat args to join audio files:
<example>
[
"-i",
"concat:file1.mp3|file2.mp3|file3.mp3",
"-c",
"copy"
]
</example>
                            """
    )
    extension: Literal["mp3", "mp4", "wav"] = Field(description="Output file extension")


class FFmpegTool(BaseTool):
    name: str = "ffmpeg"
    description: str = """
This tool is designed to manipulate video and audio using ffmpeg. Do not show the
output filename to the user as they can't directly access it.
""".strip()

    args_schema: type[FFmpegToolArgs] = FFmpegToolArgs

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        name: str,
        args: list[str],
        extension: Literal["mp3", "mp4", "wav"],
        config: RunnableConfig,
    ) -> str:
        process: subprocess.CompletedProcess[str]
        try:
            filename = safe_filename("ffmpeg", name, extension)
            output = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )
            args = (
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-nostats",
                    "-loglevel",
                    "error",
                ]
                + args
                + [output]
            )
            process = await run_subprocess(
                args,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,
                cwd=neuron_config.static_folder,
            )
            if not os.path.exists(output):
                raise FFmpegToolError("Output file not found", process.stderr)
            url = neuron_config.static_content_url + "/" + filename
            create_params = MediaItemModel.CreateParams(
                url=url,
                media_type="video" if extension == "mp4" else "audio",
                user_id=config["configurable"].get("user_id"),
                thread_id=config["configurable"].get("thread_id"),
                name=name,
            )
            await MediaItemModel.create(params=create_params)
            logger.info(f"File saved to {output} <{url}>")
            return f"""
{
                '<video src="{url}" controls></video>'
                if extension == "mp4"
                else '<audio src="{url}"></audio>'
            }
Filename: {output}
""".strip().format(url=url)
        except Exception as e:
            logger.error(e, exc_info=True)
            if process:
                logger.error(process.stderr)
                raise FFmpegToolError(str(e), process.stderr) from e
            raise e
