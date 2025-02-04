"""Unit tests for document_utils.py."""

import os
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses
from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi

from neuron_server.config import config as neuron_config
from neuron_server.tools.document_utils import (
    DocumentLoadError,
    FileFormatError,
    LocalNetworkError,
    NetworkError,
    count_tokens,
    extract_video_id,
    is_youtube_url,
    load_document_from_url,
    load_pdf_from_url,
    load_text_from_url,
    load_youtube_transcript,
)


@pytest.fixture
def mock_youtube_transcript() -> list[dict[str, Any]]:
    """Fixture for mock YouTube transcript data."""
    return [
        {"text": "First line", "start": 0.0, "duration": 2.0},
        {"text": "Second line", "start": 2.0, "duration": 2.0},
    ]


@pytest.fixture
def mock_pdf_content() -> str:
    """Fixture for mock PDF content."""
    return "Sample PDF content for testing"


@pytest.fixture
def mock_text_content() -> str:
    """Fixture for mock text file content."""
    return "Sample text content for testing"


@pytest.fixture
def mock_aiohttp() -> aioresponses:
    """Fixture for mocked aiohttp responses."""
    with aioresponses() as m:
        yield m


@pytest_asyncio.fixture
async def mock_aiohttp_session() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """Fixture for mocked aiohttp ClientSession."""
    async with aiohttp.ClientSession() as session:
        yield session


class TestYouTubeUrlHandling:
    """Tests for YouTube URL handling functions."""

    def test_valid_youtube_urls(self) -> None:
        """Test validation of valid YouTube URLs."""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "http://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "http://youtu.be/dQw4w9WgXcQ",
        ]
        for url in valid_urls:
            assert is_youtube_url(url)

    def test_invalid_youtube_urls(self) -> None:
        """Test validation of invalid YouTube URLs."""
        invalid_urls = [
            "https://www.example.com",
            "https://youtube.com",
            "https://youtu.be",
            "invalid_string",
        ]
        for url in invalid_urls:
            assert not is_youtube_url(url)

    def test_video_id_extraction(self) -> None:
        """Test extracting video IDs from valid YouTube URLs."""
        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ]
        for url, expected_id in test_cases:
            assert extract_video_id(url) == expected_id

    def test_invalid_video_id_extraction(self) -> None:
        """Test error handling for invalid YouTube URLs during ID extraction."""
        with pytest.raises(ValueError):
            extract_video_id("https://example.com")


class TestTokenCounting:
    """Tests for token counting function."""

    def test_token_counting(self) -> None:
        """Test counting tokens in normal text."""
        text = "This is a test sentence."
        assert isinstance(count_tokens(text), int)
        assert count_tokens(text) > 0

    def test_empty_string_tokens(self) -> None:
        """Test counting tokens in an empty string."""
        assert count_tokens("") == 0

    def test_special_characters_tokens(self) -> None:
        """Test counting tokens in text with special characters."""
        text = "!@#$%^&*()_+ Special chars"
        assert isinstance(count_tokens(text), int)
        assert count_tokens(text) > 0


class TestYouTubeTranscriptLoading:
    """Tests for YouTube transcript loading function."""

    @pytest.mark.asyncio
    async def test_successful_transcript_loading(
        self, mock_youtube_transcript: list[dict[str, Any]]
    ) -> None:
        """Test successful loading of YouTube transcript."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        with patch.object(
            YouTubeTranscriptApi,
            "get_transcript",
            return_value=mock_youtube_transcript,
        ):
            doc = await load_youtube_transcript(url)
            assert isinstance(doc, Document)
            assert "First line" in doc.page_content
            assert doc.metadata["video_id"] == "dQw4w9WgXcQ"
            assert doc.metadata["type"] == "youtube_transcript"

    @pytest.mark.asyncio
    async def test_transcript_loading_error(self) -> None:
        """Test error handling during transcript loading."""
        url = "https://www.youtube.com/watch?v=invalid"

        with (
            patch.object(
                YouTubeTranscriptApi,
                "get_transcript",
                side_effect=Exception("Transcript not found"),
            ),
            pytest.raises(DocumentLoadError),
        ):
            await load_youtube_transcript(url)

    @pytest.mark.asyncio
    async def test_transcript_metadata_merging(
        self, mock_youtube_transcript: list[dict[str, Any]]
    ) -> None:
        """Test metadata merging in transcript loading."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        custom_metadata = {"custom_key": "custom_value"}

        with patch.object(
            YouTubeTranscriptApi,
            "get_transcript",
            return_value=mock_youtube_transcript,
        ):
            doc = await load_youtube_transcript(url, metadata=custom_metadata)
            assert doc.metadata["custom_key"] == "custom_value"
            assert doc.metadata["video_id"] == "dQw4w9WgXcQ"


