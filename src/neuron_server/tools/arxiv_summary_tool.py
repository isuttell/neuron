from langchain.tools import BaseTool
from neuron_server.config import config as neuron_config
from neuron_server.logger import logger
import arxiv
import os
from neuron_server.util.pdf import summarize_pages, summarize_document
from langchain_anthropic import ChatAnthropic
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Type
import asyncio
from neuron_server.vectorstores import arxiv_store
import sys
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.runnables import RunnableConfig

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

model = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    temperature=0.3,
    max_tokens=4096,
)

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


class ArxivSummaryArgs(BaseModel):
    id: str = Field(description="The ID of the article to inspect.")
    force_resummarize: bool = Field(
        description="Whether to force the tool to re-summarize the article even if a cached version is available.",
        default=False,
    )


class ArxivSummaryTool(BaseTool):
    name: str = "arxiv_summary"
    description: str = (
        """
This tool provides detailed, page-by-page summaries of research articles by their arXiv short IDs. The initial run may take some time as it downloads and processes the article, and adds it to the vector store for RAG, but a cached summary is saved for faster access on future requests. Only use this tool if you can't answer the question based on the information you have as it is slower than other tools.
""".strip()
    )
    args_schema: Type[ArxivSummaryArgs] = ArxivSummaryArgs

    def _run(self, id: str, force_resummarize: bool = False) -> str:
        return asyncio.run(self._arun(id, force_resummarize))

    async def _arun(
        self,
        id: str,
        config: RunnableConfig,
        force_resummarize: bool = False,
    ) -> str:
        try:

            logger.debug(f"Searching arXiv with: id_list=[{id}]")
            # Construct the default API client.
            client = arxiv.Client()
            search = arxiv.Search(
                id_list=[id],
            )
            article = next(client.results(search), None)
            if not article:
                return "No article found"
            article_directory = (
                f"{neuron_config.static_folder}/arxiv/{article.get_short_id()}"
            )
            if not os.path.exists(article_directory):
                os.makedirs(article_directory)
            comment = article.comment.replace("\n", "<br />") if article.comment else ""
            summary = article.summary.replace("\n", "<br />") if article.summary else ""
            metadata = f"""
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

            pdf_filename = article._get_default_filename()
            pdf_full_path = f"{article_directory}/{pdf_filename}"
            if not os.path.exists(pdf_full_path):
                logger.debug(f"Downloading PDF for {article.title} to {pdf_full_path}")
                article.download_pdf(dirpath=article_directory, filename=pdf_filename)

            summary_file_path = os.path.join(
                article_directory, f"{article.get_short_id()}_summary.md"
            )

            if not force_resummarize and os.path.exists(summary_file_path):
                with open(summary_file_path, "r") as file:
                    return f"Summary already exists:\n{file.read()}"

            page_summaries, documents = await summarize_pages(
                model=model,
                pdf_path=pdf_full_path,
                metadata={
                    "title": article.title,
                    "short_id": article.get_short_id(),
                    "entry_id": article.entry_id,
                    "authors": [author.name for author in article.authors],
                    "published": article.published.astimezone().isoformat(),
                    "primary_category": article.primary_category,
                    "categories": article.categories,
                },
                config=config,
            )
            summary = await summarize_document(
                model=model, metadata=metadata, summaries=page_summaries, config=config
            )
            if len(documents) > 0:
                await arxiv_store.aadd_documents(documents)
            page_summaries = "\n\n".join(
                f"# Page {i+1} AI Summary\n\n{result}"
                for i, result in enumerate(page_summaries)
            )
            report = f"# {article.title}\n\nGenerated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n## arxiv metadata\n\n{metadata}\n\n## AI Summary:\n{summary}\n\n{page_summaries}"
            with open(summary_file_path, "w", encoding="utf-8") as file:
                file.write(report)
            logger.debug(f"Summary saved to {summary_file_path}")
            return report
        except Exception as e:
            logger.exception(e)
            return f"Failed to summarize article: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Search arXiv for research articles.")
    parser.add_argument(
        "--id",
        type=str,
        help="The ID of the article to inspect.",
        default="2412.04315v2",
    )
    args = parser.parse_args()

    tool = ArxivSummaryTool()
    results = tool._run(
        id=args.id,
    )
    print(results)
