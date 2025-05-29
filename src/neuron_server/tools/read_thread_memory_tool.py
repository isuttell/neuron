import asyncio
from typing import Any

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from neuron_server.logger import logger
from neuron_server.models.thread_model import ThreadModel


class ReadThreadMemoryToolArgs(BaseModel):
    pass  # No arguments needed for reading


class ReadThreadMemoryTool(BaseTool):
    name: str = "read_thread_memory"
    description: str = (
        "Read the current planning board to check task progress, review plans, "
        "and see what tasks remain. Use this frequently during complex tasks to "
        "stay on track and ensure nothing is missed. Returns the full planning "
        "board content including task checklists and notes."
    )

    args_schema: type[ReadThreadMemoryToolArgs] = ReadThreadMemoryToolArgs

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        config: RunnableConfig,
    ) -> str:
        try:
            thread_id = config["configurable"].get("thread_id")
            if thread_id is None:
                raise ValueError("Thread ID is required but was not provided")

            thread = await ThreadModel.get(thread_id)
            if thread is None:
                raise ValueError(f"Thread {thread_id} not found")

            if not thread.memory:
                return (
                    "Planning board is empty. Use set_thread_memory to create "
                    "a task list."
                )

            return f"Current planning board:\n\n{thread.memory}"
        except Exception as e:
            logger.error("Failed to read thread memory: %s", str(e), exc_info=True)
            raise RuntimeError("Failed to read planning board") from e
