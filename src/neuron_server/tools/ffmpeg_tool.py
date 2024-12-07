from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
from uuid import uuid4
from typing import List
import os
import subprocess
from typing import Literal


class FFmpegTool(BaseTool):
    name: str = "ffmpeg"
    description: str = (
        """
This tool is designed to manipulate video and audio using ffmpeg. Starting with a fixed base of arguments (ffmpeg -hide_banner -nostats -loglevel error -y), the LLM generates all additional arguments required to do tasks such as join audio clips and integrate sound effects based on the user’s specifications. The tool avoids duplicating the initial arguments and focuses on creating a cohesive output according to the user's input for sequence, timing, and effects. The output filename and URL is automatically generated, appended to the args, and returned in the tool's response, ready for use. Do not show the output filename to the user as they can't directly access it.

Example concat args to join audio files:

[
"-i",
"concat:file1.mp3|file2.mp3|file3.mp3",
"-c",
"copy"
]
""".strip()
    )

    def _run(self, args: List[str], extension: Literal["mp3", "mp4"] = "mp3") -> str:
        process: subprocess.CompletedProcess
        try:

            id = str(uuid4())
            # Concatenate all audio files using ffmpeg
            output_dir = config.static_folder + "/ffmpeg"
            os.makedirs(output_dir, exist_ok=True)
            filename = f"{id}.{extension}"
            output = os.path.abspath(output_dir + "/" + filename)
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
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            url = config.static_content_url + "/ffmpeg/" + filename
            logger.info(f"File saved to {output} <{url}>")
            return f"""
{ '<video src="{url}" controls></video>' if extension == "mp4" else '<audio src="{url}"></audio>' }
Filename: {output}
""".strip().format(
                url=url
            )
        except Exception as e:
            logger.exception(e)
            stderr_output = process.stderr.decode("utf-8") if process else "None"
            return f"Error generating audio: {str(e)}\n\nSTDERR:\n{stderr_output}"
