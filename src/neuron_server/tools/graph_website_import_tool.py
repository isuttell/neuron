import asyncio
import time
from typing import Literal

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.graph import encode_md5
from neuron_server.graph.document import DocumentMetadata, process_document
from neuron_server.logger import logger
from neuron_server.tools.document_utils import (
    DocumentLoadError,
    count_tokens,
    load_document_from_url,
)


class GraphWebsiteImportToolArgs(BaseModel):
    url: str = Field(
        description="The url of the document or website to import. "
        "Supports html websites, text files, pdfs, csvs, markdown documents, "
        "and YouTube video transcripts"
    )
    mode: Literal["scrape", "crawl"] | None = Field(
        "scrape",
        description="The mode of the website import. Can be 'scrape' or 'crawl'. "
        "Scrape is for a single url and Crawl is for the url and all accessible "
        "sub pages. Only used when importing websites.",
    )


class GraphWebsiteImportTool(BaseTool):
    name: str = "graph_website_import"
    description: str = """
This tool imports documents, or scrapes a website using Firecrawl, and adds it to
the knowledge graph. Use this save information from the internet for later use or
when the user asks you to save/import a website/pdf url. Supports YouTube video
transcripts, PDFs, text files, markdown, CSV, SRT, VTT, and web pages.
""".strip()
    args_schema: type[GraphWebsiteImportToolArgs] = GraphWebsiteImportToolArgs

    def _run(self, url: str, config: RunnableConfig, mode: str = "scrape") -> str:
        return asyncio.run(self._arun(url, config, mode))

    async def _arun(
        self,
        url: str,
        config: RunnableConfig,
        mode: str = "scrape",
    ) -> str:
        try:
            logger.debug(f"Importing website '{url}'")
            personality_id = config["configurable"].get("personality_id")
            assert personality_id is not None
            # Record the start time for performance measurement
            start_time = time.perf_counter()

            docs = await load_document_from_url(
                url,
                metadata={"personality_id": personality_id},
                mode=mode,
            )

            if len(docs) == 0:
                raise DocumentLoadError("No documents found")

            # Process the documents and add them to the graph
            result = (
                f"# Knowledge Graph Import Results\n\n"
                f"Imported '{url}' to the knowledge graph in {len(docs)} document(s)"
            )
            for doc in docs:
                source = doc.metadata.get("sourceURL", doc.metadata.get("url", url))
                # Count tokens in the document
                token_count = count_tokens(doc.page_content)

                # Update the document id to be the source url
                # in case we're in crawl model
                document_id = f"website:{encode_md5(source)}"
                metadata = DocumentMetadata(
                    document_id=document_id,
                    document_name=doc.metadata.get("title", None),
                    source=source,
                    personality_id=personality_id,
                )
                doc_result = await process_document(
                    text=doc.page_content.strip(), config=config, metadata=metadata
                )
                keywords = ", ".join(doc_result.keywords)
                result += f"""\

## Document {doc_result.document_id}

* **Name:** {doc_result.document_name or "unknown"}
* **Source:** {doc_result.source or "unknown"}
* **Keywords:** {keywords or "None"}
* **Tokens:** {token_count:,}

### Summary

{doc_result.summary}

### Analysis

{doc_result.analysis}
"""
            duration = time.perf_counter() - start_time
            logger.debug(f"Processed '{url}' - {duration:.2f}s")
            return result.strip()
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

    tool = GraphWebsiteImportTool()
    results = tool._run(
        url=args.url,
        mode=args.mode,
    )
    print(results)
