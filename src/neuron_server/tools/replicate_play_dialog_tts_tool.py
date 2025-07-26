import asyncio
import logging
import os
import random
from typing import Any, Literal
from uuid import uuid4

import aiofiles
import aiohttp
import replicate
import replicate.helpers
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, ConfigDict, Field

from neuron_server.config import config as neuron_config
from neuron_server.util.slug import safe_filename

logger = logging.getLogger(__name__)


VOICE_OPTIONS = Literal[
    "Angelo (Young male US conversational voice)",
    "Arsenio (Middle-aged male US African American conversational voice)",
    "Cillian (Middle-aged male Irish conversational voice)",
    "Timo (Middle-aged male US conversational voice)",
    "Dexter (Middle-aged male US conversational voice)",
    "Miles (Young male US African American conversational voice)",
    "Briggs (Elderly male US Southern (Oklahoma) conversational voice)",
    "Deedee (Middle-aged female US African American conversational voice)",
    "Nia (Young female US conversational voice)",
    "Inara (Middle-aged female US African American conversational voice)",
    "Constanza (Young female US Latin American conversational voice)",
    "Gideon (Elderly male British narrative voice)",
    "Casper (Middle-aged male US narrative voice)",
    "Mitch (Middle-aged male Australian narrative voice)",
    "Ava (Middle-aged female Australian narrative voice)",
    "Carmen (Middle-aged female Spanish conversational voice, calm and warm)",
    "Andrei (Middle-aged male Russian conversational voice, calm and warm)",
    "Ilias (Middle-aged male German narrative voice, deep and calm)",
    "Gaelle (Middle-aged female French conversational voice, professional)",
    "Alessandro (Older male Italian conversational voice, warm and gravelly)",
    "Yumiko (Young female Japanese narrative voice, warm and light)",
]


class ReplicatePlayDialogToolArgs(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(description="Display title for the generated audio")
    text: str = Field(
        description="""Text for speech generation. When using two voices,
        use the turn prefixes 'Voice 1: ' and 'Voice 2: ' respectively.
        """.strip(),
    )
    voice: VOICE_OPTIONS = Field(
        description="Voice to use for generation",
    )
    voice_2: VOICE_OPTIONS | None = Field(
        description="Optional second voice to use for generation",
        default="None",
    )
    language: str = Field(
        description="The language of the text to be spoken.",
        default="english",
        enum=[
            "afrikaans",
            "albanian",
            "amharic",
            "arabic",
            "bengali",
            "bulgarian",
            "catalan",
            "croatian",
            "czech",
            "danish",
            "dutch",
            "english",
            "french",
            "galician",
            "german",
            "greek",
            "hebrew",
            "hindi",
            "hungarian",
            "indonesian",
            "italian",
            "japanese",
            "korean",
            "malay",
            "mandarin",
            "polish",
            "portuguese",
            "russian",
            "serbian",
            "spanish",
            "swedish",
            "tagalog",
            "thai",
            "turkish",
            "ukrainian",
            "urdu",
            "xhosa",
        ],
    )
    temperature: float = Field(
        description=(
            "The temperature parameter controls variance. Lower temperatures result in "
            "more predictable results, higher temperatures allow each run to vary "
            "more, so the voice may sound less like the baseline voice. Between "
            "1.02 and 1.05 give good results."
        ),
        default=1.02,
        ge=0.1,
        le=1.5,
    )
    seed: int | None = Field(
        description=(
            "Random seed. Set when trying to exactly reproduce a generation. "
            "Set to -1 to use a random seed."
        ),
        default=-1,
    )
    prompt: str | None = Field(
        description="A prompt to guide the style of the first voice.",
        default="",
    )
    prompt2: str | None = Field(
        description="A prompt to guide the style of the second voice.",
        default="",
    )


class ReplicatePlayDialogTool(BaseTool):
    name: str = "replicate_play_dialog_tts"
    description: str = """Use this tool to generate speech from text using the PlayHT
        Dialog model. It supports multiple voices and languages, and can generate
        dialog between two voices."""

    args_schema: type[ReplicatePlayDialogToolArgs] = ReplicatePlayDialogToolArgs
    response_format: str = "content_and_artifact"

    ref: str = "playht/play-dialog"

    def _run(self, **kwargs: Any) -> str:
        return asyncio.run(self._arun(**kwargs))

    async def _arun(
        self,
        text: str,
        name: str,
        config: RunnableConfig,
        **kwargs: Any,
    ) -> tuple[str, dict]:
        logger.debug(f"Generating speech with text: {text}")

        input_args = {
            "text": text,
            **kwargs,
        }

        # Ensure a seed is set for reproducible results at a later date
        input_args["seed"] = (
            kwargs.get("seed")
            if kwargs.get("seed") is not None and kwargs.get("seed") != -1
            else random.randint(1_000_000_000, 2_147_483_647)
        )

        try:
            output = await replicate.async_run(self.ref, input=input_args)

            # Clean slug and prepare filename
            filename = safe_filename(self.ref.replace("/", "_"), name, "mp3")
            file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )

            # Handle different output types from Replicate
            if hasattr(output, "read"):
                # If output is a file-like object, read its content
                content = output.read()
                if asyncio.iscoroutine(content):
                    content = await content
                async with aiofiles.open(file_path, "wb") as file:
                    await file.write(content)
            elif isinstance(output, str) and output.startswith(("http://", "https://")):
                # If output is a URL, download it
                async with aiohttp.ClientSession() as session:  # noqa: SIM117
                    async with session.get(output) as response:
                        content = await response.read()
                        async with aiofiles.open(file_path, "wb") as file:
                            await file.write(content)
            elif isinstance(output, bytes):
                # If output is already bytes, write directly
                async with aiofiles.open(file_path, "wb") as file:
                    await file.write(output)
            else:
                raise ValueError(
                    f"Unexpected output type from Replicate: {type(output)}"
                )

            url = f"{neuron_config.static_content_url}/{filename}"

            # Generate a real UUID for consistent ID between artifact and media_item
            media_id = uuid4()

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
                output_format="mp3",
                seed=kwargs.get("seed") if kwargs.get("seed", -1) != -1 else None,
            )

            artifact_item = ToolMediaItem(
                id=media_id,
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
        description="Generate speech using PlayHT Dialog model"
    )
    parser.add_argument(
        "--text",
        type=str,
        help="Text to convert to speech",
        default="Hello, this is a test of the text to speech system.",
    )
    parser.add_argument(
        "--voice",
        type=str,
        help="Voice to use",
        default="Angelo (Young male US conversational voice)",
    )
    args = parser.parse_args()

    tool = ReplicatePlayDialogTool()
    result = await tool._arun(text=args.text, voice=args.voice)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
