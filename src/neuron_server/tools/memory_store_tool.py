import asyncio
import time
from uuid import uuid4

from langchain.tools import BaseTool
from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.tools.memory_recall_tool import MemoryStats
from neuron_server.vectorstores import memories_store


class MemoryStoreToolArgs(BaseModel):
    memory: str = Field(
        description=(
            "A detailed memory to save. Be specific. It will be used in a "
            "semantic text search and RAG. Do not use pronouns. Use proper nouns. "
            "Include all relevant details and references. The memory must be self "
            "contained. Provide quotes for any specific information."
        )
    )


class MemoryStoreTool(BaseTool):
    name: str = "store_memory"
    description: str = (
        "This tool allows you to save a memory for later retrieval. Use this when the "
        "user asks for you to remember something or you otherwise need to remember "
        "something novel."
    )

    args_schema: type[MemoryStoreToolArgs] = MemoryStoreToolArgs

    def _run(self, memory: str, config: RunnableConfig) -> str:
        return asyncio.run(self._arun(memory, config))

    async def _arun(
        self,
        memory: str,
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
                    last_recall_at=0,
                    scores=[],
                ),
            }
            document = Document(page_content=memory, id=str(uuid4()), metadata=metadata)
            await memories_store.aadd_documents([document])
            logger.debug("Saved memory: %s", memory)
            return "Memory saved"
        except Exception as e:
            logger.error(e, exc_info=True)
            raise
