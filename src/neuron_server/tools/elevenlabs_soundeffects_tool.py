from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
from uuid import uuid4
import os
from elevenlabs import ElevenLabs
from neuron_server.logger import logger
from typing import Optional, Type
from pydantic import Field, BaseModel

tool_promp_types = """
Prompt Tips:

Simple: Short prompts (e.g., "footsteps on gravel") yield single sounds. Descriptors like "high-quality, Foley" improve detail.
Audio Terms: Use terms like Foley (realistic effects), Whoosh (movement sounds), Impact (collisions), Drone (atmosphere), and onomatopoeias (e.g., "meow").
""".strip()


class ElevenLabsSoundEffectsToolArgs(BaseModel):
    text: str = Field(
        description="The text used to generate the sound effect.\n\n{tool_promp_types}"
    )
    duration_seconds: Optional[float] = Field(
        description="The duration of the sound which will be generated in seconds. Must be at least 0.5 and at most 22. If set to None we will guess the optimal duration using the prompt.",
        default=None,
    )


class ElevenLabsSoundEffectsTool(BaseTool):
    name: str = "elevenlabs_soundeffects"
    description: str = (
        """
This tool generates sound effects using the Eleven Labs sound effect API from text prompts. Users provide a prompt, and the tool returns a sound file with an <audio> tag for playback. Complex sequences (e.g., "a man walks through a hallway, then falls") should ideally be created with individual effects and later combined using ffmpeg for optimal quality.
""".strip()
    )
    args_schema: Type[ElevenLabsSoundEffectsToolArgs] = ElevenLabsSoundEffectsToolArgs

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
<audio src="{url}"></audio>
Filename: {audio_file_path}
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
