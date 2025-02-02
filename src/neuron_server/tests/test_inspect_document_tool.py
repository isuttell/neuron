from unittest.mock import patch

import pytest

from neuron_server.tools.document_utils import (
    DocumentLoadError,
    extract_video_id,
    is_youtube_url,
    load_youtube_transcript,
)
from neuron_server.tools.inspect_document_tool import (
    InspectDocumentTool,
)


def test_is_youtube_url() -> None:
    """Test YouTube URL validation."""
    assert is_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert is_youtube_url("https://youtu.be/dQw4w9WgXcQ")
    assert is_youtube_url("http://youtube.com/watch?v=dQw4w9WgXcQ")
    assert not is_youtube_url("https://example.com")
    assert not is_youtube_url("https://youtube.com")


def test_extract_video_id() -> None:
    """Test video ID extraction from URLs."""
    assert (
        extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    )
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    with pytest.raises(ValueError):
        extract_video_id("https://example.com")


@pytest.mark.asyncio
async def test_load_youtube_transcript() -> None:
    """Test loading transcripts with mocked API response."""
    mock_transcript = [
        {"text": "Hello world", "start": 0.0, "duration": 1.5},
        {"text": "This is a test", "start": 1.5, "duration": 2.0},
    ]

    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi.get_transcript"
    ) as mock_get:
        mock_get.return_value = mock_transcript
        doc = await load_youtube_transcript(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )

        assert doc.metadata["video_id"] == "dQw4w9WgXcQ"
        assert "Hello world" in doc.page_content
        assert "This is a test" in doc.page_content


@pytest.mark.asyncio
async def test_load_youtube_transcript_error() -> None:
    """Test error handling for transcript loading."""
    with (
        patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript") as mock_get,
        pytest.raises(DocumentLoadError),
    ):
        mock_get.side_effect = Exception("Transcript not available")
        await load_youtube_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


@pytest.mark.asyncio
async def test_inspect_document_tool_youtube() -> None:
    """Test the InspectDocumentTool with a YouTube URL."""
    mock_transcript = [
        {"text": "Hello world", "start": 0.0, "duration": 1.5},
        {"text": "This is a test", "start": 1.5, "duration": 2.0},
    ]

    tool = InspectDocumentTool()
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi.get_transcript"
    ) as mock_get:
        mock_get.return_value = mock_transcript
        result = await tool._arun(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            config={"configurable": {}},
        )

        assert "Hello world" in result
        assert "This is a test" in result
        assert "video_id" in result
