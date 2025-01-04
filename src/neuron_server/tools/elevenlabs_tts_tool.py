from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
from uuid import uuid4
from typing import TypedDict, List, Type
import os
import shutil
import subprocess
from elevenlabs import AsyncElevenLabs
from neuron_server.logger import logger
import asyncio
from pydantic import BaseModel, Field
from neuron_server.util.slug import safe_filename


class ElevenLabsTTSToolArgs(BaseModel):
    script: str = Field(
        description="""
The script format should consist of speaker identifiers followed by their respective dialogues, formatted as the example below:

<example>
[Chris]
Hello, how are you?

[Jessica]
I'm great!
</example>

Each script block should be short enough to be processed in a single call to the API.

Do not include action identifiers or cues in the script.

Use one of the following voices for the speaker. Exclude (voice description):

Conversational Voices:
Aria
Charlie
Chris
Eric
Jessica
Laura
River

Narrator Voices:
Bill
Brian
Lily
Matilda

News Presenter Voices:
Alice
Sarah

Character Voices:
Callum (male, middle-aged, intense)
Charlotte (female, Swedish)
Oxley - Evil Character
Sexy Female Villain Voice

Voice Clones:
Isaac
""".strip()
    )

    slug: str = Field(
        description="A unique identifier. Must be all lower case with no special characters or spaces. Use dashes for spaces. Keep it short and descriptive. Must be less than 256 characters",
    )


class SpokenLine(TypedDict):
    voice: str
    text: str


def parse_script(script: str) -> List[SpokenLine]:
    """
    Parses a script string and returns a list of dictionaries with 'voice' and 'message' keys.

    Args:
        script (str): The script string to parse.

    Returns:
        list[dict[str, str]]: A list of dictionaries containing 'voice' and 'message' keys.
    """
    lines = script.strip().split("\n")
    parsed_lines = []
    current_voice = None
    current_text = []

    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            if current_voice and current_text:
                parsed_lines.append(
                    {"voice": current_voice, "text": "\n".join(current_text)}
                )
            current_voice = line[1:-1]
            current_text = []
        elif current_voice and len(line.strip()) > 0:
            current_text.append(line)

    if current_voice and current_text:
        parsed_lines.append({"voice": current_voice, "text": "\n".join(current_text)})

    return parsed_lines


class ElevenLabsTTSTool(BaseTool):
    name: str = "elevenlabs_tts"
    description: str = (
        """
This tool generates audio from a provided script using ElevenLabs' TTS APIs and returns a link to the final audio file. Use this tool to generate audio when the users requests it. This returns an audio tag to be shown to the user so they can play it. Hide the filename as the user will not need it.
""".strip()
    )
    args_schema: Type[ElevenLabsTTSToolArgs] = ElevenLabsTTSToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, script: str, slug: str) -> str:
        try:
            client = AsyncElevenLabs(api_key=config.elevenlabs_api_key)
            working_dir = os.path.abspath(os.path.join(config.temp_folder, uuid4().hex))
            os.makedirs(working_dir)
            audio_files: List[str] = []
            for index, line in enumerate(parse_script(script)):
                logger.debug(
                    f"Generating elevenlabs audio for line: [{line['voice']}] {line['text']}"
                )
                response = await client.generate(
                    text=line["text"],
                    voice=line["voice"],
                    model="eleven_multilingual_v2",
                )
                audio_file_path = os.path.abspath(
                    os.path.join(working_dir, f"line-{index}.mp3")
                )
                audio_files.append(audio_file_path)
                with open(audio_file_path, "wb") as file:
                    async for chunk in response:
                        file.write(chunk)
                logger.debug(f"Saved generated audio chunk at {audio_file_path}")
            filename = safe_filename("elevenlabs_tts", slug, "mp3")
            output = os.path.abspath(os.path.join(config.static_folder, filename))
            ffmpeg_command = [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-loglevel",
                "error",
                "-y",
                "-i",
                "concat:" + "|".join(audio_files),
                "-c",
                "copy",
                output,
            ]
            subprocess.run(
                ffmpeg_command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            url = config.static_content_url + "/" + filename
            logger.info(f"Generated audio file saved to {output} <{url}>")
            return f'<audio src="{url}"></audio>'
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
        finally:
            shutil.rmtree(working_dir)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate an audio file from text.")
    parser.add_argument(
        "script", type=str, help="The filename script to generate audio from."
    )
    args = parser.parse_args()

    # Call the tool to generate the audio
    tool = ElevenLabsTTSTool()
    with open(args.script, "r") as f:
        script = "\n".join(f.readlines())
    results = tool._run(script)
    # Print the response
    print(results)


if __name__ == "__main__":
    main()
