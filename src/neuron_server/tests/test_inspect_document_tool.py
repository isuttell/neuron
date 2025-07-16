from dataclasses import dataclass
from unittest.mock import AsyncMock, patch

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
        MockTranscriptLine(text="Hello world", start=0.0, duration=1.5),
        MockTranscriptLine(text="This is a test", start=1.5, duration=2.0),
    ]

    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi.get_transcript"
    ) as mock_get:
        mock_get.return_value = mock_transcript
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
        patch("youtube_transcript_api.YouTubeTranscriptApi.get_transcript") as mock_get,
        pytest.raises(DocumentLoadError),
    ):
        mock_get.side_effect = Exception("Transcript not available")
        await load_youtube_transcript("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


@pytest.mark.asyncio
async def test_inspect_document_tool_youtube() -> None:
    """Test the InspectDocumentTool with a YouTube URL."""
    mock_transcript = [
        MockTranscriptLine(text="Hello world", start=0.0, duration=1.5),
        MockTranscriptLine(text="This is a test", start=1.5, duration=2.0),
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
    # assert "Summary of the document" in result # Output format changed


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
            url="https://example.com", config=config, mode="scrape", memorize=True
        )

        # Verify the result contains the document content
        assert "This is a test document" in result
        assert "This is another document" in result
        assert "<documents>" in result

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
            url="https://example.com", config=config, mode="scrape", memorize=False
        )

        # Verify the result contains the document content
        assert "Test content" in result

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

        await tool._arun(
            url="https://example.com", config=config, mode="scrape", memorize=True
        )

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
            url="https://example.com", config=config, mode="scrape", memorize=True
        )

        # Verify the result still contains the document content
        assert "Test content" in result

        # Verify error was logged
        mock_logger.error.assert_called_once()
