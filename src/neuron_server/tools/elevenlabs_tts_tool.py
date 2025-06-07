import asyncio
import os
import shutil
import subprocess
from typing import Any, Literal
from uuid import uuid4

from elevenlabs import AsyncElevenLabs
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.slug import safe_filename
from neuron_server.util.subprocess_runner import run_subprocess
from neuron_server.util.text_cleaning import clean_action_text

AvailableVoices = Literal[
    "Aria",  # Expressive middle-aged American female
    "Roger",  # Confident middle-aged American male
    "Sarah",  # Soft young American female for news
    "Laura",  # Upbeat young American female
    "Charlie",  # Natural middle-aged Australian male
    "George",  # Warm middle-aged British male
    "Callum",  # Intense middle-aged Transatlantic male
    "River",  # Confident middle-aged American non-binary
    "Liam",  # Articulate young American male
    "Charlotte",  # Seductive young Swedish female
    "Alice",  # Confident middle-aged British female
    "Matilda",  # Friendly middle-aged American female
    "Will",  # Friendly young American male
    "Jessica",  # Expressive young American female
    "Eric",  # Friendly middle-aged American male
    "Chris",  # Casual middle-aged American male
    "Brian",  # Deep middle-aged American male
    "Daniel",  # Authoritative middle-aged British male
    "Lily",  # Warm middle-aged British female
    "Bill",  # Trustworthy older American male
    "Oxley - Evil Character",  # Raspy evil middle-aged American male
    "Scott - drill instructor",  # Crisp middle-aged British drill instructor
    "Isaac",  # Personal cloned voice
    "Sexy Female Villain Voice",  # Seductive young American female villain
    "Nassim - Corporate Narration",  # Deep middle-aged American male for
    # corporate narration
    "Donovan",  # Deep male hard boiled conversational voice
]


class VoiceLine(BaseModel):
    voice: AvailableVoices = Field(
        description="""\
Use one of the following voices for the speaker:
Aria: Middle-aged American female with expressive voice for social media
Roger: Middle-aged American male with confident voice for social media
Sarah: Young American female with soft voice for news
Laura: Young American female with upbeat voice for social media
Charlie: Middle-aged Australian male with natural conversational voice
George: Middle-aged British male with warm narration voice
Callum: Middle-aged male with intense Transatlantic accent for character work
River: Middle-aged American non-binary voice, confident for social media
Liam: Young American male with articulate voice for narration
Charlotte: Young Swedish female with seductive voice for character work
Alice: Middle-aged British female with confident voice for news
Matilda: Middle-aged American female with friendly narration voice
Will: Young American male with friendly voice for social media
Jessica: Young American female with expressive conversational voice
Eric: Middle-aged American male with friendly conversational voice
Chris: Middle-aged American male with casual conversational voice
Brian: Middle-aged American male with deep narration voice
Daniel: Middle-aged British male with authoritative voice for news
Lily: Middle-aged British female with warm narration voice
Bill: Older American male with trustworthy narration voice
Oxley - Evil Character: Middle-aged American male with raspy evil character voice
Scott - drill instructor: Middle-aged British male with crisp drill instructor voice
Isaac: Personal cloned voice
Sexy Female Villain Voice: Young American female with confident, seductive villain voice
Nassim: Middle-aged American male with deep voice for corporate narration
Donovan: Deep male voice with hard boiled conversational style
"""
    )
    text: str = Field(description="The text to be spoken.")


class ElevenLabsTTSToolArgs(BaseModel):
    script: list[VoiceLine] = Field(
        description=(
            "The script to generate audio from. The script should be formatted as a "
            "list of spoken lines, with each line containing a voice identifier and "
            "the text to be spoken. Specify pronunciation using SSML phoneme tags "
            '(CMU Arpabet). Use <break time="x.xs" /> for natural pauses up to 3 '
            "seconds. Convey emotions through narrative context"
        )
    )

    name: str = Field(
        description=(
            "A unique display title for the audio file to be generated. "
            "Must be less than 256 characters. "
            "Show to the user preceeding the subtitles to be spoken."
        ),
    )

    model: Literal["eleven_turbo_v2_5", "eleven_multilingual_v2"] | None = Field(
        description=(
            "The model to use for the TTS. Defaults to eleven_multilingual_v2 for "
            "quality and eleven_turbo_v2_5 for speed."
        ),
        default="eleven_turbo_v2_5",
    )


