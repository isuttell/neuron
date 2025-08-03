import asyncio
import json
import time
from typing import Literal
from uuid import uuid4

from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.tools.artifact_types import (
    ToolArtifactMetadata,
    ToolMediaArtifact,
    ToolMediaItem,
)
from neuron_server.tools.document_utils import (
    DocumentLoadError as BaseDocumentError,
)
from neuron_server.tools.document_utils import (
    load_document_from_url,
)
from neuron_server.tools.memory_recall_tool import MemoryStats
from neuron_server.vectorstores import memories_store


class InspectDocumentToolError(BaseDocumentError):
    """Error raised by the InspectDocumentTool."""

    pass


class InspectDocumentToolArgs(BaseModel):
    url: str = Field(
        description=(
            "The url of the document or website to inspect. Supports html websites, "
            "text files, pdfs, csvs, markdown documents, and youtube urls"
        )
    )
    mode: Literal["scrape", "crawl"] | None = Field(
        "scrape",
        description=(
            "The mode of the website import. Can be 'scrape' or 'crawl'. Scrape is "
            "for a single url and Crawl is for the url and all accessible sub pages. "
            "Only used when importing websites."
        ),
    )
    memorize: bool = Field(
        False,
        description=(
            "Whether to save the document content to memory for later retrieval. "
            "Documents will be chunked and stored in the agent's memory for RAG. "
            "Use this when you want to remember the document for future conversations."
        ),
    )
    display_name: str | None = Field(
        None,
        description=(
            "Optional display name for the document. If provided, this will be used "
            "instead of the file hash for the artifact name. Use this to "
            "provide a more user-friendly name for the document."
        ),
    )


class InspectDocumentTool(BaseTool):
    name: str = "document_inspect"
    description: str = """
This tool downloads documents, scrapes websites, extracts transcripts from youtube
videos, and returns the raw text.

Use this to answer questions about a website or document.

You can optionally set memorize=true to save the document content to memory for
later retrieval through RAG. Documents will be automatically chunked and stored.

Supported document types:
txt
md
csv
srt
vtt
pdf
youtube
""".strip()
    args_schema: type[InspectDocumentToolArgs] = InspectDocumentToolArgs
    response_format: str = "content_and_artifact"

    def _run(
        self,
        url: str,
        config: RunnableConfig,
        mode: str | None = None,
        memorize: bool = False,
        display_name: str | None = None,
    ) -> tuple[str, list[dict]]:
        return asyncio.run(self._arun(url, config, mode, memorize, display_name))

    async def _arun(
        self,
        url: str,
        config: RunnableConfig,
        mode: str | None = None,
        memorize: bool = False,
        display_name: str | None = None,
    ) -> tuple[str, list[dict]]:
        try:
            # Record the start time for performance measurement
            start_time = time.perf_counter()
            logger.debug(f"Processing '{url}'")

            loaded_docs = await load_document_from_url(
                url,
                mode=mode,
                metadata={
                    "personality_id": (
                        config["configurable"].get("personality_id", None)
                        if config
                        else None
                    ),
                    "user_id": (
                        config["configurable"].get("user_id", None) if config else None
                    ),
                },
            )
            if len(loaded_docs) == 0:
                raise InspectDocumentToolError("No documents found")

            results = []
            for index, doc in enumerate(loaded_docs):
                # Add display_name to metadata if provided
                if display_name:
                    doc.metadata["display_name"] = display_name
                metadata_str = json.dumps(doc.metadata or {}, indent=2)
                results.append(
                    f"""\
    <document index="{index}">
        <source>{doc.metadata.get("source", url)}</source>
        <document_content>{doc.page_content.strip()}</document_content>
        <document_metadata>{metadata_str}</document_metadata>
    </document>
"""
                )

            # Store documents in memory if requested
            if memorize:
                await self._store_in_memory(loaded_docs, url, config)

            duration = time.perf_counter() - start_time
            logger.debug(f"Processed '{url}' - {duration:.2f}s")
            docs = "\n\n".join(results)

            artifacts = [
                ToolMediaArtifact(
                    media_type="text",
                    items=[
                        ToolMediaItem(
                            id=str(uuid4()),
                            url=doc.metadata.get("source", url),
                            name=(
                                display_name or doc.metadata.get("title", "Document")
                            ),
                            description=doc.page_content.strip(),
                            metadata=ToolArtifactMetadata(
                                type=doc.metadata.get("type", None)
                            ),
                        )
                        for doc in loaded_docs
                    ],
                )
            ]

            return (
                f"<documents>\n{docs}\n</documents>",
                [artifact.model_dump() for artifact in artifacts],
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e

    async def _store_in_memory(
        self,
        documents: list[Document],
        url: str,
        config: RunnableConfig,
    ) -> None:
        """Store documents in memory with chunking for RAG."""
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
            )

            memory_documents = []
            for doc_index, doc in enumerate(documents):
                # Split document content into chunks
                chunks = text_splitter.split_text(doc.page_content)

                for chunk_index, chunk in enumerate(chunks):
                    memory_metadata = {
                        "thread_id": config.get("configurable", {}).get("thread_id"),
                        "personality_id": config.get("configurable", {}).get(
                            "personality_id"
                        ),
                        "user_id": config.get("configurable", {}).get("user_id"),
                        "source": url,
                        "document_index": doc_index,
                        "chunk_index": chunk_index,
                        "total_chunks": len(chunks),
                        "access_count": 0,
                        "created_at": int(time.time()),
                        "stats": MemoryStats(
                            useful=0,
                            total=0,
                            last_useful_at=None,
                            last_recall_at=0,
                            scores=[],
                        ),
                    }

                    memory_doc = Document(
                        page_content=chunk,
                        id=str(uuid4()),
                        metadata=memory_metadata,
                    )
                    memory_documents.append(memory_doc)

            # Store all chunks in memory
            if memory_documents:
                await memories_store.aadd_documents(memory_documents)
                logger.debug(
                    f"Stored {len(memory_documents)} memory chunks from '{url}'"
                )
        except Exception as e:
            logger.error(f"Failed to store document in memory: {e}", exc_info=True)
            # Don't raise - memory storage failure shouldn't break document inspection


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import a website into the graph.")
    parser.add_argument(
        "--url",
        type=str,
        help="The url of the website to import.",
        default="https://www.firecrawl.dev/",
    )
    parser.add_argument(
        "--mode",
        type=str,
        help="The mode of the website import. Can be 'scrape' or 'crawl'.",
        default="scrape",
    )
    args = parser.parse_args()

    tool = InspectDocumentTool()
    results = tool._run(
        url=args.url,
        mode=args.mode,
    )
    print(results)
