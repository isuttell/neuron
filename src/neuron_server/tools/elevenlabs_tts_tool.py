from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
from huggingface_hub import AsyncInferenceClient
from uuid import uuid4
from typing import TypedDict, List
import os
import shutil
import subprocess
from elevenlabs import ElevenLabs
from neuron_server.logger import logger


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
This tool generates audio from a provided script. The input format should consist of speaker identifiers followed by their respective dialogues, formatted as the example below:

Supported Voices:
    Conversational: Chris, Eric, Charlie, Jessica, River, Laura, Aria
    Narrator: Bill, Brian, Lily, Matilda
    Character: Callum

Example:
```
[Chris]
Hello, how are you?

[Jessica]
I'm great!
```

The tool will use ElevenLabs' TTS API to generate the audio and return a link to the combined audio file. Each block should be short enough to be processed in a single call to the API. Use this tool to generate audio when the users requests it. The result should be an playable <audio> tag that users the src attribute to play the audio.
""".strip()
    )

    def _run(self, script: str) -> str:
        """
        Generates audio from a provided script. In the format of:
        ```
        [Alice]
        Hello, how are you?

        [Daniel]
        I'm great!
        ```
        """
        try:
            client = ElevenLabs(api_key=config.elevenlabs_api_key)
            id = str(uuid4())
            working_dir = config.temp_folder + "/" + id
            os.makedirs(working_dir, exist_ok=True)
            audio_files: List[str] = []
            for index, line in enumerate(parse_script(script)):
                response = client.generate(
                    text=line["text"],
                    voice=line["voice"],
                    model="eleven_multilingual_v2",
                )
                audio_file_path = working_dir + "/" + f"line-{index}.mp3"
                audio_files.append(audio_file_path)
                with open(audio_file_path, "wb") as file:
                    for chunk in response:
                        file.write(chunk)
                logger.debug(f"Saved generated audio chunk at {audio_file_path}")
            # Concatenate all audio files using ffmpeg
            output_dir = config.static_folder + "/tts"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            filename = f"{id}.mp3"
            output = output_dir + "/" + filename
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
            url = config.static_content_url + "/tts/" + filename
            logger.info(f"Generated audio file saved to {output} <{url}>")
            return url
        except Exception as e:
            logger.exception(e)
            return f"Error generating audio: {str(e)}"
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
    tool = ElevenLabsTTSTool(client=AsyncInferenceClient())
    with open(args.script, "r") as f:
        script = "\n".join(f.readlines())
    results = tool._run(script)
    # Print the response
    print(results)


if __name__ == "__main__":
    main()
