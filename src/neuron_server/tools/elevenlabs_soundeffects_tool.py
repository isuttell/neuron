import asyncio
import os

from elevenlabs import AsyncElevenLabs
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.slug import safe_filename

tool_promp_types = """
Prompt Tips:
* Short prompts (e.g., "footsteps on gravel") yield single sounds.
* Descriptors like "high-quality, Foley" improve detail.
* Use terms like Foley (realistic effects), Whoosh (movement sounds), Impact (collisions), Drone (atmosphere), and onomatopoeias (e.g., "meow").
""".strip()


class ElevenLabsSoundEffectsToolArgs(BaseModel):
    name: str = Field(
        description="A unique display name for the audio file to be generated. Must be less than 256 characters",
    )
    prompt: str = Field(
        description="The prompt used to generate the sound effect.\n\n{tool_promp_types}"
    )
    duration_seconds: float | None = Field(
        description="The duration of the sound which will be generated in seconds. Must be at least 0.5 and at most 22.",
        default=None,
    )
    prompt_influence: float | None = Field(
        description="The influence of the prompt on the sound effect. Must be between 0 and 1. Defaults to 0.3",
        default=0.3,
    )


class ElevenLabsSoundEffectsTool(BaseTool):
    name: str = "elevenlabs_sound_effects"
    description: str = (
        """
This tool generates sound effects using the Eleven Labs sound effect API from text prompts. Provide a prompt, and the tool returns a sound file with an <audio> tag for playback. Complex sequences (e.g., "a man walks through a hallway, then falls") must be created with individual effects and later combined using ffmpeg for optimal quality.
""".strip()
    )
    args_schema: type[ElevenLabsSoundEffectsToolArgs] = ElevenLabsSoundEffectsToolArgs

    def _run(self, prompt: str, duration_seconds: float | None = None) -> str:
        return asyncio.run(self._arun(prompt, duration_seconds))

    async def _arun(
        self,
        prompt: str,
        name: str,
        config: RunnableConfig,
        duration_seconds: float | None = None,
        prompt_influence: float | None = None,
    ) -> str:
        try:
            logger.debug(
                f"Generating sound effect for prompt {prompt} with duration {duration_seconds}"
            )
            client = AsyncElevenLabs(api_key=neuron_config.elevenlabs_api_key)
            response = client.text_to_sound_effects.convert(
                text=prompt,
                prompt_influence=prompt_influence,
                duration_seconds=duration_seconds,
            )
            filename = safe_filename("elevenlabs_soundeffect", name, "mp3")
            audio_file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )
            with open(audio_file_path, "wb") as file:
                async for chunk in response:
                    file.write(chunk)
            url = neuron_config.static_content_url + "/" + filename
            logger.debug(f"Saved generated audio to {audio_file_path} <{url}>")
            create_params = MediaItemModel.CreateParams(
                url=url,
                media_type="audio",
                name=name,
                description=prompt,
                thread_id=config["configurable"].get("thread_id"),
                user_id=config["configurable"].get("user_id"),
            )
            await MediaItemModel.create(params=create_params)
            return f'<audio src="{url}"></audio>'
        except Exception as e:
            logger.error(e, exc_info=True)
            raise


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
