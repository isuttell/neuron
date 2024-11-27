from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
from uuid import uuid4
from typing import TypedDict, List
from openai import OpenAI
import os
import shutil
import subprocess


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

    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current_voice = line[1:-1]
        elif current_voice and len(line.strip()) > 0:
            parsed_lines.append({"voice": current_voice, "text": line})
    return parsed_lines


class OpenAITTSTool(BaseTool):
    name: str = "openai_tts"
    description: str = (
        """
This tool generates audio from a provided script. The input format should consist of speaker identifiers followed by their respective dialogues, formatted as the example below:

Supported voices: alloy, echo, fable, onyx, nova, and shimmer

Example:
```
[alloy]
Hello, how are you?

[echo]
I'm great!
```

The tool will use OpenAI's TTS API to generate the audio and return a link to the combined audio file. Each block should be short enough to be processed in a single call to the API. Write your input text to mimic natural, conversational speech. Use punctuation like commas and periods to create pauses and guide the intonation, and add words like "Hmm," "Ah," or "Oh" for a more human touch. Use this tool to generate audio when the users requests it. The result should be an playable <audio> tag but not the filename.
""".strip()
    )

    def _run(self, script: str, speed: float = 1) -> str:
        """
        Generates audio from a provided script. In the format of:
        ```
        [alloy]
        Hello, how are you?

        [echo]
        I'm great!
        ```
        """
        try:
            client = OpenAI(api_key=config.openai_api_key)
            id = str(uuid4())
            working_dir = config.temp_folder + "/" + id
            os.makedirs(working_dir, exist_ok=True)
            audio_files: str = []
            for index, line in enumerate(parse_script(script)):
                print(f"Generating line #{index}")
                response = client.audio.speech.create(
                    model="tts-1-hd",
                    voice=line["voice"],
                    input=line["text"],
                    speed=speed,
                )
                audio_file_path = working_dir + "/" + f"line-{index}.mp3"
                response.stream_to_file(audio_file_path)
                audio_files.append(audio_file_path)
            # Concatenate all audio files using ffmpeg
            output_dir = config.static_folder + "/tts"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            filename = f"{id}.mp3"
            output = output_dir + "/" + filename
            ffmpeg_command = [
                "ffmpeg",
                "-y",
                "-i",
                "concat:" + "|".join(audio_files),
                "-c",
                "copy",
                output,
            ]
            subprocess.run(ffmpeg_command, check=True)
            url = config.static_content_url + "/tts/" + filename
            logger.info(f"Generated audio file at {output} <{url}>")
            return f"""
<audio src="{url}"></audio>
Filename: {output}
""".strip()
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
    tool = OpenAITTSTool()
    with open(args.script, "r") as f:
        script = "\n".join(f.readlines())
    results = tool._run(script)
    # Print the response
    print(results)


if __name__ == "__main__":
    main()
