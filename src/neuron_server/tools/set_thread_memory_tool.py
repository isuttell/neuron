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
            "The planning board content including task lists, checklists, and notes. "
            "Format as markdown with checkboxes for tasks (e.g., '- [ ] Task to do' "
            "or '- [x] Completed task'). This completely overwrites the existing "
            "planning board. Include ALL tasks and notes, not just updates."
        )
    )


class SetThreadMemoryTool(BaseTool):
    name: str = "set_thread_memory"
    description: str = (
        "A planning board for complex tasks. Use this to maintain task checklists, "
        "plans, and progress tracking. Store tasks as markdown checkboxes that can be "
        "checked off as completed. This is essential for complicated multi-step tasks "
        "to ensure nothing is missed. The planning board persists across messages in "
        "the thread, helping you stay organized and on track. Update it frequently as "
        "you complete tasks and discover new subtasks."
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

            # Get the existing memory before overwriting
            thread = await ThreadModel.get(thread_id)
            if thread is None:
                raise ValueError(f"Thread {thread_id} not found")

            previous_memory = thread.memory or ""

            # Update the memory
            await ThreadModel.set(thread_id, "memory", memory)

            # Return success message with previous content
            if previous_memory:
                return (
                    "Successfully updated planning board.\n\n"
                    "Previous content that was overwritten:\n"
                    "```\n"
                    f"{previous_memory}\n"
                    "```"
                )
            return "Successfully updated planning board."
        except Exception as e:
            logger.error("Failed to update thread memory: %s", str(e), exc_info=True)
            raise RuntimeError("Failed to update thread memory") from e
