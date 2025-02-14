import asyncio
import os
import shutil
import subprocess
from typing import Any, Literal
from uuid import uuid4

import aiofiles
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.slug import safe_filename
from neuron_server.util.subprocess_runner import run_subprocess
from neuron_server.util.text_cleaning import clean_action_text

client = AsyncOpenAI(api_key=neuron_config.openai_api_key)


class VoiceLine(BaseModel):
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = Field(
        description="The voice to use for the line."
    )
    text: str = Field(description="The text to be spoken.")


class OpenAITTSToolArgs(BaseModel):
    script: list[VoiceLine] = Field(
        description=(
            "The script to generate audio from. The script should be formatted as a list "  # noqa: E501
            "of spoken lines, with each line containing a voice identifier and the text "  # noqa: E501
            "to be spoken."
        )
    )
    speed: float = Field(
        description=(
            "The speed of the audio. 1 is normal speed. 0.5 is half speed. "
            "2 is double speed. If the user wants it slightly faster use a value "
            "of 1.04 or in that range without distorting the audio."
        ),
        default=1,
    )
    name: str = Field(
        description=(
            "A unique display title for the audio file to be generated. "
            "Must be less than 256 characters"
        ),
    )


class OpenAITTSTool(BaseTool):
    name: str = "openai_tts"
    description: str = (
        "The tool will use OpenAI's TTS API to generate the audio and return a link to "
        "the audio file. Write your input text to mimic natural, conversational speech. "  # noqa: E501
        "Use this tool by default over other TTS tools when the user requests you "
        "generate spoken audio."
    )
    args_schema: type[OpenAITTSToolArgs] = OpenAITTSToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        script: list[VoiceLine],
        name: str,
        config: RunnableConfig,
        speed: float = 1,
    ) -> str:
        working_dir: str
        try:
            working_dir = os.path.abspath(
                os.path.join(neuron_config.temp_folder, uuid4().hex)
            )
            os.makedirs(working_dir)
            if len(script) == 0:
                raise ValueError("Failed to parse script. Found no lines.")
            audio_files: list[str] = []

            for index, line in enumerate(script):
                cleaned_text = clean_action_text(line.text)
                logger.debug(
                    "Generating openai audio for line: [%s] %s",
                    line.voice,
                    cleaned_text,
                )
                response = await client.audio.speech.create(
                    model="tts-1-hd",
                    voice=line.voice,
                    input=cleaned_text,
                    speed=speed,
                )
                audio_file_path = os.path.abspath(
                    os.path.join(working_dir, f"line-{index}.mp3")
                )
                async with aiofiles.open(audio_file_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        await f.write(chunk)
                audio_files.append(audio_file_path)
                logger.debug("Saved generated audio chunk at %s", audio_file_path)
            # Concatenate all audio files using ffmpeg
            filename = safe_filename("openai_tts", name, "mp3")
            output = os.path.join(neuron_config.static_folder, filename)
            if len(audio_files) > 1:
                ffmpeg_command = [
                    "ffmpeg",
                    "-loglevel",
                    "error",
                    "-hide_banner",
                    "-i",
                    "concat:" + "|".join(audio_files),
                    "-c",
                    "copy",
                    output,
                ]
                await run_subprocess(
                    ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
            else:
                shutil.copy(audio_files[0], output)
            url = neuron_config.static_content_url + "/" + filename
            create_params = MediaItemModel.CreateParams(
                url=url,
                media_type="tts",
                user_id=config["configurable"].get("user_id"),
                thread_id=config["configurable"].get("thread_id"),
                name=name,
                description="\n".join(
                    [f"[{line.voice}]\n\n{line.text}" for line in script]
                ),
            )
            media_item = await MediaItemModel.create(params=create_params)
            logger.debug("Generated audio file at %s <%s>", output, url)
            return f"""\
<audio id="{media_item.id}">
    <display><audio src="{url}"></audio></display>
</audio>""".strip()
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
        finally:
            if os.path.exists(working_dir):
                shutil.rmtree(working_dir)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate an audio file from text.")
    parser.add_argument(
        "script", type=str, help="The filename script to generate audio from."
    )
    args = parser.parse_args()

    # Call the tool to generate the audio
    tool = OpenAITTSTool()
    with open(args.script) as f:
        script = "\n".join(f.readlines())
    results = tool._run(script)
    # Print the response
    print(results)


if __name__ == "__main__":
    main()
