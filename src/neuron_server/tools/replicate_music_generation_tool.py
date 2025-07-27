import asyncio
import logging
import os
from typing import Any, Literal
from uuid import uuid4

import aiofiles
import aiohttp
import replicate
import replicate.helpers
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.util.slug import safe_filename

logger = logging.getLogger(__name__)


class ReplicateMusicGenerationToolArgs(BaseModel):
    name: str = Field(
        description=(
            "A unique display name for the audio generation less than 256 characters"
        )
    )
    prompt: str = Field(description="A description of the music you want to generate.")
    input_audio: str | None = Field(
        description="""
            An audio file url that will influence the generated music. If
            continuation is True, the generated music will be a continuation of
            the audio file. Otherwise, the generated music will mimic the audio
            file's melody. The input audio duration must be shorter than to
            requested duration. Use the ffmpeg tool to trim the input audio file
            to the desired length of approximately 10 seconds for a 60 second clip.
            """,
        default=None,
    )
    duration: int | None = Field(
        description="Duration of the generated audio in seconds.", default=6
    )
    continuation: bool | None = Field(
        description=(
            "If True, generated music will continue from input_audio. Otherwise, "
            "generated music will mimic input_audio's melody."
        ),
        default=False,
    )
    continuation_start: int | None = Field(
        description="Start time of the audio file to use for continuation.", default=0
    )
    continuation_end: int | None = Field(
        description=(
            "End time of the audio file to use for continuation. If -1, will default "
            "to end of clip."
        ),
        default=-1,
    )
    normalization_strategy: Literal["loudness", "peak", "clip", "rms"] | None = Field(
        description="Strategy for normalizing audio.", default="loudness"
    )
    top_k: int | None = Field(
        description="Reduces sampling to the k most likely tokens.", default=250
    )
    top_p: float | None = Field(
        description=(
            "Reduces sampling to tokens with cumulative probability of p. When 0, "
            "top_k sampling is used."
        ),
        default=0,
    )
    temperature: float | None = Field(
        description=(
            "Controls the 'conservativeness' of the sampling process. Higher "
            "temperature means more diversity."
        ),
        default=1.0,
    )
    classifier_free_guidance: int | None = Field(
        description=(
            "Increases influence of inputs on output. Higher values produce "
            "lower-variance outputs that adhere more closely to inputs."
        ),
        default=3,
    )
    seed: int | None = Field(
        description=(
            "Seed for random number generator. If None or -1 a random seed will be used"
        ),
        default=-1,
    )


class ReplicateMusicGenerationTool(BaseTool):
    name: str = "replicate_music_generation"
    description: str = """Use this tool to generate music using the MusicGen model
        stereo-melody-large version. It creates original music from text
        descriptions, continues existing audio, or creates variations based on
        input audio. The model supports various styles and can generate
        high-quality stereo audio output.

        If you get a 'Prompt is longer than audio to generate' error then the
        input audio is too long and you need to trim it with ffmpeg."""

    args_schema: type[ReplicateMusicGenerationToolArgs] = (
        ReplicateMusicGenerationToolArgs
    )
    response_format: str = "content_and_artifact"

    ref: str = (
        "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb"
    )

    def _run(self, **kwargs: Any) -> str:
        return asyncio.run(self._arun(**kwargs))

    async def _arun(
        self,
        prompt: str,
        name: str,
        config: RunnableConfig,
        input_audio: str | None = None,
        **kwargs: Any,
    ) -> tuple[str, dict]:
        logger.debug(f"Generating music with prompt: {prompt}")

        input_args = {
            "prompt": prompt,
            "model_version": "stereo-melody-large",
            "output_format": "mp3",
            **kwargs,
        }
        extension = kwargs.get("output_format", "mp3")

        # Handle input audio if provided
        tmp_audio_file = None
        if input_audio:
            tmp_audio_file = os.path.join(
                neuron_config.temp_folder, f"{uuid4().hex}.{extension}"
            )
            try:
                async with (
                    aiohttp.ClientSession() as session,
                    session.get(input_audio) as response,
                    aiofiles.open(tmp_audio_file, "wb") as f,
                ):
                    response.raise_for_status()
                    await f.write(await response.content.read())
                input_args["input_audio"] = open(tmp_audio_file, "rb")  # noqa: SIM115
            except Exception as e:
                logger.error(f"Failed to download input audio: {str(e)}")
                if tmp_audio_file and os.path.exists(tmp_audio_file):
                    os.remove(tmp_audio_file)
                raise
        try:
            for key, value in input_args.items():
                is_audio = key == "input_audio" and value
                logger.debug(f"{key}={True if is_audio else value}")
        except Exception as e:
            logger.warning(e, exc_info=True)

        try:
            output: replicate.helpers.FileOutput = await replicate.async_run(
                self.ref, input=input_args
            )

            # Clean slug and prepare filename
            filename = safe_filename(self.ref.replace("/", "_"), name, extension)
            file_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )

            # Save the generated audio
            async with aiofiles.open(file_path, "wb") as file:
                async for chunk in output:
                    await file.write(chunk)

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

            metadata = ToolArtifactMetadata(
                model=self.ref,
                prompt=prompt,
                duration=float(kwargs.get("duration", 6)),
                output_format=kwargs.get("output_format", "mp3"),
                temperature=kwargs.get("temperature"),
                cfg_strength=kwargs.get("classifier_free_guidance"),
            )

            artifact_item = ToolMediaItem(
                id=media_id,
                url=url,
                caption=name,
                description=prompt,
                metadata=metadata,
            )

            artifact = ToolMediaArtifact(media_type="audio", items=[artifact_item])

            return artifact.to_xml(), [artifact.model_dump()]

        except Exception as e:
            logger.error(e, exc_info=True)
            raise
        finally:
            if tmp_audio_file and os.path.exists(tmp_audio_file):
                os.remove(tmp_audio_file)


async def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate music using Meta's MusicGen model"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Description of the music to generate",
        default="An upbeat electronic dance track with a strong beat",
    )
    parser.add_argument(
        "--input_audio",
        type=str,
        help="Optional input audio URL to influence generation",
        default=None,
    )
    args = parser.parse_args()

    tool = ReplicateMusicGenerationTool()
    result = await tool._arun(
        prompt=args.prompt, input_audio=args.input_audio, slug="test-generation"
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
