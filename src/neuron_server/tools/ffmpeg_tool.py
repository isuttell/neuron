from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
from uuid import uuid4
from typing import List, Literal, Type
import os
import subprocess
from pydantic import BaseModel, Field
from neuron_server.util.slug import slugify


class FFmpegToolError(Exception):
    def __init__(self, message: str, stderr: str):
        self.message = message
        self.stderr = stderr

    def __str__(self):
        return f"Error generating audio: {self.message}\n\nSTDERR:\n{self.stderr}"


class FFmpegToolArgs(BaseModel):
    args: List[str] = Field(
        description="""\
ffmpeg arguments. Starting with a fixed base of arguments (ffmpeg -hide_banner -nostats -loglevel error -y), include all arguments required to do tasks such as join audio clips and integrate sound effects based on the user’s specifications. The tool avoids duplicating the initial arguments and focuses on creating a cohesive output according to the user's input for sequence, timing, and effects. The output filename and URL is automatically generated, appended to the args, and returned in the tool's response, ready for use.

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
    slug: str = Field(
        description="A unique identifier. Must be all lower case with no special characters or spaces. Use dashes for spaces. Keep it short and descriptive. Must be less than 256 characters",
    )


class FFmpegTool(BaseTool):
    name: str = "ffmpeg"
    description: str = (
        """
This tool is designed to manipulate video and audio using ffmpeg. Do not show the output filename to the user as they can't directly access it.
""".strip()
    )

    args_schema: Type[FFmpegToolArgs] = FFmpegToolArgs

    def _run(
        self, args: List[str], extension: Literal["mp3", "mp4", "wav"], slug: str
    ) -> str:
        process: subprocess.CompletedProcess
        try:
            # Remove any non-alphanumeric characters and limit to 255 characters
            slug = slugify(slug)

            # Concatenate all audio files using ffmpeg
            filename = f"ffmpeg_{uuid4().hex[:8]}_{slug}.{extension}"
            output = os.path.abspath(os.path.join(config.static_folder, filename))
            args = (
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-nostats",
                    "-loglevel",
                    "error",
                    "-y",
                ]
                + args
                + [output]
            )
            process = subprocess.run(
                args,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600,
            )
            if not os.path.exists(output):
                raise FFmpegToolError("Output file not found", process.stderr)
            url = config.static_content_url + "/" + filename
            logger.info(f"File saved to {output} <{url}>")
            return f"""
{ '<video src="{url}" controls></video>' if extension == "mp4" else '<audio src="{url}"></audio>' }
Filename: {output}
""".strip().format(
                url=url
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            if process:
                logger.error(process.stderr)
                raise FFmpegToolError(str(e), process.stderr)
            else:
                raise e
