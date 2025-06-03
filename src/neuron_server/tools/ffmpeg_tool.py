import asyncio
import os
import subprocess
from typing import Any, Literal
from uuid import uuid4

import aiofiles
import aiohttp
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

    @staticmethod
    def get_auth_cookies() -> dict[str, str] | None:
        """Get authentication cookies for requests.

        Returns:
            Optional dictionary of cookies for authentication
        """
        if neuron_config.static_require_auth:
            from neuron_server.controllers.csrf import create_session_cookie
            session_cookie, _ = create_session_cookie("system", include_csrf=False)
            return {"neuron_session": session_cookie}
        return None

    @staticmethod
    async def download_file_with_auth(
        url: str,
        cookies: dict[str, str] | None = None
    ) -> tuple[str, bool]:
        """Download a file with authentication and return the local path.

        Args:
            url: The URL to download
            cookies: Optional cookies to use for authentication

        Returns:
            Tuple of (file_path, is_temporary) where is_temporary indicates
            if the file should be deleted after use
        """
        if not url.startswith(neuron_config.static_content_url):
            return url, False  # Not a URL from our server, just return it

        # Use provided cookies or get new ones
        if cookies is None:
            cookies = FFmpegTool.get_auth_cookies()

        # Create a temporary file for download
        ext = os.path.splitext(url)[1]
        tmp_file = os.path.abspath(
            os.path.join(neuron_config.temp_folder, f"{uuid4().hex}{ext}")
        )

        # Download the file
        async with (
            aiohttp.ClientSession(cookies=cookies) as session,
            session.get(url) as response,
            aiofiles.open(tmp_file, "wb") as file,
        ):
            response.raise_for_status()
            await file.write(await response.content.read())

        return tmp_file, True

    @staticmethod
    async def process_url_argument(
        arg: str,
        cookies: dict[str, str] | None = None
    ) -> tuple[str, list[str]]:
        """Process a URL argument and download it if needed.

        Args:
            arg: The argument to process
            cookies: Optional cookies to use for authentication

        Returns:
            Tuple of (processed_arg, tmp_files) where tmp_files is a list of
            temporary files that should be deleted after use
        """
        tmp_files = []

        if arg.startswith(("http://", "https://")):
            local_path, is_temp = await FFmpegTool.download_file_with_auth(arg, cookies)
            if is_temp:
                tmp_files.append(local_path)
            return local_path, tmp_files

        return arg, tmp_files

    @staticmethod
    async def process_concat_argument(
        arg: str,
        cookies: dict[str, str] | None = None
    ) -> tuple[str, list[str]]:
        """Process a concat argument and download any URLs.

        Args:
            arg: The concat argument (e.g., "concat:file1.mp3|file2.mp3")
            cookies: Optional cookies to use for authentication

        Returns:
            Tuple of (processed_arg, tmp_files) where tmp_files is a list of
            temporary files that should be deleted after use
        """
        if not arg.startswith("concat:") or ":" not in arg:
            return arg, []

        concat_parts = arg.split(":", 1)[1].split("|")
        new_parts = []
        tmp_files = []

        for part in concat_parts:
            if part.startswith(("http://", "https://")):
                local_path, is_temp = await FFmpegTool.download_file_with_auth(
                    part, cookies
                )
                if is_temp:
                    tmp_files.append(local_path)
                new_parts.append(local_path)
            else:
                new_parts.append(part)

        return f"concat:{('|').join(new_parts)}", tmp_files

    @staticmethod
    async def preprocess_arguments(
        args: list[str],
        cookies: dict[str, str] | None = None
    ) -> tuple[list[str], list[str]]:
        """Process all arguments and download files as needed.

        Args:
            args: The input arguments
            cookies: Optional cookies to use for authentication

        Returns:
            Tuple of (processed_args, tmp_files) where tmp_files is a list of
            temporary files that should be deleted after use
        """
        if cookies is None:
            cookies = FFmpegTool.get_auth_cookies()

        modified_args = []
        tmp_files = []
        i = 0

        while i < len(args):
            if args[i] == "-i" and i + 1 < len(args):
                # Handle input file argument
                modified_args.append("-i")
                processed_arg, new_tmp_files = await FFmpegTool.process_url_argument(
                    args[i + 1], cookies
                )
                modified_args.append(processed_arg)
                tmp_files.extend(new_tmp_files)
                i += 2
            elif args[i].startswith("concat:"):
                # Handle concat argument
                processed_arg, new_tmp_files = await FFmpegTool.process_concat_argument(
                    args[i], cookies
                )
                modified_args.append(processed_arg)
                tmp_files.extend(new_tmp_files)
                i += 1
            else:
                # Pass through other arguments
                modified_args.append(args[i])
                i += 1

        return modified_args, tmp_files

    @staticmethod
    def get_output_format(extension: Literal["mp3", "mp4", "wav"]) -> str:
        """Get the output format HTML tag.

        Args:
            extension: The file extension

        Returns:
            HTML tag for displaying the file
        """
        if extension == "mp4":
            return '<video src="{url}" controls></video>'
        return '<audio src="{url}"></audio>'

    @staticmethod
    async def run_ffmpeg_command(
        command: list[str],
        cwd: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        """Run a ffmpeg command.

        Args:
            command: The ffmpeg command to run
            cwd: Optional working directory

        Returns:
            CompletedProcess with stdout and stderr

        Raises:
            FFmpegToolError: If the command fails
        """
        logger.info(f"Running: {' '.join(command)}")

        return await run_subprocess(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
            cwd=cwd,
        )

    @staticmethod
    def cleanup_temp_files(tmp_files: list[str]) -> None:
        """Clean up temporary files.

        Args:
            tmp_files: List of temporary files to delete
        """
        for tmp_file in tmp_files:
            if os.path.exists(tmp_file):
                try:
                    os.remove(tmp_file)
                except Exception as e:
                    logger.error(f"Error removing temporary file {tmp_file}: {e}")

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0912, PLR0915
        self,
        name: str,
        args: list[str],
        extension: Literal["mp3", "mp4", "wav"],
        config: RunnableConfig,
    ) -> str:
        process: subprocess.CompletedProcess[str] | None = None
        tmp_files: list[str] = []

        try:
            # Generate output filename and path
            filename = safe_filename("ffmpeg", name, extension)
            output = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )

            # Process arguments and download files
            cookies = self.get_auth_cookies()
            modified_args, tmp_files = await self.preprocess_arguments(args, cookies)

            # Prepare the final command
            command = (
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-nostats",
                    "-loglevel",
                    "error",
                ]
                + modified_args
                + [output]
            )

            # Run the ffmpeg command
            process = await self.run_ffmpeg_command(
                command,
                cwd=neuron_config.static_folder
            )

            # Check that output file exists
            if not os.path.exists(output):
                raise FFmpegToolError("Output file not found", process.stderr)

            # Create media item
            url = neuron_config.static_content_url + "/" + filename
            create_params = MediaItemModel.CreateParams(
                url=url,
                media_type="video" if extension == "mp4" else "audio",
                user_id=config["configurable"].get("user_id"),
                thread_id=config["configurable"].get("thread_id"),
                name=name,
            )
            await MediaItemModel.create(params=create_params)

            # Return formatted response
            logger.info(f"File saved to {output} <{url}>")
            output_format = self.get_output_format(extension)
            return f"""
{output_format}
Filename: {output}
""".strip().format(url=url)

        except Exception as e:
            logger.error(e, exc_info=True)
            if process:
                logger.error(process.stderr)
                raise FFmpegToolError(str(e), process.stderr) from e
            raise e
        finally:
            # Clean up temporary files
            self.cleanup_temp_files(tmp_files)
