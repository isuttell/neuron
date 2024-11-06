from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
from uuid import uuid4
import os
from elevenlabs import ElevenLabs
from neuron_server.logger import logger
from typing import Optional


class ElevenLabsSoundEffectsTool(BaseTool):
    name: str = "elevenlabs_soundeffects"
    description: str = (
        """
This tool generates sound effects using the Eleven Labs sound effect API. Users provide a simple text prompt, and the tool produces a corresponding sound effect, returning a filename for each sound file. These filenames can then be combined with other audio or video elements using ffmpeg, enabling seamless integration with your media projects. Simple prompts, like 'footsteps on gravel,' generate single, distinct effects, while more descriptive prompts enhance audio detail and quality. Do not show the output filename to the user as they can't directly access it. If you want to show the user make sure to use an <audio> tag and the src attribute to point to the URL.

Args:
Text: The text prompt to generate sound effects from
duration_seconds: The duration of the sound which will be generated in seconds. Must be at least 0.5 and at most 22. If set to None we will guess the optimal duration using the prompt. Defaults to None.
""".strip()
    )

    def _run(self, text: str, duration_seconds: Optional[float] = None) -> str:
        try:
            client = ElevenLabs(api_key=config.elevenlabs_api_key)
            id = str(uuid4())
            response = client.text_to_sound_effects.convert(
                text=text,
                prompt_influence=0.3,
                duration_seconds=duration_seconds,
            )
            output_dir = config.static_folder + "/soundeffects"
            os.makedirs(output_dir, exist_ok=True)
            audio_file_path = os.path.abspath(output_dir + "/" + f"{id}.mp3")
            with open(audio_file_path, "wb") as file:
                for chunk in response:
                    file.write(chunk)
            url = config.static_content_url + "/soundeffects/" + f"{id}.mp3"
            logger.debug(f"Saved generated audio to {audio_file_path} <{url}>")

            return f"""
Filename: {audio_file_path}
URL: <{url}>
""".strip()
        except Exception as e:
            logger.exception(e)
            return f"Error generating audio: {str(e)}"


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate sound effects from a text prompt."
    )
    parser.add_argument(
        "prompt", type=str, help="The text prompt to generate sound effects from."
    )
    args = parser.parse_args()

    # Call the tool to generate the audio
    tool = ElevenLabsSoundEffectsTool()
    results = tool._run(args.prompt)
    # Print the response
    print(results)


if __name__ == "__main__":
    main()
