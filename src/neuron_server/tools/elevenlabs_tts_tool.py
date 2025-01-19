from langchain.tools import BaseTool
from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from uuid import uuid4
from typing import Type, List, Literal, Optional
import os
import shutil
import subprocess
from elevenlabs import AsyncElevenLabs
from neuron_server.logger import logger
import asyncio
from pydantic import BaseModel, Field
from neuron_server.util.slug import safe_filename
from neuron_server.util.script_parser import parse_script
from neuron_server.util.subprocess_runner import run_subprocess
from neuron_server.models.media_item_model import MediaItemModel
from langchain_core.runnables import RunnableConfig


class ElevenLabsTTSToolArgs(BaseModel):
    script: str = Field(
        description="""
The script format should consist of speaker identifiers followed by their respective dialogues, formatted as the example below:

Example:
\"\"\"
[Chris]
Hello, how are you?

[Jessica]
I'm great!
\"\"\"

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
George

News Presenter Voices:
Alice
Sarah
Daniel

Social Media Voices:
Laura
River
Roger
Will

Character Voices:
Callum (male, middle-aged, intense)
Charlotte (female, Swedish, seductive)
Sexy Female Villain Voice

Voice Clones:
Isaac
""".strip()
    )

    name: str = Field(
        description="A unique display title for the audio file to be generated. Must be less than 256 characters",
    )

    model: Optional[Literal["eleven_turbo_v2_5", "eleven_multilingual_v2"]] = Field(
        description="The model to use for the TTS. Defaults to eleven_multilingual_v2 for quality and eleven_turbo_v2_5 for speed.",
        default="eleven_turbo_v2_5",
    )


class ElevenLabsTTSTool(BaseTool):
    name: str = "elevenlabs_tts"
    description: str = (
        """
This tool generates audio from a provided script using ElevenLabs' TTS APIs and returns a link to the final audio file. Use this tool to generate high quality audio for characters when the users requests it. This returns an audio tag to be shown to the user so they can play it. Hide the filename as the user will not need it.
""".strip()
    )
    args_schema: Type[ElevenLabsTTSToolArgs] = ElevenLabsTTSToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        script: str,
        name: str,
        config: RunnableConfig,
        model: Optional[
            Literal["eleven_turbo_v2_5", "eleven_multilingual_v2"]
        ] = "eleven_turbo_v2_5",
    ) -> str:
        try:
            logger.debug(f"Generating elevenlabs audio using {model}...")
            client = AsyncElevenLabs(api_key=neuron_config.elevenlabs_api_key)
            working_dir = os.path.abspath(
                os.path.join(neuron_config.temp_folder, uuid4().hex)
            )
            os.makedirs(working_dir)
            audio_files: List[str] = []
            for index, line in enumerate(parse_script(script, remove_actions=True)):
                logger.debug(
                    f"Generating elevenlabs audio for line: [{line['voice']}] {line['text']}"
                )
                response = await client.generate(
                    text=line["text"],
                    voice=line["voice"],
                    model=model,
                )
                audio_file_path = os.path.abspath(
                    os.path.join(working_dir, f"line-{index}.mp3")
                )
                audio_files.append(audio_file_path)
                with open(audio_file_path, "wb") as file:
                    async for chunk in response:
                        file.write(chunk)
                logger.debug(f"Saved generated audio chunk at {audio_file_path}")
            filename = safe_filename("elevenlabs_tts", name, "mp3")
            output = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )
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
            await run_subprocess(
                ffmpeg_command,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            url = neuron_config.static_content_url + "/" + filename
            await MediaItemModel.create(
                url=url,
                type="audio",
                user_id=config["configurable"].get("user_id"),
                thread_id=config["configurable"].get("thread_id"),
                name=name,
                description=script,
            )
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