class TestPdfLoading:
    """Tests for PDF loading function."""

    @pytest.mark.asyncio
    async def test_successful_pdf_loading(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
        mock_pdf_content: str,
    ) -> None:
        """Test successful loading of PDF document."""
        url = "https://example.com/test.pdf"
        mock_aiohttp.get(url, status=200, body=b"PDF content")

        with patch("pymupdf4llm.to_markdown", return_value=mock_pdf_content):
            doc = await load_pdf_from_url(url)
            assert isinstance(doc, Document)
            assert doc.page_content == mock_pdf_content
            assert doc.metadata["type"] == "pdf"

    @pytest.mark.asyncio
    async def test_pdf_loading_network_error(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test network error handling during PDF loading."""
        url = "https://example.com/test.pdf"
        mock_aiohttp.get(url, status=404)
        with pytest.raises(NetworkError):
            await load_pdf_from_url(url)

    @pytest.mark.asyncio
    async def test_pdf_loading_format_error(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test format error handling during PDF loading."""
        url = "https://example.com/test.pdf"
        mock_aiohttp.get(url, status=200, body=b"Not a PDF file")

        with (
            patch("pymupdf4llm.to_markdown", side_effect=Exception("Invalid PDF")),
            pytest.raises(FileFormatError),
        ):
            await load_pdf_from_url(url)

    @pytest.mark.asyncio
    async def test_pdf_metadata_merging(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
        mock_pdf_content: str,
    ) -> None:
        """Test metadata merging in PDF loading."""
        url = "https://example.com/test.pdf"
        mock_aiohttp.get(url, status=200, body=b"PDF content")
        custom_metadata = {"custom_key": "custom_value"}

        with patch("pymupdf4llm.to_markdown", return_value=mock_pdf_content):
            doc = await load_pdf_from_url(url, metadata=custom_metadata)
            assert doc.metadata["custom_key"] == "custom_value"
            assert doc.metadata["type"] == "pdf"

    @pytest.mark.asyncio
    async def test_temp_file_cleanup(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
        mock_pdf_content: str,
    ) -> None:
        """Test cleanup of temporary PDF files."""
        url = "https://example.com/test.pdf"
        mock_aiohttp.get(url, status=200, body=b"PDF content")

        with patch("pymupdf4llm.to_markdown", return_value=mock_pdf_content):
            await load_pdf_from_url(url)
            # Verify temp file is cleaned up
            temp_files = [
                f for f in os.listdir(neuron_config.temp_folder) if f.endswith(".pdf")
            ]
            assert not temp_files


class TestTextLoading:
    """Tests for text file loading function."""

    @pytest.mark.asyncio
    async def test_txt_loading(
        self, mock_aiohttp_session: aiohttp.ClientSession, mock_aiohttp: aioresponses
    ) -> None:
        """Test loading .txt file."""
        url = "https://example.com/test.txt"
        mock_aiohttp.get(url, status=200, body="Sample text content")
        doc = await load_text_from_url(url)
        assert isinstance(doc, Document)
        assert doc.metadata["type"] == "txt"
        assert doc.page_content == "Sample text content"

    @pytest.mark.asyncio
    async def test_md_loading(
        self, mock_aiohttp_session: aiohttp.ClientSession, mock_aiohttp: aioresponses
    ) -> None:
        """Test loading .md file."""
        url = "https://example.com/test.md"
        mock_aiohttp.get(url, status=200, body="# Sample markdown")
        doc = await load_text_from_url(url)
        assert isinstance(doc, Document)
        assert doc.metadata["type"] == "md"
        assert doc.page_content == "# Sample markdown"

    @pytest.mark.asyncio
    async def test_csv_loading(
        self, mock_aiohttp_session: aiohttp.ClientSession, mock_aiohttp: aioresponses
    ) -> None:
        """Test loading .csv file."""
        url = "https://example.com/test.csv"
        mock_aiohttp.get(url, status=200, body="id,name\n1,test")
        doc = await load_text_from_url(url)
        assert isinstance(doc, Document)
        assert doc.metadata["type"] == "csv"
        assert doc.page_content == "id,name\n1,test"

    @pytest.mark.asyncio
    async def test_loading_error(
        self, mock_aiohttp_session: aiohttp.ClientSession, mock_aiohttp: aioresponses
    ) -> None:
        """Test error handling during text loading."""
        url = "https://example.com/test.txt"
        mock_aiohttp.get(url, status=404)
        with pytest.raises(DocumentLoadError):
            await load_text_from_url(url)

    @pytest.mark.asyncio
    async def test_text_metadata_merging(
        self, mock_aiohttp_session: aiohttp.ClientSession, mock_aiohttp: aioresponses
    ) -> None:
        """Test metadata merging in text loading."""
        url = "https://example.com/test.txt"
        mock_aiohttp.get(url, status=200, body="Sample text content")
        custom_metadata = {"custom_key": "custom_value"}
        doc = await load_text_from_url(url, metadata=custom_metadata)
        assert doc.metadata["custom_key"] == "custom_value"
        assert doc.metadata["type"] == "txt"
        assert doc.page_content == "Sample text content"


class TestDocumentLoading:
    """Tests for document loading function."""

    @pytest.mark.asyncio
    async def test_youtube_url_loading(
        self, mock_youtube_transcript: list[dict[str, Any]]
    ) -> None:
        """Test loading YouTube URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

        with patch.object(
            YouTubeTranscriptApi,
            "get_transcript",
            return_value=mock_youtube_transcript,
        ):
            docs = await load_document_from_url(url)
            assert len(docs) == 1
            assert docs[0].metadata["type"] == "youtube_transcript"

    @pytest.mark.asyncio
    async def test_pdf_url_loading(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
        mock_pdf_content: str,
    ) -> None:
        """Test loading PDF URL."""
        url = "https://example.com/test.pdf"
        mock_aiohttp.get(url, status=200, body=b"PDF content")

        with patch("pymupdf4llm.to_markdown", return_value=mock_pdf_content):
            docs = await load_document_from_url(url)
            assert len(docs) == 1
            assert docs[0].metadata["type"] == "pdf"
            assert docs[0].page_content == mock_pdf_content

    @pytest.mark.asyncio
    async def test_text_url_loading(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test loading text URL."""
        url = "https://example.com/test.txt"
        mock_aiohttp.get(url, status=200, body="Sample text content")
        docs = await load_document_from_url(url)
        assert len(docs) == 1
        assert docs[0].metadata["type"] == "txt"
        assert docs[0].page_content == "Sample text content"

    @pytest.mark.asyncio
    async def test_webpage_loading(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test loading webpage URL."""
        url = "https://example.com"
        mock_docs = [Document(page_content="test content", metadata={"source": url})]

        with patch(
            "langchain_community.document_loaders.FireCrawlLoader"
        ) as mock_loader_class:
            mock_loader = mock_loader_class.return_value
            mock_loader.aload = AsyncMock(return_value=mock_docs)
            docs = await load_document_from_url(url)
            assert len(docs) == 1
            assert docs[0].metadata["type"] == "webpage"

    @pytest.mark.asyncio
    async def test_webpage_scrape_mode(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test scrape mode for webpage loading."""
        url = "https://example.com"
        mock_docs = [Document(page_content="test content", metadata={"source": url})]

        with patch(
            "langchain_community.document_loaders.FireCrawlLoader"
        ) as mock_loader_class:
            mock_loader = mock_loader_class.return_value
            mock_loader.aload = AsyncMock(return_value=mock_docs)
            docs = await load_document_from_url(url, mode="scrape")
            assert len(docs) == 1
            assert docs[0].metadata["type"] == "webpage"
            mock_loader_class.assert_called_once_with(
                api_key=mock_loader_class.call_args[1]["api_key"],
                url=url,
                mode="scrape",
            )

    @pytest.mark.asyncio
    async def test_local_network_restriction(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test restriction on local network URLs."""
        urls = ["http://zaks.io/test", "http://192.168.1.1/test"]
        for url in urls:
            with pytest.raises(LocalNetworkError):
                await load_document_from_url(url)

    @pytest.mark.asyncio
    async def test_loading_error(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test error handling during document loading."""
        url = "https://example.com"
        mock_aiohttp.get(url, status=404)
        with pytest.raises(DocumentLoadError):
            await load_document_from_url(url)

    @pytest.mark.asyncio
    async def test_metadata_merging(
        self,
        mock_aiohttp_session: aiohttp.ClientSession,
        mock_aiohttp: aioresponses,
    ) -> None:
        """Test metadata merging in document loading."""
        url = "https://example.com/test.txt"
        mock_aiohttp.get(url, status=200, body="Sample text content")
        custom_metadata = {"custom_key": "custom_value"}
        docs = await load_document_from_url(url, metadata=custom_metadata)
        assert len(docs) == 1
        assert docs[0].metadata["custom_key"] == "custom_value"
        assert docs[0].page_content == "Sample text content"

    @pytest.mark.asyncio
    async def test_crawl_mode(self) -> None:
        """Test crawl mode parameter."""
        url = "https://example.com"
        mock_docs = [Document(page_content="test content", metadata={"source": url})]

        with patch(
            "langchain_community.document_loaders.FireCrawlLoader"
        ) as mock_loader_class:
            mock_loader = mock_loader_class.return_value
            mock_loader.aload = AsyncMock(return_value=mock_docs)
            docs = await load_document_from_url(url, mode="crawl")
            assert len(docs) == 1
            assert docs[0].metadata["type"] == "webpage"
            mock_loader_class.assert_called_once_with(
                api_key=mock_loader_class.call_args[1]["api_key"],
                url=url,
                mode="crawl",
            )
