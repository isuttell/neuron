from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig

from neuron_server.tools.document_utils import (
    DocumentLoadError,
    extract_video_id,
    is_youtube_url,
    load_youtube_transcript,
)
from neuron_server.tools.inspect_document_tool import (
    InspectDocumentTool,
    InspectDocumentToolArgs,
)


# Helper class for mocking transcript lines
@dataclass
class MockTranscriptLine:
    text: str
    start: float
    duration: float


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

    with (
        patch(
            "neuron_server.tools.document_utils.YouTubeTranscriptApi"
        ) as mock_api_class,
        patch(
            "neuron_server.tools.document_utils.WebVTTFormatter.format_transcript"
        ) as mock_format,
    ):
        mock_api = mock_api_class.return_value
        mock_fetched = AsyncMock()
        mock_fetched.to_raw_data = Mock()
        mock_fetched.to_raw_data.return_value = mock_transcript
        mock_api.fetch.return_value = mock_fetched
        mock_format.return_value = (
            "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nHello world\n\n"
            "00:00:01.500 --> 00:00:03.500\nThis is a test"
        )
        # Re-import after patch
        from neuron_server.tools.document_utils import load_youtube_transcript

        doc = await load_youtube_transcript(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert isinstance(doc, Document)
        assert "Hello world" in doc.page_content
        assert doc.metadata["video_id"] == "dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_load_youtube_transcript_error() -> None:
    """Test error handling for transcript loading."""
    with (
        patch(
            "neuron_server.tools.document_utils.YouTubeTranscriptApi"
        ) as mock_api_class,
        pytest.raises(DocumentLoadError),
    ):
        mock_api = mock_api_class.return_value
        mock_api.fetch.side_effect = Exception("Transcript not available")
        await load_youtube_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


@pytest.mark.asyncio
async def test_inspect_document_tool_youtube() -> None:
    """Test the InspectDocumentTool with a YouTube URL."""
    mock_transcript = [
        {"text": "Hello world", "start": 0.0, "duration": 1.5},
        {"text": "This is a test", "start": 1.5, "duration": 2.0},
    ]

    tool = InspectDocumentTool()
    with (
        patch(
            "neuron_server.tools.document_utils.YouTubeTranscriptApi"
        ) as mock_api_class,
        patch(
            "neuron_server.tools.document_utils.WebVTTFormatter.format_transcript"
        ) as mock_format,
    ):
        mock_api = mock_api_class.return_value
        mock_fetched = AsyncMock()
        mock_fetched.to_raw_data = Mock()
        mock_fetched.to_raw_data.return_value = mock_transcript
        mock_api.fetch.return_value = mock_fetched
        mock_format.return_value = (
            "WEBVTT\n\n00:00:00.000 --> 00:00:01.500\nHello world\n\n"
            "00:00:01.500 --> 00:00:03.500\nThis is a test"
        )
        result = await tool._arun(
            url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            config={"configurable": {}},
        )

    content, artifacts = result
    assert "Hello world" in content
    assert "This is a test" in content
    assert isinstance(artifacts, list)
    assert len(artifacts) == 1
    assert artifacts[0]["media_type"] == "text"


# Tests for memorize functionality
@pytest.mark.asyncio
async def test_inspect_document_tool_args_memorize() -> None:
    """Test InspectDocumentToolArgs with memorize parameter."""
    # Test default memorize value
    args = InspectDocumentToolArgs(url="https://example.com")
    assert args.memorize is False

    # Test explicit memorize=True
    args = InspectDocumentToolArgs(url="https://example.com", memorize=True)
    assert args.memorize is True

    # Test explicit memorize=False
    args = InspectDocumentToolArgs(url="https://example.com", memorize=False)
    assert args.memorize is False


@pytest.mark.asyncio
async def test_inspect_document_tool_memorize_functionality() -> None:
    """Test the memorize functionality with mocked dependencies."""
    # Mock documents to be loaded
    mock_docs = [
        Document(
            page_content="This is a test document with some content to be chunked.",
            metadata={"source": "https://example.com", "title": "Test Doc"},
        ),
        Document(
            page_content="This is another document with different content for testing.",
            metadata={"source": "https://example.com", "title": "Test Doc 2"},
        ),
    ]

    # Mock config
    config = RunnableConfig(
        configurable={
            "user_id": "test_user",
            "thread_id": "test_thread",
            "personality_id": "test_personality",
        }
    )

    tool = InspectDocumentTool()

    with (
        patch(
            "neuron_server.tools.inspect_document_tool.load_document_from_url"
        ) as mock_load,
        patch(
            "neuron_server.tools.inspect_document_tool.memories_store"
        ) as mock_memory_store,
    ):
        mock_load.return_value = mock_docs
        mock_memory_store.aadd_documents = AsyncMock()

        # Test with memorize=True
        result = await tool._arun(
            url="https://example.com", config=config, memorize=True
        )

        # Verify the result contains the document content
        content, artifacts = result
        assert "This is a test document" in content
        assert "This is another document" in content
        assert "<documents>" in content
        assert isinstance(artifacts, list)
        assert len(artifacts) == 1
        assert artifacts[0]["media_type"] == "text"

        # Verify that memories_store.aadd_documents was called
        mock_memory_store.aadd_documents.assert_called_once()

        # Get the documents that were stored in memory
        stored_docs = mock_memory_store.aadd_documents.call_args[0][0]

        # Verify documents were chunked and stored
        assert len(stored_docs) >= 2  # Should have at least 2 chunks

        # Verify each stored document has the correct metadata
        for doc in stored_docs:
            assert doc.metadata["user_id"] == "test_user"
            assert doc.metadata["thread_id"] == "test_thread"
            assert doc.metadata["personality_id"] == "test_personality"
            assert doc.metadata["source"] == "https://example.com"
            assert "chunk_index" in doc.metadata
            assert "document_index" in doc.metadata
            assert "total_chunks" in doc.metadata
            assert doc.metadata["access_count"] == 0
            assert "created_at" in doc.metadata
            assert "stats" in doc.metadata


@pytest.mark.asyncio
async def test_inspect_document_tool_no_memorize() -> None:
    """Test that memorize=False doesn't store documents in memory."""
    mock_docs = [
        Document(
            page_content="Test content", metadata={"source": "https://example.com"}
        )
    ]

    config = RunnableConfig(configurable={"user_id": "test_user"})
    tool = InspectDocumentTool()

    with (
        patch(
            "neuron_server.tools.inspect_document_tool.load_document_from_url"
        ) as mock_load,
        patch(
            "neuron_server.tools.inspect_document_tool.memories_store"
        ) as mock_memory_store,
    ):
        mock_load.return_value = mock_docs
        mock_memory_store.aadd_documents = AsyncMock()

        # Test with memorize=False (default)
        result = await tool._arun(
            url="https://example.com", config=config, memorize=False
        )

        # Verify the result contains the document content
        content, artifacts = result
        assert "Test content" in content
        assert isinstance(artifacts, list)
        assert len(artifacts) == 1
        assert artifacts[0]["media_type"] == "text"

        # Verify that memories_store.aadd_documents was NOT called
        mock_memory_store.aadd_documents.assert_not_called()


@pytest.mark.asyncio
async def test_inspect_document_tool_memorize_chunking() -> None:
    """Test that large documents are properly chunked when memorized."""
    # Create a large document that should be split into multiple chunks
    large_content = "This is a test sentence. " * 100  # ~2500 characters
    mock_docs = [
        Document(page_content=large_content, metadata={"source": "https://example.com"})
    ]

    config = RunnableConfig(
        configurable={"user_id": "test_user", "thread_id": "test_thread"}
    )

    tool = InspectDocumentTool()

    with (
        patch(
            "neuron_server.tools.inspect_document_tool.load_document_from_url"
        ) as mock_load,
        patch(
            "neuron_server.tools.inspect_document_tool.memories_store"
        ) as mock_memory_store,
    ):
        mock_load.return_value = mock_docs
        mock_memory_store.aadd_documents = AsyncMock()

        await tool._arun(url="https://example.com", config=config, memorize=True)

        # Get the stored documents
        stored_docs = mock_memory_store.aadd_documents.call_args[0][0]

        # Verify multiple chunks were created
        assert len(stored_docs) > 1

        # Verify chunk metadata is correct
        for i, doc in enumerate(stored_docs):
            assert doc.metadata["chunk_index"] == i
            assert doc.metadata["total_chunks"] == len(stored_docs)
            assert doc.metadata["document_index"] == 0
            # Each chunk should be roughly 1000 characters or less
            assert len(doc.page_content) <= 1200  # Allow for overlap


@pytest.mark.asyncio
async def test_inspect_document_tool_memorize_error_handling() -> None:
    """Test that memory storage errors don't break document inspection."""
    mock_docs = [
        Document(
            page_content="Test content", metadata={"source": "https://example.com"}
        )
    ]

    config = RunnableConfig(configurable={"user_id": "test_user"})
    tool = InspectDocumentTool()

    with (
        patch(
            "neuron_server.tools.inspect_document_tool.load_document_from_url"
        ) as mock_load,
        patch(
            "neuron_server.tools.inspect_document_tool.memories_store"
        ) as mock_memory_store,
        patch("neuron_server.tools.inspect_document_tool.logger") as mock_logger,
    ):
        mock_load.return_value = mock_docs
        # Make memory storage fail
        mock_memory_store.aadd_documents = AsyncMock(
            side_effect=Exception("Memory storage failed")
        )

        # This should not raise an exception
        result = await tool._arun(
            url="https://example.com", config=config, memorize=True
        )

        # Verify the result still contains the document content
        content, artifacts = result
        assert "Test content" in content
        assert isinstance(artifacts, list)
        assert len(artifacts) == 1
        assert artifacts[0]["media_type"] == "text"

        # Verify error was logged
        mock_logger.error.assert_called_once()
