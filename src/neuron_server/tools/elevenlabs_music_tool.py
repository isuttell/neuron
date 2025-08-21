import asyncio
import os
from typing import Any
from uuid import uuid4

from elevenlabs import AsyncElevenLabs
from elevenlabs.types import MusicPrompt, SongSection
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
from neuron_server.tools.artifact_types import (
    ToolArtifactMetadata,
    ToolMediaArtifact,
    ToolMediaItem,
)
from neuron_server.util.media_utilities import get_media_duration
from neuron_server.util.slug import safe_filename


class SongSectionArgs(BaseModel):
    section_name: str = Field(
        description=(
            "Name of the section (e.g., 'intro', 'verse', 'chorus', 'bridge', "
            "'outro'). Must be between 1 and 100 characters."
        )
    )

    positive_local_styles: list[str] = Field(
        description=(
            "List of musical styles that should be present in this specific section "
            "(e.g., ['edm', 'swing dance', 'upbeat'])"
        )
    )

    negative_local_styles: list[str] = Field(
        description=(
            "List of musical styles that should NOT be present in this specific "
            "section (e.g., ['pop', 'jazz'])"
        ),
        default=[],
    )

    duration_ms: int = Field(
        description=(
            "Duration of this section in milliseconds. Must be between 3000ms "
            "(3 seconds) and 120000ms (2 minutes)."
        ),
        ge=3000,
        le=120000,
    )

    lines: list[str] = Field(
        description=(
            "Lyrics or thematic descriptions for this section. Each string "
            "represents a line of content."
        ),
        default=[],
    )


class ElevenLabsMusicToolArgs(BaseModel):
    title: str = Field(
        description=(
            "Title/name for the music composition. "
            "This will be used as the display name for the generated music file."
        )
    )

    positive_global_styles: list[str] = Field(
        description=(
            "List of musical styles that should be present throughout the entire song "
            "(e.g., ['electronic', 'ambient', 'uplifting', 'medium tempo'])"
        )
    )

    negative_global_styles: list[str] = Field(
        description=(
            "List of musical styles that should NOT be present anywhere in the song "
            "(e.g., ['heavy metal', 'sad', 'aggressive', 'dissonant'])"
        ),
        default=[],
    )

    sections: list[SongSectionArgs] = Field(
        description=(
            "List of song sections that define the structure of the composition. "
            "Each section specifies its own styles, duration, and content. "
            "Typical structure might include intro, verse, chorus, bridge, outro."
        ),
        min_length=1,
    )


