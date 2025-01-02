from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
from neuron_server.vectorstores import memories_store
from langchain_core.runnables import RunnableConfig
from langchain_core.documents import Document
from typing import List, TypedDict
from datetime import datetime, timezone
import math


def format_memory(document: Document) -> str:
    created_at: datetime | None = (
        datetime.fromtimestamp(document.metadata.get("created_at", None)).astimezone()
        if document.metadata.get("created_at", None)
        else None
    )
    return f"""
Document ID: {document.id}
Relevance Score: {document.metadata.get("score", 0)}%
Recorded: {created_at.isoformat(timespec='seconds') if created_at else 'Unknown'}

{document.page_content}
""".strip()


def decay_date(target_date: datetime, half_life: int = 7) -> float:
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


class MemoryStats(TypedDict):
    useful: int
    total: int
    last_useful_at: int | None
    last_recall_at: int
    scores: List[float]


def calculate_score(document: Document, relevance_score: float) -> int:
    created_at: datetime | None = (
        datetime.fromtimestamp(document.metadata.get("created_at", None)).astimezone()
        if document.metadata.get("created_at", None)
        else None
    )
    stats: MemoryStats = document.metadata.get(
        "stats",
        {
            "useful": 0,
            "total": 1,
            "last_useful_at": None,
            "last_recall_at": int(datetime.now(timezone.utc).timestamp()),
            "scores": [],
        },
    )
    last_useful_at: datetime | None = (
        datetime.fromtimestamp(stats["last_useful_at"]).astimezone()
        if stats["last_useful_at"]
        else None
    )
    last_recall_at: datetime | None = (
        datetime.fromtimestamp(stats["last_recall_at"]).astimezone()
        if stats["last_recall_at"]
        else None
    )
    usefulness_score: float = (
        stats["useful"] / stats["total"] if stats["total"] > 1 else 1.0
    )
    last_useful_score: float = (decay_date(last_useful_at, 30)) if last_useful_at else 0
    last_recall_at_score: float = (
        (decay_date(last_recall_at, 14)) if last_recall_at else 1.0
    )
    created_at_score: float = (decay_date(created_at, 14)) if created_at else 0
    weights_scores = [
        (relevance_score, 0.4),
        (usefulness_score, 0.2),
        (last_useful_score, 0.2),
        (last_recall_at_score, 0.1),
        (created_at_score, 0.1),
    ]
    score = sum(w * s for w, s in weights_scores)
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
    filter_by_thread: bool = Field(
        description="If True, the memories will be filtered by the current thread.",
        default=False,
    )


NO_MEMORIES_FOUND = "No memories found"


class MemoryRecallTool(BaseTool):
    name: str = "recall_memory"
    description: str = (
        "This tool allows you to recall information from long term memory. Use this if you are looking for a specific memory or need a wide range of memories and the answer is not in the current recall memories."
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
        filter_by_thread: bool = False,
    ) -> str:
        assert "personality_id" in config["configurable"]
        # Always filter by personality
        doc_filter = {"personality_id": config["configurable"]["personality_id"]}

        # Filter by thread if specified
        if filter_by_thread:
            doc_filter["thread_id"] = config["configurable"]["thread_id"]

        doc_scores = await memories_store.asimilarity_search_with_relevance_scores(
            query,
            k=k,
            filter=doc_filter,
            score_threshold=score_threshold,
        )
        if len(doc_scores) == 0:
            return NO_MEMORIES_FOUND
        results: List[Document] = []
        for doc, score in doc_scores:
            doc.metadata["score"] = round(score * 100)  # calculate_score(doc, score)
            results.append(doc)

        # Filter out memories that don't meet the score threshold after calculating
        # the combined score
        results = list(
            filter(
                lambda doc: doc.metadata.get("score") >= score_threshold * 100, results
            )
        )
        if len(results) == 0:
            return "No memories found"
        results.sort(key=lambda doc: doc.metadata.get("score"), reverse=True)
        response = "\n--------\n".join([format_memory(doc) for doc in results])
        return response
