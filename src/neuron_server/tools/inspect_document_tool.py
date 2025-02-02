import asyncio
import json
import time
from datetime import datetime
from typing import Any, Literal

from langchain.tools import BaseTool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.tools.document_utils import (
    DocumentLoadError as BaseDocumentError,
)
from neuron_server.tools.document_utils import (
    load_document_from_url,
)


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
    custom_instructions: str | None = Field(
        None,
        description=(
            "If provided, the custom instructions will be used to inspect the document "
            "returning the raw text. Use this to extract specific information from the "
            "document. Use this unless you need the raw text. It should be in "
            "second person and be a detailed step by step guide to follow. It should "
            "include how detailed of an analysis to perform. Include relevant context. "
            "It may include multiple questions or complicated plans to analyze the "
            "document."
        ),
    )


custom_instructions_prompt = PromptTemplate(
    template="""
You will be given a document, metadata, and custom instructions. Your
job is to follow the custom instructions as closely as possible whether that is
summarizing, answering questions, extracting information, etc. Be as long and detailed
as needed. Accuracy is important. Include related context and metadata like authors,
speakers, writers, etc. so that another agent can use this information to answer
questions. Include quotes from the document, links to sources using the sourceURL from
from the metadata, links to specific timestamps in youtube videos, etc.. Use markdown
to format the output.

Now: {now}

Document Metadata:
\"\"\"
{metadata}
\"\"\"

Document ({index}):
\"\"\"
{document}
\"\"\"

Custom Instructions:
\"\"\"
{custom_instructions}
\"\"\"
""".strip(),
    input_variables=[
        "custom_instructions",
        "document",
        "index",
        "now",
        "metadata",
    ],
)

custom_instructions_chain = (
    custom_instructions_prompt
    | ChatOpenAI(model="o3-mini-2025-01-31")
    | StrOutputParser()
)


class InspectDocumentTool(BaseTool):
    name: str = "document_inspect"
    description: str = """
This tool downloads documents, scapes websites, extracts transcripts from youtube
videos, and returns the raw text.

Use this to answer questions about a website or document.

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

    def _run(self, *args: tuple[Any, ...], **kwargs: dict[str, Any]) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        url: str,
        config: RunnableConfig,
        mode: str | None = None,
        custom_instructions: str | None = None,
    ) -> str:
        try:
            # Record the start time for performance measurement
            start_time = time.perf_counter()
            logger.debug(f"Processing '{url}' with instructions: {custom_instructions}")

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

            results = []
            tasks = []
            for index, doc in enumerate(docs):
                if custom_instructions:
                    tasks.append(
                        custom_instructions_chain.ainvoke(
                            {
                                "custom_instructions": custom_instructions,
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
