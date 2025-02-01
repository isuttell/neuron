import asyncio
import json
import os
import time
from datetime import datetime
from typing import Any, Literal

import aiohttp
import pymupdf4llm
from langchain.tools import BaseTool
from langchain_community.document_loaders import FireCrawlLoader
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.config import config as neuron_config
from neuron_server.graph import encode_md5
from neuron_server.logger import logger


async def load_pdf_from_url(
    url: str, metadata: dict[str, Any] | None = None
) -> Document:
    temp_file = os.path.abspath(
        os.path.join(neuron_config.temp_folder, f"{encode_md5(url)}.pdf")
    )
    try:
        async with aiohttp.ClientSession() as session, session.get(url) as response:
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
    url: str, metadata: dict[str, Any] | None = None
) -> Document:
    async with aiohttp.ClientSession() as session, session.get(url) as response:
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


class InspectDocumentToolError(Exception):
    pass


@cache_response(ttl=60 * 60 * 3)
async def load_document_from_url(
    url: str,
    metadata: dict[str, Any] | None = None,
    mode: Literal["scrape", "crawl"] = "scrape",
) -> list[Document]:
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
    if url.endswith(".pdf"):
        doc = await load_pdf_from_url(url, metadata={"extension": "pdf", **metadata})
        return [doc]
    if "zaks.io" in url or "192.168" in url:
        raise InspectDocumentToolError(
            "FireCrawl cannot access urls on the local network."
        )

    loader = FireCrawlLoader(
        api_key=neuron_config.firecrawl_api_key, url=url, mode=mode
    )
    docs = await loader.aload()
    for doc in docs:
        doc.metadata["updated_at"] = int(time.time())
    return docs


class InspectDocumentToolArgs(BaseModel):
    url: str = Field(
        description=(
            "The url of the document or website to inspect. Supports html websites, "
            "text files, pdfs, csvs, and markdown documents"
        )
    )
    mode: Literal["scrape", "crawl"] | None = Field(
        "scrape",
        description=(
            "The mode of the website import. Can be 'scrape' or 'crawl'. Scrape is "
            "for a single url and Crawl is for the url and all accessible sub pages. "
            "Ignored when importing documents"
        ),
    )
    add_facts_to_store: bool | None = Field(
        False,
        description=(
            "If True, the document's atomic facts will be extracted and added to the "
            "document store. This is useful for long term memory."
        ),
    )
    summarize_prompt: str | None = Field(
        None,
        description=(
            "If provided, the prompt will be used to summarize the document instead of "
            "returning the raw text. Use this to extract specific information from the "
            "document and reduce the amount of information returned. It should be in "
            "second person and be a detailed step by step guide to follow. It should "
            "include how detailed of an analysis to perform. Include relevant context "
            "to aid the analysis."
        ),
    )


document_inspect_prompt = PromptTemplate(
    template="""
You are an intelligent assistant and will be given a text document and a prompt. Your
job is to comprehensively summarize the document in a way that is useful for answering
the prompt. Be as long and detailed as needed. Accuracy is important. Include quotes
and markdown links to sources. Use markdown to format the output.

Now: {now}

Document Metadata:
\"\"\"
{metadata}
\"\"\"

Document ({index}):
\"\"\"
{document}
\"\"\"

Prompt:
\"\"\"
{prompt}
\"\"\"
""".strip(),
    input_variables=["prompt", "document", "index", "now", "metadata"],
)


class InspectDocumentTool(BaseTool):
    name: str = "document_inspect"
    description: str = """
This tool downloads documents, or scrapes a website using Firecrawl, and returns its
raw text. Use this to answer questions about a website or document.

Supported document types:
txt
md
csv
srt
vtt
pdf
""".strip()
    args_schema: type[InspectDocumentToolArgs] = InspectDocumentToolArgs

    def _run(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        url: str,
        config: RunnableConfig,
        mode: str = "scrape",
        summarize_prompt: str | None = None,
    ) -> str:
        try:
            # Record the start time for performance measurement
            start_time = time.perf_counter()
            logger.debug(f"Processing '{url}' with prompt: {summarize_prompt}")

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
                raise InspectDocumentToolError("No documents found")

            from neuron_server.models.provider_model import ProviderModelModel

            # Inspect the image
            llm = await ProviderModelModel.get_active_llm()
            chain = document_inspect_prompt | llm.model | StrOutputParser()

            results = []
            tasks = []
            for index, doc in enumerate(docs):
                if summarize_prompt:
                    tasks.append(
                        chain.ainvoke(
                            {
                                "prompt": summarize_prompt,
                                "document": doc.page_content,
                                "index": f"{index}/{len(docs)}",
                                "now": datetime.now()
                                .astimezone()
                                .isoformat(timespec="seconds"),
                                "metadata": json.dumps(doc.metadata or {}, indent=2),
                            }
                        )
                    )
                else:
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

            summaries: list[str] = await asyncio.gather(*tasks)
            for index, summary in enumerate(summaries):
                metadata_str = json.dumps(doc.metadata or {}, indent=2)
                results.append(
                    f"""\
    <document index="{index}">
        <source>{doc.metadata.get("source", url)}</source>
        <document_summary>{summary.strip()}</document_summary>
        <document_metadata>{metadata_str}</document_metadata>
    </document>
"""
                )
            duration = time.perf_counter() - start_time
            logger.debug(f"Processed '{url}' - {duration:.2f}s")
            docs = "\n\n".join(results)
            return f"<documents>\n{docs}\n</documents>"

        except Exception as e:
            logger.error(e, exc_info=True)
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

    tool = InspectDocumentTool()
    results = tool._run(
        url=args.url,
        mode=args.mode,
    )
    print(results)
