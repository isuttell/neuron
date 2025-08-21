from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest
from pydantic import ValidationError

from neuron_server.tools.elevenlabs_music_tool import (
    ElevenLabsMusicTool,
    ElevenLabsMusicToolArgs,
    SongSectionArgs,
)

# Module path constant to reduce line length
MUSIC_MODULE = "neuron_server.tools.elevenlabs_music_tool"


class TestSongSectionArgs:
    def test_valid_section(self):
        section = SongSectionArgs(
            section_name="verse",
            positive_local_styles=["jazz", "piano"],
            negative_local_styles=["heavy"],
            duration_ms=30000,
            lines=["Verse line one", "Verse line two"],
        )
        assert section.section_name == "verse"
        assert section.positive_local_styles == ["jazz", "piano"]
        assert section.negative_local_styles == ["heavy"]
        assert section.duration_ms == 30000
        assert section.lines == ["Verse line one", "Verse line two"]

    def test_duration_validation(self):
        # Valid duration
        section = SongSectionArgs(
            section_name="intro", positive_local_styles=["ambient"], duration_ms=5000
        )
        assert section.duration_ms == 5000

        # Duration too short
        with pytest.raises(ValidationError):
            SongSectionArgs(
                section_name="intro",
                positive_local_styles=["ambient"],
                duration_ms=2000,
            )

        # Duration too long
        with pytest.raises(ValidationError):
            SongSectionArgs(
                section_name="intro",
                positive_local_styles=["ambient"],
                duration_ms=130000,
            )

    def test_optional_fields(self):
        section = SongSectionArgs(
            section_name="chorus", positive_local_styles=["pop"], duration_ms=20000
        )
        assert section.negative_local_styles == []
        assert section.lines == []


class TestElevenLabsMusicToolArgs:
    def test_valid_args(self):
        sections = [
            SongSectionArgs(
                section_name="intro",
                positive_local_styles=["ambient"],
                duration_ms=10000,
            ),
            SongSectionArgs(
                section_name="verse",
                positive_local_styles=["jazz", "piano"],
                duration_ms=30000,
            ),
        ]
        args = ElevenLabsMusicToolArgs(
            title="Jazz Piano Test",
            positive_global_styles=["jazz", "medium tempo"],
            negative_global_styles=["heavy metal"],
            sections=sections,
        )
        assert args.title == "Jazz Piano Test"
        assert args.positive_global_styles == ["jazz", "medium tempo"]
        assert args.negative_global_styles == ["heavy metal"]
        assert len(args.sections) == 2

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            ElevenLabsMusicToolArgs()

    def test_sections_validation(self):
        # Empty sections should fail
        with pytest.raises(ValidationError):
            ElevenLabsMusicToolArgs(
                title="Test", positive_global_styles=["pop"], sections=[]
            )

        # Valid with one section
        sections = [
            SongSectionArgs(
                section_name="full_song",
                positive_local_styles=["electronic"],
                duration_ms=60000,
            )
        ]
        args = ElevenLabsMusicToolArgs(
            title="Electronic Test",
            positive_global_styles=["electronic"],
            sections=sections,
        )
        assert len(args.sections) == 1

    def test_optional_negative_styles(self):
        sections = [
            SongSectionArgs(
                section_name="test",
                positive_local_styles=["ambient"],
                duration_ms=15000,
            )
        ]
        args = ElevenLabsMusicToolArgs(
            title="Ambient Test", positive_global_styles=["ambient"], sections=sections
        )
        assert args.negative_global_styles == []