class ElevenLabsTTSTool(BaseTool):
    name: str = "elevenlabs_tts"
    description: str = """
This tool generates audio from a provided script using ElevenLabs' TTS APIs and
returns a link to the final audio file. Use this tool to generate high quality
audio for characters when the users requests it. This returns an audio tag to be
shown to the user so they can play it. Hide the filename as the user will not
need it.
""".strip()
    args_schema: type[ElevenLabsTTSToolArgs] = ElevenLabsTTSToolArgs

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        script: list[VoiceLine],
        name: str,
        config: RunnableConfig,
        model: Literal["eleven_turbo_v2_5", "eleven_multilingual_v2"]
        | None = "eleven_turbo_v2_5",
    ) -> str:
        try:
            logger.debug(f"Generating elevenlabs audio using {model}...")
            client = AsyncElevenLabs(api_key=neuron_config.elevenlabs_api_key)

            # Get voice mappings
            voice_map = await self._get_voice_mappings(client)

            working_dir = os.path.abspath(
                os.path.join(neuron_config.temp_folder, uuid4().hex)
            )
            os.makedirs(working_dir)
            audio_files: list[str] = []
            if len(script) == 0:
                raise ValueError("Failed to parse script. Found no lines.")

            for index, line in enumerate(script):
                cleaned_text = clean_action_text(line.text)
                logger.debug(
                    f"Generating elevenlabs audio for line: "
                    f"[{line.voice}] {cleaned_text}"
                )

                # Get voice ID from mapping
                voice_id = voice_map.get(line.voice)
                if not voice_id:
                    raise ValueError(
                        f"Voice '{line.voice}' not found in ElevenLabs voice list"
                    )

                # Use the new API method
                audio_stream = client.text_to_speech.stream(
                    text=cleaned_text,
                    voice_id=voice_id,
                    model_id=model,
                )

                audio_file_path = os.path.abspath(
                    os.path.join(working_dir, f"line-{index}.mp3")
                )
                audio_files.append(audio_file_path)

                # Write the stream to file
                with open(audio_file_path, "wb") as file:
                    async for chunk in audio_stream:
                        file.write(chunk)

                logger.debug(f"Saved generated audio chunk at {audio_file_path}")
            filename = safe_filename("elevenlabs_tts", name, "mp3")
            output = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )
            if len(audio_files) > 1:
                ffmpeg_command = [
                    "ffmpeg",
                    "-hide_banner",
                    "-nostats",
                    "-loglevel",
                    "error",
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
            logger.info(f"Generated audio file saved to {output} <{url}>")
            return f"""\
<audio id="{media_item.id}">
    <display><audio src="{url}"></audio></display>
</audio>"""
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
        finally:
            shutil.rmtree(working_dir)

    async def _get_voice_mappings(self, client: AsyncElevenLabs) -> dict[str, str]:
        """Get voice name to ID mappings from ElevenLabs API."""
        try:
            # Get voices from the API
            voices_response = await client.voices.get_all()
            voice_map = {}

            for voice in voices_response.voices:
                # Map voice name to ID
                voice_map[voice.name] = voice.voice_id

            logger.debug(f"Loaded {len(voice_map)} voice mappings from ElevenLabs API")
            return voice_map

        except Exception as e:
            logger.error(f"Failed to get voice mappings from API: {e}")
            raise RuntimeError(
                "Unable to retrieve voice list from ElevenLabs API. "
                "Please check your API key and connection."
            ) from e


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate an audio file from text.")
    parser.add_argument(
        "script", type=str, help="The filename script to generate audio from."
    )
    args = parser.parse_args()

    # Call the tool to generate the audio
    tool = ElevenLabsTTSTool()
    with open(args.script) as f:
        script = "\n".join(f.readlines())
    results = tool._run(script)
    # Print the response
    print(results)


if __name__ == "__main__":
    main()
