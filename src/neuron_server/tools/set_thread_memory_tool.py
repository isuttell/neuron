import asyncio
import uuid
from typing import Any

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.models.thread_model import ThreadModel
from neuron_server.tools.artifact_types import (
    ToolArtifactMetadata,
    ToolMediaArtifact,
    ToolMediaItem,
)


class SetThreadMemoryToolArgs(BaseModel):
    memory: str = Field(
        description=(
            "Your internal task tracking and planning notes. This is YOUR private "
            "workspace for tracking what you need to do - not the user's tasks. "
            "Format as markdown with checkboxes (e.g., '- [ ] Analyze code structure' "
            "or '- [x] Updated function signatures'). This completely overwrites your "
            "existing notes. Include ALL your tasks and observations, not just updates."
        )
    )


class SetThreadMemoryTool(BaseTool):
    name: str = "set_thread_memory"
    description: str = (
        "YOUR internal task tracker and memory - not visible to the user. Use this "
        "to track YOUR work: what you need to analyze, implement, or remember. "
        "Essential for complex requests to ensure you complete all steps. Store your "
        "tasks as markdown checkboxes. This is YOUR private workspace that persists "
        "in the thread. Update frequently as you work through problems and discover "
        "subtasks. The user cannot see this - it's only for YOUR organization."
    )

    args_schema: type[SetThreadMemoryToolArgs] = SetThreadMemoryToolArgs
    response_format: str = "content_and_artifact"

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> tuple[str, list[dict]]:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        memory: str,
        config: RunnableConfig,
    ) -> tuple[str, list[dict]]:
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
            logger.debug(
                "Updated thread memory for thread_id=%s (length: %d characters)",
                thread_id,
                len(memory),
            )

            # Create media artifact with the updated memory
            artifacts = [
                ToolMediaArtifact(
                    media_type="text",
                    items=[
                        ToolMediaItem(
                            id=str(uuid.uuid4()),
                            url="",
                            name="Tasks Updated",
                            description=memory,
                            metadata=ToolArtifactMetadata(
                                type="thread_memory",
                            ),
                        )
                    ],
                )
            ]

            # Return success message with previous content
            if previous_memory:
                response_text = (
                    "Successfully updated your internal task tracker.\n\n"
                    "Previous notes that were overwritten:\n"
                    "```\n"
                    f"{previous_memory}\n"
                    "```"
                )
            else:
                response_text = "Successfully updated your internal task tracker."

            return response_text, [artifact.model_dump() for artifact in artifacts]
        except Exception as e:
            logger.error("Failed to update thread memory: %s", str(e), exc_info=True)
            raise RuntimeError("Failed to update thread memory") from e
