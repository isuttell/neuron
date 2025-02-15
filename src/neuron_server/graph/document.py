"""Document processing and chunk handling functions for Neo4j graph operations.

This module provides functionality for processing documents and storing their content
in a Neo4j graph database. It handles document chunking, information extraction,
and graph relationship construction. Key features include:

- Document chunking with configurable size and overlap
- Concurrent processing of document chunks
- Atomic fact extraction from text
- Graph relationship construction
- Document summarization and analysis
"""

# Standard library imports
import asyncio
import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

# Third-party imports
from langchain_core.runnables import RunnableConfig
from langchain_text_splitters import TokenTextSplitter

# Local imports
from neuron_server.logger import logger

from .chains import summary_chain
from .connection import get_graph
from .construction import construction_chain, import_query, match_query
from .models import DocumentResult, Extraction, SummaryResponse
from .utils import encode_md5


@dataclass
class DocumentMetadata:
    """Metadata for a document."""

    document_id: str
    document_name: str | None = None
    personality_id: str | None = None
    user_id: str | None = None
    source: str | None = None


@dataclass
class ChunkConfig:
    """Configuration for chunk processing."""

    chunk_size: int = 2000
    chunk_overlap: int = 200
    max_attempts: int = 3
    retry_delay_seconds: int = 1


# Module-level default configuration
DEFAULT_CHUNK_CONFIG: Final[ChunkConfig] = ChunkConfig()


def import_chunks(
    texts: Sequence[str],
    extractions: Sequence[Extraction],
    metadata: DocumentMetadata,
) -> None:
    """Import document chunks and their extracted information into Neo4j.

    Args:
        texts: List of text chunks from the document.
        extractions: List of extracted information for each chunk.
        metadata: Document metadata including IDs and source information.
    """
    docs: list[dict[str, Any]] = [extraction.model_dump() for extraction in extractions]
    for index, doc in enumerate(docs):
        doc["chunk_id"] = encode_md5(texts[index])
        doc["chunk_text"] = texts[index]
        doc["index"] = index
        for af in doc["atomic_facts"]:
            af["id"] = encode_md5(af["atomic_fact"])

    get_graph().query(
        import_query,
        params={
            "data": docs,
            "document_id": metadata.document_id,
            "document_name": metadata.document_name,
            "personality_id": metadata.personality_id,
            "user_id": metadata.user_id,
            "source": metadata.source,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    )

    get_graph().query(match_query, params={"document_id": metadata.document_id})
    get_graph().refresh_schema()


async def process_chunk(
    input_text: str,
    index: int,
    config: RunnableConfig | None,
    semaphore: asyncio.Semaphore,
    chunk_config: ChunkConfig = DEFAULT_CHUNK_CONFIG,
) -> Extraction:
    """Process a single chunk of text to extract information.

    Args:
        input_text: Text chunk to process.
        index: Index of the chunk in the document.
        config: Configuration for the LangChain runnable.
        semaphore: Semaphore for controlling concurrent processing.
        chunk_config: Configuration for chunk processing.

    Returns:
        Extraction object containing the processed information.

    Raises:
        Exception: If processing fails after all retry attempts.
    """
    start_time = time.perf_counter()
    async with semaphore:
        for attempt in range(chunk_config.max_attempts):
            try:
                results: Extraction = await construction_chain.ainvoke(
                    input_text, config=config
                )
                duration = time.perf_counter() - start_time
                logger.debug(
                    "Found %d atomic facts for chunk #%d - %.2fs",
                    len(results.atomic_facts),
                    index,
                    duration,
                )
                return results
            except Exception as e:
                if attempt < chunk_config.max_attempts - 1:
                    logger.warning(
                        "Error processing chunk %d: %s. Retry in %ds...",
                        index,
                        str(e),
                        chunk_config.retry_delay_seconds,
                    )
                    await asyncio.sleep(chunk_config.retry_delay_seconds)
                else:
                    raise e
    return None  # Explicit return for RET503


async def process_document(
    text: str,
    config: RunnableConfig,
    metadata: DocumentMetadata,
    chunk_config: ChunkConfig = DEFAULT_CHUNK_CONFIG,
) -> DocumentResult:
    """Process a document by splitting it into chunks and extracting information.

    Args:
        text: Full text of the document to process.
        config: Configuration for the LangChain runnable.
        metadata: Document metadata including IDs and source information.
        chunk_config: Configuration for chunk processing.

    Returns:
        DocumentResult containing extracted information and analysis.
    """
    start_time = time.perf_counter()
    logger.debug("Started graph extraction...")
    personality_id: str | None = config["configurable"].get("personality_id")
    assert personality_id is not None
    user_id: str | None = config["configurable"].get("user_id")
    assert user_id is not None
    metadata.personality_id = personality_id
    metadata.user_id = user_id

    text_splitter = TokenTextSplitter(
        chunk_size=chunk_config.chunk_size,
        chunk_overlap=chunk_config.chunk_overlap,
    )
    texts = text_splitter.split_text(text)

    # Limit to 10 concurrent tasks
    semaphore = asyncio.Semaphore(10)
    logger.debug("Extracting atomic facts from %d text chunks", len(texts))
    extractions: list[Extraction] = await asyncio.gather(
        *[
            process_chunk(
                input_text=input_text,
                config=config,
                semaphore=semaphore,
                index=index,
                chunk_config=chunk_config,
            )
            for index, input_text in enumerate(texts)
        ]
    )

    import_chunks(
        texts=texts,
        extractions=extractions,
        metadata=metadata,
    )

    summary_response: SummaryResponse = await summary_chain.ainvoke(
        {
            "input": "\n\n".join(
                [extraction.description for extraction in extractions]
            ),
        }
    )
    logger.debug("Finished graph extraction - %.2fs", time.perf_counter() - start_time)
    return DocumentResult(
        document_id=metadata.document_id,
        document_name=metadata.document_name,
        source=metadata.source,
        keywords=summary_response.keywords,
        summary=summary_response.summary,
        analysis=summary_response.critical_analysis,
    )


def get_document(document_id: str, personality_id: str) -> dict[str, str] | None:
    """Get document information from Neo4j.

    Args:
        document_id: ID of the document to retrieve.
        personality_id: ID of the personality that processed the document.

    Returns:
        Dictionary containing document information or None if not found.
    """
    data = get_graph().query(
        """
MATCH (c:Chunk)<-[:HAS_CHUNK]-(doc:Document)
WHERE doc.id = $id AND c.personality_id = $personality_id
RETURN doc.id AS document_id, doc.name AS document_name,
       c.id AS chunk_id, c.text AS text,
       c.updated_at AS updated_at
    """.strip(),
        params={"id": document_id, "personality_id": personality_id},
    )
    return data if data else None
