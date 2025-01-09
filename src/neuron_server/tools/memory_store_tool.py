from langchain.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
import time
from neuron_server.vectorstores import memories_store
from langchain_core.runnables import RunnableConfig
from langchain_core.documents import Document
from uuid import uuid4
from neuron_server.tools.memory_recall_tool import MemoryStats
from datetime import datetime, timezone


class MemoryStoreToolArgs(BaseModel):
    memories: List[str] = Field(
        description="A detailed list of memories to save. Be specific. It will be used for in a semantic text search and RAG. Do not use pronouns. Include all relevant details and references. Each memory must be self contained. Provide quotes for any specific information."
    )


class MemoryStoreTool(BaseTool):
    name: str = "store_memory"
    description: str = (
        "This tool allows you to save memories for later retrieval. Use this when the user asks for you to remember something or you otherwise need to remember something novel."
    )

    args_schema: Type[MemoryStoreToolArgs] = MemoryStoreToolArgs

    def _run(self, memories: List[str], config: RunnableConfig) -> str:
        return asyncio.run(self._arun(memories, config))

    async def _arun(
        self,
        memories: List[str],
        config: RunnableConfig,
    ) -> str:
        try:
            metadata = {
                "thread_id": config["configurable"].get("thread_id", None),
                "personality_id": config["configurable"].get("personality_id", None),
                "user_id": config["configurable"].get("user_id", None),
                "access_count": 0,
                "created_at": int(time.time()),
                "stats": MemoryStats(
                    useful=0,
                    total=0,
                    last_useful_at=None,
                    last_recall_at=None,
                    scores=[],
                ),
            }
            documents = [
                Document(page_content=memory, id=str(uuid4()), metadata=metadata)
                for memory in memories
            ]
            await memories_store.aadd_documents(documents)
            memories_str = "\n".join(
                [f"- {memory.page_content}" for memory in documents]
            )
            logger.debug(f"Saved memories:\n{memories_str}")
            return f"Memories saved"
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
