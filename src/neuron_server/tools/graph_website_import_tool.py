from langchain.tools import BaseTool
from neuron_server.logger import logger
from pydantic import BaseModel, Field
from typing import Type, Literal
import asyncio
from langchain_core.runnables import RunnableConfig
from neuron_server.graph import process_document, get_document, encode_md5
import os
import time
from neuron_server.config import config as neuron_config
import aiohttp
from langchain_community.document_loaders import FireCrawlLoader
import pymupdf4llm
from langchain_core.documents import Document


async def load_pdf_from_url(url: str) -> Document:
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
        return Document(page_content=text, metadata={"url": url})
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


class GraphWebsiteImportToolArgs(BaseModel):
    url: str = Field(description="The url of the website to import.")
    mode: Literal["scrape", "crawl"] = Field(
        "scrape",
        description="The mode of the website import. Can be 'scrape' or 'crawl'. Scrape is for a single url and Crawl is for the url and all accessible sub pages",
    )


class GraphWebsiteImportTool(BaseTool):
    name: str = "website_graph_import"
    description: str = (
        """
This tool scrapes a website using Firecrawl, converts it to markdown and adds it to the knowledge graph. Use this save information from the internet for later use or when the user asks you to save/import a website/pdf url.
""".strip()
    )
    args_schema: Type[GraphWebsiteImportToolArgs] = GraphWebsiteImportToolArgs

    def _run(self, url: str, config: RunnableConfig, mode: str = "scrape") -> str:
        return asyncio.run(self._arun(url, config, mode))

    async def _arun(
        self,
        url: str,
        config: RunnableConfig,
        mode: str = "scrape",
    ) -> str:
        try:
            personality_id = config["configurable"].get("personality_id")
            assert personality_id is not None
            # Record the start time for performance measurement
            start_time = time.perf_counter()

            # if url.endswith(".pdf"):
            #     doc = await load_pdf_from_url(url)
            #     docs = [doc]
            # else:
            loader = FireCrawlLoader(
                api_key=neuron_config.firecrawl_api_key, url=url, mode=mode
            )
            docs = await loader.aload()

            # Process the documents and add them to the graph
            for doc in docs:
                source = doc.metadata.get("sourceURL", doc.metadata.get("url", url))
                # Update the document id to be the source url
                # in case we're in crawl model
                document_id = f"website:{encode_md5(source)}"
                await process_document(
                    text=doc.page_content.strip(),
                    document_id=document_id,
                    document_name=doc.metadata.get("title", url),
                    source=source,
                    config=config,
                )
            duration = time.perf_counter() - start_time
            logger.debug(f"Processed '{url}' - {duration:.2f}s")
            return f"Added '{url}' to the knowledge graph - {duration:.2f}s"
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

    tool = GraphWebsiteImportTool()
    results = tool._run(
        url=args.url,
        mode=args.mode,
    )
    print(results)
