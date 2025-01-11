from langchain.tools import BaseTool
from neuron_server.logger import logger
from pydantic import BaseModel, Field
from typing import Type, Optional
import asyncio
from langchain_core.runnables import RunnableConfig
from neuron_server.graph import process_document, get_document
import arxiv
import os
import time
from werkzeug.exceptions import BadRequest
import pymupdf4llm
from neuron_server.config import config as neuron_config
import tiktoken

encoder = tiktoken.encoding_for_model("gpt-4o")


def format_arxiv_summary(article: arxiv.Result) -> str:
    comment = article.comment.replace("\n", "<br />") if article.comment else ""
    summary = article.summary.replace("\n", "<br />") if article.summary else ""
    return f"""
| Field              | Description |
|--------------------|-|
| Title              | {article.title} |
| Short ID           | {article.get_short_id()} |
| Link               | {article.entry_id} |
| Authors            | {", ".join([author.name for author in article.authors])} |
| Published          | {article.published} |
| Primary Category   | {article.primary_category} |
| Categories         | {", ".join(article.categories)} |
| Comment            | {comment} |
| Links              | {", ".join([link.href for link in article.links])} |
| arxiv Summary      | {summary} |
""".strip()


class GraphArxivImportToolArgs(BaseModel):
    arxiv_id: str = Field(description="The arxiv id of the article to import.")


class GraphArxivImportTool(BaseTool):
    name: str = "arxiv_graph_import"
    description: str = (
        """
Use this tool to import arXiv articles into the knowledge graph or check if an article already exists. It will return basic metadata about the article and the time it took to process. Be aware that this is a can be a slow process depending on the size of the article. Always confirm with the user before running this tool.
""".strip()
    )
    args_schema: Type[GraphArxivImportToolArgs] = GraphArxivImportToolArgs

    def _run(self, arxiv_id: str, config: RunnableConfig) -> str:
        return asyncio.run(self._arun(arxiv_id, config))

    async def _arun(
        self,
        arxiv_id: str,
        config: RunnableConfig,
    ) -> str:
        try:
            personality_id = config["configurable"].get("personality_id")
            # Record the start time for performance measurement
            start_time = time.perf_counter()
            logger.debug(f"Searching arXiv with: id_list=[{arxiv_id}]")

            # Construct the default API client for arXiv
            client = arxiv.Client()
            search = arxiv.Search(
                id_list=[arxiv_id],
            )

            # Retrieve the article based on the search
            article = next(client.results(search), None)
            if not article:
                # Raise an error if no article is found
                raise BadRequest("No article found")

            # Define the directory to store the article
            article_directory = os.path.abspath(
                os.path.join(
                    neuron_config.static_folder, "arxiv", article.get_short_id()
                )
            )
            # Create the directory if it does not exist
            if not os.path.exists(article_directory):
                os.makedirs(article_directory)

            # Get the default filename for the PDF
            pdf_filename = article._get_default_filename()
            pdf_full_path = os.path.abspath(
                os.path.join(article_directory, pdf_filename)
            )

            # Download the PDF if it does not already exist
            if not os.path.exists(pdf_full_path):
                logger.debug(f"Downloading PDF for {article.title} to {pdf_full_path}")
                article.download_pdf(dirpath=article_directory, filename=pdf_filename)

            # Create a unique document ID for the article
            document_id = f"arxiv:{article.get_short_id()}"

            # Check if the document already exists in the graph
            document = get_document(document_id, personality_id=personality_id)
            if document:
                return f"""
{format_arxiv_summary(article)}

Article {document_id} already exists in knowledge graph. Skipping import.
"""

            # Log the processing of the article
            logger.debug(f"Processing {article.title} from {pdf_full_path}")
            # Convert the PDF to markdown text
            text = pymupdf4llm.to_markdown(pdf_full_path, show_progress=True)
            # Process the document and add it to the graph
            doc_result = await process_document(
                text=text,
                document_id=document_id,
                document_name=article.title,
                source=article.entry_id,
                config=config,
            )
            token_count = len(encoder.encode(text))

            duration = time.perf_counter() - start_time
            logger.debug(f"Processed '{article.title}' in {duration:.2f} seconds")
            keywords = ", ".join(doc_result.keywords)
            return f"""
# Graph Import Result

Added '{article.title}' to knowledge graph in {round(duration)} seconds

## Arxiv Metadata

{format_arxiv_summary(article)}

## Document {doc_result.document_id}

* **Name:** {doc_result.document_name or 'unknown'}
* **Source:** {doc_result.source or 'unknown'}
* **Keywords:** {keywords or 'None'}
* **Tokens:** {token_count:,}

### Summary

{doc_result.summary}

### Analysis

{doc_result.analysis}
"""
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Failed to add article to knowledge graph: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Import an arxiv article into the graph."
    )
    parser.add_argument(
        "--arxiv_id",
        type=str,
        help="The arxiv id of the article to import.",
        default="2412.14455",
    )
    args = parser.parse_args()

    tool = GraphArxivImportTool()
    results = tool._run(
        arxiv_id=args.arxiv_id,
    )
    print(results)
