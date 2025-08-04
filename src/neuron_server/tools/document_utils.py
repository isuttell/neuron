import os
import re
import time
from typing import Any

import aiohttp
import pymupdf4llm
import tiktoken
from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import WebVTTFormatter

from neuron_server.config import config as neuron_config
from neuron_server.controllers.csrf import create_session_cookie
from neuron_server.logger import logger


class DocumentLoadError(Exception):
    """Base exception for document loading errors."""

    pass


class NetworkError(DocumentLoadError):
    """Raised when network-related errors occur during document loading."""

    pass


class FileFormatError(DocumentLoadError):
    """Raised when document format is invalid or unsupported."""

    pass


class LocalNetworkError(DocumentLoadError):
    """Raised when attempting to access restricted local network URLs."""

    pass


def is_youtube_url(url: str) -> bool:
    """Check if a URL is a YouTube video URL.

    Args:
        url: The URL to check

    Returns:
        bool: True if the URL is a YouTube video URL
    """
    patterns = [
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)",
        r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)",
    ]
    return any(re.match(pattern, url) for pattern in patterns)


def extract_video_id(url: str) -> str:
    """Extract the video ID from a YouTube URL.

    Args:
        url: The YouTube URL

    Returns:
        str: The video ID

    Raises:
        ValueError: If the URL is not a valid YouTube URL
    """
    for pattern in [
        r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([a-zA-Z0-9_-]+)",
        r"(?:https?:\/\/)?(?:www\.)?youtu\.be\/([a-zA-Z0-9_-]+)",
    ]:
        if match := re.match(pattern, url):
            return match.group(1)
    raise ValueError(f"Invalid YouTube URL: {url}")


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string using tokenizer."""
    encoder = tiktoken.encoding_for_model("gpt-4o")
    return len(encoder.encode(text))


def truncate_response(text: str, max_tokens: int = 20000) -> str:
    """Truncate response if it exceeds token limit.

    Args:
        text: The text to potentially truncate
        max_tokens: Maximum token limit (default: 20000)

    Returns:
        Original text if under limit, or truncated text with truncation message
    """
    token_count = count_tokens(text)

    if token_count <= max_tokens:
        return text

    # Estimate characters per token (rough approximation)
    chars_per_token = len(text) / token_count
    max_chars = int(max_tokens * chars_per_token * 0.9)  # 90% safety margin

    truncated = text[:max_chars]
    truncation_msg = (
        f"\n\n[RESPONSE TRUNCATED: Original response was {token_count} tokens, "
        f"truncated to stay under {max_tokens} token limit]"
    )

    return truncated + truncation_msg


async def load_youtube_transcript(
    url: str,
    metadata: dict[str, Any] | None = None,
) -> Document:
    """Load transcripts from a YouTube video.

    Args:
        url: The YouTube video URL
        metadata: Optional metadata to include

    Returns:
        Document: The transcript document with pretty-printed subtitles

    Raises:
        DocumentLoadError: If transcripts cannot be loaded
    """
    try:
        video_id = extract_video_id(url)
        api = YouTubeTranscriptApi()
        fetched_transcript = api.fetch(video_id)
        transcript = fetched_transcript.to_raw_data()

        # Convert dictionary items to objects with attributes if needed
        class TranscriptItem:
            def __init__(self, item_dict: dict[str, Any]) -> None:
                self.text = item_dict.get("text", "")
                self.start = item_dict.get("start", 0.0)
                self.duration = item_dict.get("duration", 0.0)

        # Convert if transcript items are dictionaries
        if transcript and isinstance(transcript[0], dict):
            transcript = [TranscriptItem(item) for item in transcript]

        formatter = WebVTTFormatter()
        return Document(
            page_content=formatter.format_transcript(transcript),
            metadata={
                "title": f"YouTube Transcript - {video_id}",
                "sourceURL": url,
                "video_id": video_id,
                "type": "youtube_transcript",
                "updated_at": int(time.time()),
                **(metadata or {}),
            },
        )
    except Exception as e:
        raise DocumentLoadError(f"Failed to load YouTube transcript: {str(e)}") from e


async def load_pdf_from_url(
    url: str, metadata: dict[str, Any] | None = None
) -> Document:
    """Load a PDF document from a URL.

    Args:
        url: The URL of the PDF document
        metadata: Optional metadata to include

    Returns:
        Document: The loaded PDF document

    Raises:
        DocumentLoadError: If the PDF cannot be loaded
    """
    import tempfile

    temp_file = None
    try:
        # Create a temporary file that will be automatically cleaned up
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tf:
            temp_file = tf.name

            # Generate proper signed session cookie for internal tool access

            session_cookie, _ = create_session_cookie("system", include_csrf=True)
            cookies = {"neuron_session": session_cookie}

            async with aiohttp.ClientSession(cookies=cookies) as session:
                try:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            tf.write(chunk)
                except aiohttp.ClientError as e:
                    raise NetworkError(f"Failed to download PDF: {str(e)}") from e
        try:
            text = pymupdf4llm.to_markdown(temp_file, show_progress=True)
        except Exception as e:
            raise FileFormatError(f"Failed to parse PDF: {str(e)}") from e
        return Document(
            page_content=text,
            metadata={
                "title": url.rsplit("/", 1)[-1],
                "sourceURL": url,
                "type": "pdf",
                "updated_at": int(time.time()),
                **(metadata or {}),
            },
        )
    except (NetworkError, FileFormatError) as e:
        raise e
    except Exception as e:
        raise DocumentLoadError(f"Unexpected error loading PDF: {str(e)}") from e
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


async def load_text_from_url(
    url: str, metadata: dict[str, Any] | None = None
) -> Document:
    """Load a text document from a URL.

    Args:
        url: The URL of the text document
        metadata: Optional metadata to include

    Returns:
        Document: The loaded text document

    Raises:
        DocumentLoadError: If the text cannot be loaded
    """
    try:
        # Generate proper signed session cookie for internal tool access

        session_cookie, _ = create_session_cookie("system", include_csrf=True)
        cookies = {"neuron_session": session_cookie}

        async with aiohttp.ClientSession(cookies=cookies) as session:
            async with session.get(url) as response:
                response.raise_for_status()
                text = await response.text()
                extension = url.rsplit(".", 1)[-1] if "." in url else "txt"
            return Document(
                page_content=text,
                metadata={
                    "title": url.rsplit("/", 1)[-1],
                    "sourceURL": url,
                    "type": extension,
                    "updated_at": int(time.time()),
                    **(metadata or {}),
                },
            )
    except Exception as e:
        raise DocumentLoadError(f"Failed to load text: {str(e)}") from e


async def load_document_from_url(
    url: str,
    metadata: dict[str, Any] | None = None,
) -> list[Document]:
    """Load documents from a URL.

    Args:
        url: The URL to load documents from
        metadata: Optional metadata to include

    Returns:
        list[Document]: The loaded documents

    Raises:
        DocumentLoadError: If the documents cannot be loaded
    """
    try:
        if is_youtube_url(url):
            doc = await load_youtube_transcript(url, metadata=metadata)
            return [doc]

        if (
            url.endswith(".txt")
            or url.endswith(".md")
            or url.endswith(".csv")
            or url.endswith(".srt")
            or url.endswith(".vtt")
        ):
            doc = await load_text_from_url(url, metadata=metadata)
            return [doc]

        if url.endswith(".pdf"):
            doc = await load_pdf_from_url(url, metadata=metadata)
            return [doc]

        if "zaks.io" in url or "192.168" in url:
            raise LocalNetworkError(
                "FireCrawl cannot access urls on the local network."
            )

        from firecrawl import AsyncFirecrawlApp

        app = AsyncFirecrawlApp(api_key=neuron_config.firecrawl_api_key)
        result = await app.scrape_url(url)

        # Safe access to markdown content
        page_content = ""
        if hasattr(result, "markdown") and result.markdown:
            page_content = result.markdown
        elif hasattr(result, "data") and hasattr(result.data, "markdown"):
            page_content = result.data.markdown

        # Safe access to metadata
        doc_metadata = {
            "sourceURL": url,
            "type": "webpage",
            "updated_at": int(time.time()),
        }

        # Extract title and other metadata safely
        if hasattr(result, "metadata") and result.metadata:
            if isinstance(result.metadata, dict):
                doc_metadata["title"] = result.metadata.get("title", "")
                doc_metadata.update(result.metadata)
            else:
                # If metadata is an object, try to get title attribute
                doc_metadata["title"] = getattr(result.metadata, "title", "")
                if hasattr(result.metadata, "__dict__"):
                    doc_metadata.update(result.metadata.__dict__)

        # Add any custom metadata passed in
        if metadata:
            doc_metadata.update(metadata)

        return [Document(page_content=page_content, metadata=doc_metadata)]
    except (NetworkError, FileFormatError, LocalNetworkError) as e:
        logger.error(f"Failed to load document from {url}: {e}")
        raise e
    except Exception as e:
        logger.error(f"Failed to load document from {url}: {e}")
        raise DocumentLoadError(f"Failed to load document: {str(e)}") from e
