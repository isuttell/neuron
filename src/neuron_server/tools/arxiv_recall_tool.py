from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
from neuron_server.vectorstores import arxiv_store
from langchain_core.runnables import RunnableConfig
from langchain_core.documents import Document
from typing import List
from datetime import datetime


def format_document(document: Document) -> str:
    title: str = document.metadata.get("title")
    published: datetime = datetime.fromisoformat(
        document.metadata.get("published")
    ).astimezone()
    entry_id: str = document.metadata.get("entry_id")
    page: int = document.metadata.get("page")
    page_count: int = document.metadata.get("page_count")
    authors: str = ", ".join(document.metadata.get("authors", []))
    content: str = document.page_content.replace("\n", "<br />")
    return f"""
| Title     | {title} |
|-----------|---------|
| Link      | {entry_id} |
| Published | {published.isoformat(timespec="seconds")} |
| Page      | {page} / {page_count} |
| Author(s) | {authors} |
| Content   | {content} |
""".strip()


class ArxivRecallToolArgs(BaseModel):
    query: str = Field(
        description="The semantic text query to search for in the arxiv memories"
    )
    k: int = Field(description="The number of documents to recall", default=3, min=3)


class ArxivRecallTool(BaseTool):
    name: str = "arxiv_recall"
    description: str = (
        "This tool allows you to recall information from long term memory of arxiv papers. Use this to recall information from arxiv papers."
    )

    args_schema: Type[ArxivRecallToolArgs] = ArxivRecallToolArgs

    def _run(self, query: str, config: RunnableConfig, k: int = 3):
        return asyncio.run(self._arun(query, config, k))

    async def _arun(
        self,
        query: str,
        k: int = 3,
    ) -> str:
        try:
            logger.debug(f"Searching arxiv memories for query: {query} with k={k}")
            documents = await arxiv_store.asimilarity_search(
                query,
                k=k,
            )
            if len(documents) == 0:
                return "No documents found"
            return "\n\n--------\n\n".join([format_document(doc) for doc in documents])
        except Exception as e:
            logger.exception(e)
            return f"Error searching arxiv memories: {str(e)}"
