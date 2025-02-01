import asyncio
from typing import Any

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.models.thread_model import ThreadModel


class SetThreadMemoryToolArgs(BaseModel):
    memory: str = Field(
        description=(
            "The full and complete memory to overwrite the existing thread memory. "
            "Do not paraphrase the memory."
        )
    )


class SetThreadMemoryTool(BaseTool):
    name: str = "set_thread_memory"
    description: str = (
        "This tool allows you to update the memory of the current thread. Use this "
        "to store plans and other custom instructions that you do not want to get "
        "lost. For example, on a complicated task you might put together a rational "
        "plan to solve it, store it using this tool and then it will be included "
        "in future requests to guide the agent."
    )

    args_schema: type[SetThreadMemoryToolArgs] = SetThreadMemoryToolArgs

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        memory: str,
        config: RunnableConfig,
    ) -> str:
        try:
            thread_id = config["configurable"].get("thread_id")
            if thread_id is None:
                raise ValueError("Thread ID is required but was not provided")
            await ThreadModel.set(thread_id, "memory", memory)
            return "Successfully updated thread memory"
        except Exception as e:
            logger.error("Failed to update thread memory: %s", str(e), exc_info=True)
            raise RuntimeError("Failed to update thread memory") from e
