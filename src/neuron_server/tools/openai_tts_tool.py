from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
from uuid import uuid4
from neuron_server.util.script_parser import parse_script
import os
import shutil
import subprocess
from neuron_server.util.slug import safe_filename
from openai import AsyncOpenAI
from typing import List, Type
import asyncio
from pydantic import BaseModel, Field
import aiofiles

client = AsyncOpenAI(api_key=config.openai_api_key)


class OpenAITTSToolArgs(BaseModel):
    script: str = Field(
        description="""
The script to generate audio from. The script should be formatted as a list of spoken lines, with each line containing a voice identifier and the text to be spoken.

Supported voices:
<voices>
    <voice>alloy</voice>
    <voice>echo</voice>
    <voice>fable</voice>
    <voice>onyx</voice>
    <voice>nova</voice>
    <voice>shimmer</voice>
</voices>

<example>
[nova]
Welcome! I'm here to demonstrate our text-to-speech voices.

[alloy]
And I'll help explain how they sound different.
</example>
""".strip(),
    )
    speed: float = Field(
        description="The speed of the audio. 1 is normal speed. 0.5 is half speed. 2 is double speed. If the user wants it slightly faster user a value of 1.04 or in that range without distorting the audio.",
        default=1,
    )
    slug: str = Field(
        description="A unique identifier. Must be all lower case with no special characters or spaces. Use dashes for spaces. Keep it short and descriptive. Must be less than 256 characters",
    )


class OpenAITTSTool(BaseTool):
    name: str = "openai_tts"
    description: str = (
        """
The tool will use OpenAI's TTS API to generate the audio and return a link to the audio file. Write your input text to mimic natural, conversational speech. Use this tool by default over other TTS tools when the user requests you generate spoken audio.
""".strip()
    )
    args_schema: Type[OpenAITTSToolArgs] = OpenAITTSToolArgs

    async def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, script: str, slug: str, speed: float = 1) -> str:
        """
        Generates audio from a provided script. In the format of:
        ```
        [alloy]
        Hello, how are you?

        [echo]
        I'm great!
        ```
        """
        working_dir: str
        try:
            working_dir = os.path.abspath(os.path.join(config.temp_folder, uuid4().hex))
            os.makedirs(working_dir)
            audio_files: List[str] = []
            for index, line in enumerate(parse_script(script)):
                logger.debug(
                    f"Generating openai audio for line: [{line['voice']}] {line['text']}"
                )
                response = await client.audio.speech.create(
                    model="tts-1-hd",
                    voice=line["voice"],
                    input=line["text"],
                    speed=speed,
                )
                audio_file_path = os.path.abspath(
                    os.path.join(working_dir, f"line-{index}.mp3")
                )
                async with aiofiles.open(audio_file_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        await f.write(chunk)
                audio_files.append(audio_file_path)
                logger.debug(f"Saved generated audio chunk at {audio_file_path}")
            # Concatenate all audio files using ffmpeg
            filename = safe_filename("openai_tts", slug, "mp3")
            output = os.path.join(config.static_folder, filename)
            ffmpeg_command = [
                "ffmpeg",
                "-loglevel",
                "error",
                "-hide_banner",
                "-y",
                "-i",
                "concat:" + "|".join(audio_files),
                "-c",
                "copy",
                output,
            ]
            subprocess.run(ffmpeg_command, check=True)
            url = config.static_content_url + "/" + filename
            logger.debug(f"Generated audio file at {output} <{url}>")
            return f"""<audio src="{url}"></audio>""".strip()
        except Exception as e:
            logger.exception(e)
            raise e
        finally:
            if os.path.exists(working_dir):
                shutil.rmtree(working_dir)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate an audio file from text.")
    parser.add_argument(
        "script", type=str, help="The filename script to generate audio from."
    )
    args = parser.parse_args()

    # Call the tool to generate the audio
    tool = OpenAITTSTool()
    with open(args.script, "r") as f:
        script = "\n".join(f.readlines())
    results = tool._run(script)
    # Print the response
    print(results)


if __name__ == "__main__":
    main()
