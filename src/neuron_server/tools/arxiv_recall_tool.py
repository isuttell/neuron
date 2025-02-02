import asyncio
from datetime import datetime

from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.vectorstores import arxiv_store


def format_document(document: Document, score: float) -> str:
    title: str = document.metadata.get("title")
    published: datetime = datetime.fromisoformat(
        document.metadata.get("published")
    ).astimezone()
    entry_id: str = document.metadata.get("entry_id")
    short_id: str = document.metadata.get("short_id")
    page: int = document.metadata.get("page")
    page_count: int = document.metadata.get("page_count")
    content: str = document.page_content.replace("\n", "<br />")
    return f"""
| Key         | Value   |
|-------------|---------|
| Short Id    | {short_id} |
| Title       | {title} |
| Publication | arxiv   |
| Link        | {entry_id} |
| Published   | {published.isoformat(timespec="minutes")} |
| Page        | {page} / {page_count} |
| Relevance   | {round(score * 100)}% |
| Excerpt     | {content} |
""".strip()


class ArxivRecallToolArgs(BaseModel):
    query: str = Field(
        description="The semantic text query to search for in the arxiv memories"
    )
    k: int = Field(description="The number of documents to recall", default=10, ge=3)
    score_threshold: float = Field(
        description="The minimum score to recall a document",
        default=0.2,
        ge=0.0,
        le=1.0,
    )
    filter_short_id: str | None = Field(
        description=(
            "The optional short id of the document to filter by. "
            "Use to ask questions from a specific paper."
        ),
        default=None,
    )


class ArxivRecallTool(BaseTool):
    name: str = "arxiv_recall"
    description: str = (
        "This tool allows you to recall information from long term memory "
        "of arxiv papers that have been summarized. Use this to ask specific "
        "questions about a paper."
    )

    args_schema: type[ArxivRecallToolArgs] = ArxivRecallToolArgs

    def _run(self, query: str, config: RunnableConfig, k: int = 10) -> str:
        return asyncio.run(self._arun(query, config, k))

    async def _arun(
        self,
        query: str,
        k: int = 10,
        score_threshold: float = 0.2,
        filter_short_id: str = None,
    ) -> str:
        try:
            logger.debug(f"Searching arxiv memories for query: {query} with k={k}")
            filter_dict = {"short_id": filter_short_id} if filter_short_id else None
            docs_scores = await arxiv_store.asimilarity_search_with_relevance_scores(
                query,
                k=k,
                score_threshold=score_threshold,
                filter=filter_dict,
            )
            if len(docs_scores) == 0:
                return "No documents found"
            return "\n\n--------\n\n".join(
                [format_document(doc, score) for doc, score in docs_scores]
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error searching arxiv memories: {str(e)}"
