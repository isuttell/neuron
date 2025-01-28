import os
import re
from typing import Any

import pymupdf4llm
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_text_splitters.markdown import MarkdownTextSplitter

from neuron_server.llms.prompts import (
    document_summarize_page_prompt,
    document_summarize_prompt,
)
from neuron_server.logger import logger

markdown_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


def convert_to_documents(
    pdf_path: str, metadata: dict[str, Any] | None = None
) -> list[Document]:
    markdown_text = pymupdf4llm.to_markdown(pdf_path, show_progress=False)
    return markdown_splitter.create_documents(
        [markdown_text], metadatas=[metadata or {}]
    )


async def summarize_pages(
    model: Runnable,
    pdf_path: str,
    metadata: dict[str, Any] | None = None,
    config: RunnableConfig = None,
) -> tuple[list[str], list[Document]]:
    filename = os.path.basename(pdf_path)
    pages = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
    chain = document_summarize_page_prompt | model | StrOutputParser()
    last_page: str | None = None
    texts: list[str] = [page["text"] for page in pages]
    metadatas: list[dict[str, Any]] = [
        {
            "page": page["metadata"]["page"],
            "page_count": page["metadata"]["page_count"],
            "title": page["metadata"]["title"],
            "author": page["metadata"]["author"],
            "filename": filename,
            **(metadata or {}),
        }
        for page in pages
    ]
    # Split the pages into documents foir RAG
    documents = markdown_splitter.create_documents(
        texts,
        metadatas=metadatas,
    )

    logger.debug(f"Summarizing {len(pages)} pages in {filename}...")
    # iterate over each page adding to the summary
    results: list[str] = []
    for i, page in enumerate(pages):
        content: str = await chain.ainvoke(
            {
                "last_page": last_page or "",
                "page": page,
                "page_number": i + 1,
                "total_pages": len(pages),
            },
            {**(config or {}), "run_name": "summarize_pages"},
        )
        summary = re.sub(r"```(?:\w+)?\s*|\s*```", "", content.strip()).strip()
        results.append(summary)
        last_page = summary
        logger.debug(
            f"Summarized page {i+1} of {len(pages)} in {os.path.basename(pdf_path)}"
        )
    if not results:
        raise ValueError("Failed to summarize document")
    return results, documents


async def summarize_document(
    model: Runnable, metadata: str, summaries: list[str], config: RunnableConfig = None
) -> str:
    chain = document_summarize_prompt | model | StrOutputParser()
    content: str = await chain.ainvoke(
        {
            "pages": "\n\n".join(
                [
                    f'Page {i+1} Summary\n"""\n{summary}\n"""'
                    for i, summary in enumerate(summaries)
                ]
            ),
            "metadata": metadata,
        },
        {**(config or {}), "run_name": "summarize_document"},
    )
    return re.sub(r"```(?:\w+)?\s*|\s*```", "", content.strip()).strip()