class ElevenLabsMusicTool(BaseTool):
    name: str = "elevenlabs_music"
    description: str = """
This tool generates structured music compositions using ElevenLabs' advanced music
generation API. Create complete songs with multiple sections (intro, verse, chorus,
bridge, outro) and precise control over musical styles. Specify global styles for
the entire composition and section-specific styles for each part. Perfect for
creating professional-quality instrumental or vocal music with detailed structure.
""".strip()
    args_schema: type[ElevenLabsMusicToolArgs] = ElevenLabsMusicToolArgs
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> tuple[str, dict]:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        title: str,
        positive_global_styles: list[str],
        negative_global_styles: list[str],
        sections: list[SongSectionArgs],
        config: RunnableConfig,
    ) -> tuple[str, dict]:
        try:
            logger.debug(f"Generating ElevenLabs music composition: {title}")

            client = AsyncElevenLabs(api_key=neuron_config.elevenlabs_api_key)

            # Convert SongSectionArgs to SongSection objects
            song_sections = []
            for section_args in sections:
                song_section = SongSection(
                    section_name=section_args.section_name,
                    positive_local_styles=section_args.positive_local_styles,
                    negative_local_styles=section_args.negative_local_styles,
                    duration_ms=section_args.duration_ms,
                    lines=section_args.lines,
                )
                song_sections.append(song_section)

            # Create the MusicPrompt composition plan
            composition_plan = MusicPrompt(
                positive_global_styles=positive_global_styles,
                negative_global_styles=negative_global_styles,
                sections=song_sections,
            )

            # Generate filename and save path
            filename = safe_filename("elevenlabs_music", title, "mp3")
            output_path = os.path.abspath(
                os.path.join(neuron_config.static_folder, filename)
            )

            # Generate music using the composition plan
            with open(output_path, "wb") as f:
                async for chunk in client.music.compose(
                    composition_plan=composition_plan
                ):
                    f.write(chunk)

            url = neuron_config.static_content_url + "/" + filename
            logger.info(f"Generated music file saved to {output_path} <{url}>")

            # Generate a real UUID for consistent ID between artifact and media_item
            media_id = uuid4()

            # Prepare artifact for UI using typed models

            # Get actual duration from the generated file
            actual_duration = await get_media_duration(output_path)

            # Calculate total planned duration
            total_planned_duration = (
                sum(section.duration_ms for section in sections) / 1000.0
            )

            # Create comprehensive description with all song details
            description_parts = [
                f'Title: "{title}"',
                f"Global Styles: {', '.join(positive_global_styles)}",
            ]

            if negative_global_styles:
                description_parts.append(
                    f"Avoiding: {', '.join(negative_global_styles)}"
                )

            description_parts.append("")  # Empty line before sections

            # Add detailed section information
            for i, section in enumerate(sections, 1):
                section_duration = section.duration_ms / 1000.0
                section_info = (
                    f"Section {i}: {section.section_name} ({section_duration:.1f}s)"
                )
                description_parts.append(section_info)

                if section.positive_local_styles:
                    description_parts.append(
                        f"- Styles: {', '.join(section.positive_local_styles)}"
                    )

                if section.negative_local_styles:
                    description_parts.append(
                        f"- Avoiding: {', '.join(section.negative_local_styles)}"
                    )

                if section.lines:
                    for line in section.lines:
                        description_parts.append(f'- "{line}"')

                description_parts.append("")  # Empty line after each section

            # Add summary
            summary = (
                f"Total: {len(sections)} sections, "
                f"{total_planned_duration:.1f}s planned"
            )
            description_parts.append(summary)

            comprehensive_description = "\n".join(description_parts)

            # Create simple composition summary for backward compatibility
            sections_desc = ", ".join([section.section_name for section in sections])
            composition_summary = (
                f"Composition: {title} | Sections: {sections_desc} | "
                f"Styles: {', '.join(positive_global_styles)}"
            )

            metadata = ToolArtifactMetadata(
                model="elevenlabs/eleven_music",
                prompt=composition_summary,  # Keep simple summary for compatibility
                duration=actual_duration,
                output_format="mp3",
                # Music-specific metadata fields
                title=title,
                positive_global_styles=positive_global_styles,
                negative_global_styles=negative_global_styles,
                sections_count=len(sections),
                total_planned_duration=total_planned_duration,
            )

            artifact_item = ToolMediaItem(
                id=media_id,
                url=url,
                name=title,
                description=comprehensive_description,
                metadata=metadata,
            )

            artifact = ToolMediaArtifact(media_type="audio", items=[artifact_item])

            return artifact.to_xml(), [artifact.model_dump()]
        except Exception as e:
            logger.error(e, exc_info=True)
            raise


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate music from text prompt.")
    parser.add_argument(
        "prompt",
        type=str,
        help="The text prompt describing the music to generate.",
    )
    parser.add_argument(
        "--name",
        type=str,
        default="Generated Music",
        help="Display name for the generated music.",
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Duration in seconds (10-300).",
    )
    args = parser.parse_args()

    # Call the tool to generate the music
    tool = ElevenLabsMusicTool()
    results = tool._run(
        prompt=args.prompt,
        name=args.name,
        duration=args.duration,
        config={},
    )
    # Print the response
    print(results)


if __name__ == "__main__":
    main()
