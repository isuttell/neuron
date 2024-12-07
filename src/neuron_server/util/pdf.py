import pymupdf4llm
from langchain_core.documents import Document
from langchain_text_splitters.character import RecursiveCharacterTextSplitter
from langchain_text_splitters.markdown import MarkdownTextSplitter
from typing import List, Dict, Any, Optional
from neuron_server.llms.llm import LLM
from neuron_server.llms.prompts import (
    document_summarize_page_prompt,
    document_summarize_prompt,
)
from langchain_core.messages import AIMessage
from neuron_server.logger import logger
import re
from langchain_core.runnables import Runnable

markdown_splitter = MarkdownTextSplitter(chunk_size=1000, chunk_overlap=200)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


def convert_to_documents(
    pdf_path: str, metadata: Optional[Dict[str, Any]] = None
) -> List[Document]:
    markdown_text = pymupdf4llm.to_markdown(pdf_path, show_progress=False)
    return markdown_splitter.create_documents(
        [markdown_text], metadatas=[metadata or {}]
    )


async def summarize_pages(model: Runnable, pdf_path: str) -> List[str]:
    pages = pymupdf4llm.to_markdown(pdf_path, page_chunks=True)
    chain = document_summarize_page_prompt | model
    last_page: Optional[str] = None
    logger.debug(f"Summarizing {len(pages)} pages in {pdf_path}...")
    # iterate over each page adding to the summary
    results: List[str] = []
    for i, page in enumerate(pages):
        message: AIMessage = await chain.ainvoke(
            {
                "last_page": last_page or "",
                "page": page,
                "page_number": i + 1,
                "total_pages": len(pages),
            },
            {"run_name": "summarize_pages"},
        )
        summary = re.sub(r"```(?:\w+)?\s*|\s*```", "", message.content.strip()).strip()
        results.append(summary)
        last_page = summary
        logger.debug(f"Summarized page {i} of {len(pages)}")
    if not results:
        raise ValueError("Failed to summarize document")
    return results


async def summarize_document(
    model: Runnable, metadata: str, summaries: List[str]
) -> str:
    chain = document_summarize_prompt | model
    message: AIMessage = await chain.ainvoke(
        {
            "pages": [
                f"Page {i+1} Summary:\n{summary}\n\n---\n\n"
                for i, summary in enumerate(summaries)
            ],
            "metadata": metadata,
        },
        {"run_name": "summarize_document"},
    )
    return re.sub(r"```(?:\w+)?\s*|\s*```", "", message.content.strip()).strip()