class TestElevenLabsMusicTool:
    @pytest.fixture
    def tool(self):
        return ElevenLabsMusicTool()

    @pytest.fixture
    def mock_config(self):
        with patch("neuron_server.tools.elevenlabs_music_tool.neuron_config") as mock:
            mock.elevenlabs_api_key = "test_api_key"
            mock.static_folder = "/tmp/static"
            mock.static_content_url = "http://localhost:8000/static"
            yield mock

    @pytest.fixture
    def mock_media_duration(self):
        async def mock_duration(*args, **kwargs):
            return 45.0

        with patch(
            "neuron_server.util.media_utilities.get_media_duration",
            side_effect=mock_duration,
        ) as mock:
            yield mock

    @pytest.fixture
    def sample_sections(self):
        return [
            SongSectionArgs(
                section_name="intro",
                positive_local_styles=["ambient"],
                duration_ms=10000,
            ),
            SongSectionArgs(
                section_name="main",
                positive_local_styles=["jazz", "piano"],
                negative_local_styles=["electronic"],
                duration_ms=35000,
                lines=["Melodic jazz piano", "Walking bass line"],
            ),
        ]

    async def test_successful_music_generation(
        self, tool, mock_config, mock_media_duration, sample_sections
    ):
        mock_client = AsyncMock()

        # Mock async generator for stream response
        class MockAsyncGenerator:
            def __init__(self, chunks) -> None:
                self.chunks = chunks
                self.index = 0

            def __aiter__(self) -> "MockAsyncGenerator":
                return self

            async def __anext__(self) -> bytes:
                if self.index >= len(self.chunks):
                    raise StopAsyncIteration
                chunk = self.chunks[self.index]
                self.index += 1
                return chunk

        mock_compose = MagicMock(
            return_value=MockAsyncGenerator([b"chunk1", b"chunk2"])
        )
        mock_client.music.compose = mock_compose

        with (
            patch(f"{MUSIC_MODULE}.AsyncElevenLabs") as mock_el,
            patch(f"{MUSIC_MODULE}.safe_filename") as mock_fn,
            patch(f"{MUSIC_MODULE}.open", mock_open()) as mock_file,
            patch("os.path.abspath") as mock_abspath,
        ):
            mock_elevenlabs = mock_el
            mock_filename = mock_fn
            mock_elevenlabs.return_value = mock_client
            mock_filename.return_value = "test_music.mp3"
            mock_abspath.return_value = "/tmp/static/test_music.mp3"

            result = await tool._arun(
                title="Jazz Piano Composition",
                positive_global_styles=["jazz", "medium tempo"],
                negative_global_styles=["heavy metal"],
                sections=sample_sections,
                config={},
            )

        # Verify the client was called with composition_plan
        mock_client.music.compose.assert_called_once()
        call_args = mock_client.music.compose.call_args
        assert "composition_plan" in call_args.kwargs

        # Verify file was written
        mock_file.assert_called_once_with("/tmp/static/test_music.mp3", "wb")
        write_calls = mock_file().write.call_args_list
        assert len(write_calls) == 2
        assert write_calls[0][0][0] == b"chunk1"
        assert write_calls[1][0][0] == b"chunk2"

        # Verify return format
        assert len(result) == 2
        xml_output, artifacts = result
        assert isinstance(xml_output, str)
        assert isinstance(artifacts, list)
        assert len(artifacts) == 1

        # Verify artifact structure
        artifact = artifacts[0]
        assert artifact["media_type"] == "audio"
        assert len(artifact["items"]) == 1

        item = artifact["items"][0]
        assert item["name"] == "Jazz Piano Composition"
        assert item["url"] == "http://localhost:8000/static/test_music.mp3"

        # Verify comprehensive description contains all details
        description = item["description"]
        assert 'Title: "Jazz Piano Composition"' in description
        assert "Global Styles: jazz, medium tempo" in description
        assert "Avoiding: heavy metal" in description
        assert "Section 1: intro (10.0s)" in description
        assert "Section 2: main (35.0s)" in description
        assert "Styles: ambient" in description
        assert "Styles: jazz, piano" in description
        assert "Avoiding: electronic" in description
        assert '"Melodic jazz piano"' in description
        assert '"Walking bass line"' in description
        assert "Total: 2 sections, 45.0s planned" in description

        assert item["id"] is not None  # UUID should not be None

        # Verify enhanced metadata
        metadata = item["metadata"]
        assert metadata["title"] == "Jazz Piano Composition"
        assert metadata["positive_global_styles"] == ["jazz", "medium tempo"]
        assert metadata["negative_global_styles"] == ["heavy metal"]
        assert metadata["sections_count"] == 2
        assert metadata["total_planned_duration"] == 45.0

    async def test_music_composition_plan_structure(
        self, tool, mock_config, mock_media_duration, sample_sections
    ):
        mock_client = AsyncMock()

        # Mock async generator for stream response
        class MockAsyncGenerator:
            def __init__(self, chunks) -> None:
                self.chunks = chunks
                self.index = 0

            def __aiter__(self) -> "MockAsyncGenerator":
                return self

            async def __anext__(self) -> bytes:
                if self.index >= len(self.chunks):
                    raise StopAsyncIteration
                chunk = self.chunks[self.index]
                self.index += 1
                return chunk

        mock_compose = MagicMock(return_value=MockAsyncGenerator([b"audio_data"]))
        mock_client.music.compose = mock_compose

        with (
            patch(f"{MUSIC_MODULE}.AsyncElevenLabs") as mock_el,
            patch(f"{MUSIC_MODULE}.safe_filename") as mock_fn,
            patch(f"{MUSIC_MODULE}.open", mock_open()),
            patch("os.path.abspath"),
        ):
            mock_elevenlabs = mock_el
            mock_elevenlabs.return_value = mock_client
            mock_fn.return_value = "test.mp3"

            await tool._arun(
                title="Test Composition",
                positive_global_styles=["ambient", "electronic"],
                negative_global_styles=["rock", "metal"],
                sections=sample_sections,
                config={},
            )

        # Verify composition plan was passed
        call_args = mock_client.music.compose.call_args
        composition_plan = call_args.kwargs["composition_plan"]

        assert composition_plan.positive_global_styles == ["ambient", "electronic"]
        assert composition_plan.negative_global_styles == ["rock", "metal"]
        assert len(composition_plan.sections) == 2

        # Verify sections were converted properly
        section1 = composition_plan.sections[0]
        assert section1.section_name == "intro"
        assert section1.positive_local_styles == ["ambient"]
        assert section1.duration_ms == 10000

        section2 = composition_plan.sections[1]
        assert section2.section_name == "main"
        assert section2.positive_local_styles == ["jazz", "piano"]
        assert section2.negative_local_styles == ["electronic"]
        assert section2.duration_ms == 35000
        assert section2.lines == ["Melodic jazz piano", "Walking bass line"]

    async def test_api_error_handling(self, tool, mock_config, sample_sections):
        mock_client = AsyncMock()

        # Set side_effect directly on the mock function
        mock_compose = MagicMock(side_effect=Exception("API Error"))
        mock_client.music.compose = mock_compose

        with (
            patch(f"{MUSIC_MODULE}.AsyncElevenLabs") as mock_elevenlabs,
            patch(f"{MUSIC_MODULE}.safe_filename") as mock_fn,
            patch(f"{MUSIC_MODULE}.open", mock_open()),
            patch("os.path.abspath"),
        ):
            mock_elevenlabs.return_value = mock_client
            mock_fn.return_value = "error_test.mp3"

            with pytest.raises(Exception, match="API Error"):
                await tool._arun(
                    title="Error Test",
                    positive_global_styles=["test"],
                    negative_global_styles=[],
                    sections=sample_sections,
                    config={},
                )

    def test_sync_run_method(self, tool):
        with patch.object(tool, "_arun") as mock_arun:
            mock_arun.return_value = ("xml", [{}])

            with patch("asyncio.run") as mock_asyncio_run:
                mock_asyncio_run.return_value = ("xml", [{}])

                result = tool._run(
                    title="Test",
                    positive_global_styles=["test"],
                    negative_global_styles=[],
                    sections=[],
                    config={},
                )

                assert result == ("xml", [{}])
                mock_asyncio_run.assert_called_once()

    def test_tool_properties(self, tool):
        assert tool.name == "elevenlabs_music"
        assert "structured music compositions" in tool.description
        assert tool.args_schema == ElevenLabsMusicToolArgs
        assert tool.response_format == "content_and_artifact"
