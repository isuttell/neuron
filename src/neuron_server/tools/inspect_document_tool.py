from langchain.tools import BaseTool
from neuron_server.logger import logger
from pydantic import BaseModel, Field
from typing import Type, Literal, Optional, Dict, Any
import asyncio
from langchain_core.runnables import RunnableConfig
from neuron_server.graph import encode_md5
import os
import time
from neuron_server.config import config as neuron_config
import aiohttp
from langchain_community.document_loaders import FireCrawlLoader
import pymupdf4llm
from langchain_core.documents import Document
import json
from neuron_server.cache import cache_response
from typing import List


async def load_pdf_from_url(
    url: str, metadata: Optional[Dict[str, Any]] = None
) -> Document:
    temp_file = os.path.abspath(
        os.path.join(neuron_config.temp_folder, f"{encode_md5(url)}.pdf")
    )
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                with open(temp_file, "wb") as f:
                    while True:
                        chunk = await response.content.read(1024)
                        if not chunk:
                            break
                        f.write(chunk)
        text = pymupdf4llm.to_markdown(temp_file, show_progress=True)
        return Document(
            page_content=text,
            metadata={
                "title": url.rsplit("/", 1)[-1],
                "sourceURL": url,
                **(metadata or {}),
            },
        )
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


async def load_text_from_url(
    url: str, metadata: Optional[Dict[str, Any]] = None
) -> Document:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            text = await response.text()
            return Document(
                page_content=text,
                metadata={
                    "title": url.rsplit("/", 1)[-1],
                    "sourceURL": url,
                    **(metadata or {}),
                },
            )


@cache_response(ttl=60 * 60 * 3)
async def load_document_from_url(
    url: str,
    metadata: Optional[Dict[str, Any]] = None,
    mode: Literal["scrape", "crawl"] = "scrape",
) -> List[Document]:
    metadata = {"updated_at": int(time.time()), **(metadata or {})}
    if (
        url.endswith(".txt")
        or url.endswith(".md")
        or url.endswith(".csv")
        or url.endswith(".srt")
        or url.endswith(".vtt")
    ):
        doc = await load_text_from_url(
            url, metadata={"extension": url.rsplit(".")[-1], **metadata}
        )
        return [doc]
    elif url.endswith(".pdf"):
        doc = await load_pdf_from_url(url, metadata={"extension": "pdf", **metadata})
        return [doc]
    else:
        if "zaks.io" in url or "192.168" in url:
            raise DocumentInspectToolFailed(
                "FireCrawl cannot access urls on the local network."
            )

        loader = FireCrawlLoader(
            api_key=neuron_config.firecrawl_api_key, url=url, mode=mode
        )
        docs = await loader.aload()
        for doc in docs:
            doc.metadata["updated_at"] = int(time.time())
        return docs


class DocumentInspectToolFailed(Exception):
    pass


class DocumentInspectToolArgs(BaseModel):
    url: str = Field(
        description="The url of the document or website to inspect. Supports html websites, text files, pdfs, csvs, and markdown documents"
    )
    mode: Optional[Literal["scrape", "crawl"]] = Field(
        "scrape",
        description="The mode of the website import. Can be 'scrape' or 'crawl'. Scrape is for a single url and Crawl is for the url and all accessible sub pages. Ignored when importing documents",
    )
    add_facts_to_store: bool = Field(
        False,
        description="If True, the document's atomic facts will be extracted and added to the document store. This is useful for long term memory.",
    )


class DocumentInspectTool(BaseTool):
    name: str = "document_inspect"
    description: str = (
        """
This tool downloads documents, or scrapes a website using Firecrawl, and returns its raw text. Use this to answer questions about a website or document.

Supported document types:
txt
md
csv
srt
vtt
pdf
""".strip()
    )
    args_schema: Type[DocumentInspectToolArgs] = DocumentInspectToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        url: str,
        config: RunnableConfig,
        mode: str = "scrape",
    ) -> str:
        try:
            # Record the start time for performance measurement
            start_time = time.perf_counter()

            docs = await load_document_from_url(
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
            if len(docs) == 0:
                raise DocumentInspectToolFailed("No documents found")
            results = []
            for index, doc in enumerate(docs):
                results.append(
                    f"""\
    <document index="{index}">
        <source>{doc.metadata.get("source", url)}</source>
        <document_content>{doc.page_content}</document_content>
        <document_metadata>{json.dumps(doc.metadata or {})}</document_metadata>
    </document>
"""
                )
            duration = time.perf_counter() - start_time
            logger.debug(f"Processed '{url}' - {duration:.2f}s")
            docs = "\n\n".join(results)
            return f"<documents>\n{docs}\n</documents>"
        except Exception as e:
            logger.exception(e)
            raise e


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

    tool = DocumentInspectTool()
    results = tool._run(
        url=args.url,
        mode=args.mode,
    )
    print(results)
