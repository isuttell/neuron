from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
from neuron_server.vectorstores import memories_store
from langchain_core.runnables import RunnableConfig
from langchain_core.documents import Document
from typing import List
from datetime import datetime
import math


def format_memory(document: Document) -> str:
    created_at: datetime | None = (
        datetime.fromtimestamp(document.metadata.get("created_at", None)).astimezone()
        if document.metadata.get("created_at", None)
        else None
    )
    return f"""
{document.page_content}
Relevance Score: {document.metadata.get("score", 0)}%
Recorded: {created_at.isoformat(timespec='seconds') if created_at else 'Unknown'}
""".strip()


def log_decay(target_date: datetime, half_life: int = 7) -> float:
    """
    Calculate a logarithmic decay value for a datetime.

    Parameters:
        target_date (datetime): The date to evaluate.
        half_life (int): The number of days where the decay reduces by half.

    Returns:
        float: Decay value (1 for recent dates, decays after `half_life` days).
    """

    reference_date = datetime.now().astimezone()

    # Calculate days difference
    days_diff = (reference_date - target_date).total_seconds() / (24 * 3600)

    # Ensure the value doesn't go below 0
    days_diff = max(0, days_diff)

    # Logarithmic decay function
    decay = 1 / (1 + math.log(1 + days_diff / half_life))

    return decay


def calculate_score(document: Document, relevance_score: float) -> int:
    created_at: datetime | None = (
        datetime.fromtimestamp(document.metadata.get("created_at", None)).astimezone()
        if document.metadata.get("created_at", None)
        else None
    )

    time_decay: float = (log_decay(created_at) * 0.75) if created_at else 0.0
    score = relevance_score * time_decay
    return round(score * 100)


class MemoryRecallToolArgs(BaseModel):
    query: str = Field(description="The query to search for in the memories")
    k: int = Field(description="The number of memories to recall", default=3, min=3)
    score_threshold: float = Field(
        description="The score threshold for the memories to recall.A higher threshold (e.g., 0.7) increases precision but reduces recall, while a lower threshold (e.g., 0.3) increases recall but lowers precision. 0.2 is a good default.",
        default=0.2,
        gte=0.0,
        le=1.0,
    )


class MemoryRecallTool(BaseTool):
    name: str = "recall_memory"
    description: str = (
        "This tool allows you to recall information from long term memory. Use this if you are looking for a specific memory."
    )

    args_schema: Type[MemoryRecallToolArgs] = MemoryRecallToolArgs

    def _run(
        self,
        query: str,
        config: RunnableConfig,
        k: int = 3,
        score_threshold: float = 0.2,
    ):
        return asyncio.run(self._arun(query, config, k, score_threshold))

    async def _arun(
        self,
        query: str,
        config: RunnableConfig,
        k: int = 3,
        score_threshold: float = 0.2,
    ) -> str:
        assert "personality_id" in config["configurable"]
        doc_scores = await memories_store.asimilarity_search_with_relevance_scores(
            query,
            k=k,
            filter={"personality_id": config["configurable"]["personality_id"]},
            score_threshold=score_threshold,
        )
        if len(doc_scores) == 0:
            return "No memories found"
        results: List[Document] = []
        for doc, score in doc_scores:
            doc.metadata["score"] = calculate_score(doc, score)
            results.append(doc)
        results.sort(key=lambda doc: doc.metadata.get("score"), reverse=True)
        response = "\n--------\n".join([format_memory(doc) for doc in results])
        return response
