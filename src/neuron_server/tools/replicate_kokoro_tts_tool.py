import asyncio
import logging
import os
from typing import Any, Literal

import replicate
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ConfigDict, Field

from neuron_server.config import config as neuron_config
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.replicate_helpers import save_replicate_output
from neuron_server.util.slug import safe_filename

logger = logging.getLogger(__name__)

DEFAULT_TEXT_PREVIEW_LENGTH = 100


def create_text_preview(
    text: str, max_length: int = DEFAULT_TEXT_PREVIEW_LENGTH
) -> str:
    """
    Create a truncated preview of text for logging.

    Args:
        text: The text to preview
        max_length: Maximum length before truncation (default: 100)

    Returns:
        Truncated text with ellipsis if needed
    """
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


VOICE_OPTIONS = Literal[
    "af_aoede",  # American English female, C+
    "af_bella",  # American English female, A- (high quality)
    "af_kore",  # American English female, C+
    "af_nicole",  # American English female, B-
    "af_sarah",  # American English female, C+
    "am_fenrir",  # American English male, C+
    "am_michael",  # American English male, C+
    "am_puck",  # American English male, C+
    "bf_emma",  # British English female, B-
]


class ReplicateKokoroTTSToolArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(description="Display title for the generated audio")
    text: str = Field(description="Text input (long text is automatically split)")
    voice: VOICE_OPTIONS = Field(
        description="""Voice to use for synthesis. Prefixes: 'af_' = American Female,
        'am_' = American Male, 'bf_' = British Female. Highest quality voices:
        af_bella (A-), af_nicole (B-), bf_emma (B-) - use these for best results.
        Other C+ voices available: af_aoede, af_kore, af_sarah, am_fenrir,
        am_michael, am_puck.""",
        default="af_bella",
    )
    speed: float = Field(
        description="Speech speed multiplier (0.5 = half speed, 2.0 = double speed)",
        default=1.0,
        ge=0.1,
        le=5.0,
    )


class ReplicateKokoroTTSTool(BaseTool):
    name: str = "replicate_kokoro_tts"
    description: str = """Use this tool to generate speech from text using the Kokoro
        TTS model. It's a lightweight 82M parameter model with high-quality
        English voices (American and British English) rated C+ or better.
        This tool is specifically designed for long-form content like audiobooks
        and automatically handles text batching for extended generations."""

    args_schema: type[ReplicateKokoroTTSToolArgs] = ReplicateKokoroTTSToolArgs
    response_format: str = "content_and_artifact"

    ref: str = (
        "jaaari/kokoro-82m:"
        "f559560eb822dc509045f3921a1921234918b91739db4bf3daab2169b71c7a13"
    )

    def _run(self, **kwargs: Any) -> str:
        return asyncio.run(self._arun(**kwargs))

    async def _arun(
        self,
        text: str,
        name: str,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> tuple[str, dict]:
        logger.debug(f"Generating speech with Kokoro TTS: {create_text_preview(text)}")

        input_args = {
            "text": text,
            "voice": kwargs.get("voice", "af_bella"),
            "speed": kwargs.get("speed", 1.0),
        }

        try:
            output = await replicate.async_run(self.ref, input=input_args)

            # Clean slug and prepare filename
            filename = safe_filename(self.ref.replace("/", "_"), name, "wav")
            file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )

            # Save the replicate output to file
            await save_replicate_output(output, file_path)

            url = f"{neuron_config.static_content_url}/{filename}"
            create_params = MediaItemModel.CreateParams(
                thread_id=config["configurable"].get("thread_id"),
                user_id=config["configurable"].get("user_id"),
                url=url,
                media_type="tts",
                name=name,
                description=text,
            )
            media_item = await MediaItemModel.create(params=create_params)
            logger.debug(f"Saved generated audio to {file_path} <{url}>")

            # Prepare artifact for UI using typed models
            from neuron_server.tools.artifact_types import (
                ToolArtifactMetadata,
                ToolMediaArtifact,
                ToolMediaItem,
            )
            from neuron_server.util.media_utilities import get_media_duration

            # Get actual duration from the generated file
            duration = await get_media_duration(file_path)

            metadata = ToolArtifactMetadata(
                model=self.ref,
                prompt=name,
                duration=duration,
                output_format="wav",
            )

            artifact_item = ToolMediaItem(
                id=str(media_item.id),
                url=url,
                caption=name,
                description=text,
                metadata=metadata,
            )

            artifact = ToolMediaArtifact(media_type="audio", items=[artifact_item])

            return artifact.to_xml(), [artifact.model_dump()]

        except Exception as e:
            logger.error(e, exc_info=True)
            raise


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate speech using Kokoro TTS model"
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Text to convert to speech",
        default="Hello, this is a test of the Kokoro text to speech system.",
    )
    parser.add_argument(
        "--voice",
        type=str,
        help="Voice to use",
        default="af_bella",
    )
    parser.add_argument(
        "--speed",
        type=float,
        help="Speech speed multiplier",
        default=1.0,
    )
    args = parser.parse_args()

    tool = ReplicateKokoroTTSTool()
    result = await tool._arun(
        text=args.text, voice=args.voice, speed=args.speed, name="test"
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
