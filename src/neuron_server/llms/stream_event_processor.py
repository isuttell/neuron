"""Stream event processing functionality."""

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, ToolMessage

from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessage,
    PartialMessageEvent,
    ThreadMessage,
)
from neuron_server.llms.message_processor import get_message_content
from neuron_server.llms.thread_status_manager import ThreadStatusManager
from neuron_server.logger import logger
from neuron_server.models.thread_model import ThreadModel
from neuron_server.pubsub import pubsub


class ChainEventData(TypedDict):
    """Data structure for chain events."""

    kind: str
    name: str
    data: dict[str, Any]
    run_id: str
    active_runs: dict[str, str]


class ChainEvent(TypedDict):
    """Chain event data structure."""

    thread: ThreadModel
    event_data: ChainEventData
    human_message: str | None


class ToolEventContext(TypedDict):
    """Context for tool event handling."""

    thread: ThreadModel
    kind: str
    name: str
    run_id: str
    active_runs: dict[str, str]
    data: dict[str, Any]
    node: str | None
    human_message: str | None


class StreamEventProcessor:
    """Processes stream events from the LLM workflow."""

    def __init__(self, status_manager: ThreadStatusManager) -> None:
        """Initialize the stream event processor.

        Args:
            status_manager: Thread status manager instance
        """
        self.status_manager = status_manager

    @staticmethod
    def _clean_run_id(run_id: str) -> str:
        """Remove 'run-' prefix and clean up any extra dashes from run IDs."""
        # Remove 'run-' prefix (including any extra dashes like 'run--')
        if run_id.startswith("run-"):
            # Find where the actual ID starts (after all dashes following 'run')
            cleaned = run_id[4:]  # Remove 'run-'
            # Remove any leading dashes
            cleaned = cleaned.lstrip("-")
            return cleaned if cleaned else run_id  # Return original if empty
        return run_id

    async def _handle_chain_event(self, event: ChainEvent) -> None:
        """Handle chain start/end events.

        Processes chain lifecycle events and updates thread status accordingly.

        Args:
            event: Chain event data containing thread and event information
        """
        thread = event["thread"]
        data = event["event_data"]
        human_message = event.get("human_message")

        if data["kind"] == "on_chain_start":
            data["active_runs"][data["run_id"]] = (
                "thinking" if data["name"] == "message" else data["name"]
            )
        elif data["kind"] == "on_chain_end":
            del data["active_runs"][data["run_id"]]

        if data["name"] == "update_title" and data["kind"] == "on_chain_end":
            thread.name = data["data"]["output"]["title"]
            await ThreadModel.set(thread.id, "name", thread.name)

        values = list(set(data["active_runs"].values()))
        await self.status_manager.update_thread_status(
            thread,
            ", ".join(values) if len(values) > 0 else "thinking",
            force_update=True,
            human_message=human_message,
        )

    async def _handle_tool_event(self, ctx: ToolEventContext) -> None:
        """Handle tool start/end events.

        Processes tool lifecycle events, updates thread status, and publishes
        tool messages.

        Args:
            ctx: Tool event context containing all event data
        """
        thread = ctx["thread"]
        tool_name = ctx["name"]
        human_message = ctx.get("human_message")

        # Track tool end events
        if ctx["kind"] == "on_tool_end":
            await self.status_manager.add_tool_end_event(thread.id, tool_name)

        if ctx["kind"] == "on_tool_start":
            logger.debug(f"Starting tool {ctx['name']}...")
            ctx["active_runs"][ctx["run_id"]] = (
                ctx["name"]
                if ctx["name"] not in ["store_memory", "recall_memory"]
                else "update_memory"
            )
        elif ctx["kind"] == "on_tool_end":
            logger.debug(f"Finished tool {ctx['name']}...")
            del ctx["active_runs"][ctx["run_id"]]

        if ctx["kind"] == "on_tool_end" and isinstance(
            ctx["data"]["output"], ToolMessage
        ):
            output: ToolMessage = ctx["data"]["output"]
            # Ensure tool messages have consistent IDs
            # Use the tool's run_id as the message ID for consistency
            message_data = output.model_dump()
            message_data["id"] = self._clean_run_id(ctx["run_id"])

            # The tool message artifact (if present) will be preserved automatically
            # due to ThreadMessage's extra="allow" configuration

            message = ThreadMessage(
                **message_data,
                thread_id=ctx["thread"].id,
                node=ctx["node"],
            )
            # Filter out hidden messages
            if not output.additional_kwargs.get("hidden", False):
                await pubsub.publish("app", MessageEvent(message=message))

        values = list(set(ctx["active_runs"].values()))
        await self.status_manager.update_thread_status(
            ctx["thread"],
            ", ".join(values) if len(values) > 0 else "thinking",
            human_message=human_message,
        )

    async def _handle_chat_model_stream(
        self,
        thread: ThreadModel,
        chunk: AIMessage,
        run_id: str,
        node: str | None,
        start_time: datetime,
        index: int,
        human_message_content: str | None,
    ) -> int:
        """Handle chat model streaming events.

        Args:
            thread: Thread model instance
            chunk: AI message chunk
            run_id: Run ID for the message
            node: Graph node identifier
            start_time: Start time for the message
            index: Current streaming index
            human_message_content: Human message content for status updates

        Returns:
            Updated index
        """
        content = get_message_content(chunk)

        # Handle content which can now be a list of Content objects or a string
        if content and not chunk.additional_kwargs.get("hidden", False):
            await self.status_manager.update_thread_status(
                thread, "streaming", human_message=human_message_content
            )
            index += 1

            # If content is still a string (for backward compatibility),
            # convert it to a Content object
            if isinstance(content, str):
                content = [{"type": "text", "text": content, "index": 0}]

            await pubsub.publish(
                "app",
                PartialMessageEvent(
                    message=PartialMessage(
                        id=self._clean_run_id(run_id),  # Clean run_id to remove prefix
                        type="ai",
                        content=content,
                        thread_id=thread.id,
                        index=index,
                        status="streaming",
                        node=node,
                        created_at=start_time.isoformat(),
                    )
                ),
            )
        return index

    async def _handle_chat_model_end(
        self,
        thread: ThreadModel,
        output: AIMessage,
        run_id: str,
        node: str | None,
        start_time: datetime,
        active_runs: dict[str, str],
        human_message_content: str | None,
    ) -> None:
        """Handle chat model end events.

        Args:
            thread: Thread model instance
            output: Final AI message
            run_id: Run ID for the message
            node: Graph node identifier
            start_time: Start time for the message
            active_runs: Currently active runs
            human_message_content: Human message content for status updates
        """
        if (
            "update_title" not in active_runs.values()
            and not output.additional_kwargs.get("hidden", False)
        ):
            # Use the run_id as the message ID to match streaming messages
            message_data = output.model_dump()
            message_data["id"] = self._clean_run_id(run_id)

            message = ThreadMessage(
                **message_data,
                thread_id=thread.id,
                node=node,
            )
            if not message.created_at:
                message.created_at = start_time.isoformat()
            await pubsub.publish("app", MessageEvent(message=message))
        await self.status_manager.update_thread_status(
            thread, "thinking", human_message=human_message_content
        )

    async def process_stream_events(
        self,
        thread: ThreadModel,
        event_stream: AsyncIterator[dict[str, Any]],
        human_message_content: str | None,
        start_time: datetime,
    ) -> None:
        """Process stream events from the LLM workflow.

        Args:
            thread: Thread model instance
            event_stream: Stream of events from the LLM
            human_message_content: Human message content for status updates
            start_time: Start time for the processing
        """
        index = -1
        active_runs: dict[str, str] = {}

        async for body in event_stream:
            kind: str = body["event"]
            name: str = body["name"]
            data: dict = body["data"]
            run_id: str = body["run_id"]
            node: str | None = body["metadata"].get("langgraph_node")

            if kind in ["on_chain_start", "on_chain_end"] and name in [
                "update_title",
                "update_memory",
            ]:
                await self._handle_chain_event(
                    ChainEvent(
                        thread=thread,
                        event_data=ChainEventData(
                            kind=kind,
                            name=name,
                            data=data,
                            run_id=run_id,
                            active_runs=active_runs,
                        ),
                        human_message=human_message_content,
                    )
                )

            elif kind in ["on_tool_start", "on_tool_end"]:
                await self._handle_tool_event(
                    ToolEventContext(
                        thread=thread,
                        kind=kind,
                        name=name,
                        run_id=run_id,
                        active_runs=active_runs,
                        data=data,
                        node=node,
                        human_message=human_message_content,
                    )
                )

            elif kind == "on_chat_model_stream" and isinstance(
                data["chunk"], AIMessage
            ):
                chunk = data["chunk"]
                index = await self._handle_chat_model_stream(
                    thread,
                    chunk,
                    run_id,
                    node,
                    start_time,
                    index,
                    human_message_content,
                )

            elif kind == "on_chat_model_end":
                output: AIMessage = data["output"]
                await self._handle_chat_model_end(
                    thread,
                    output,
                    run_id,
                    node,
                    start_time,
                    active_runs,
                    human_message_content,
                )

            elif kind == "error":
                logger.error(data)


def create_stream_event_processor(
    status_manager: ThreadStatusManager,
) -> StreamEventProcessor:
    """Create a stream event processor with the given status manager.

    Args:
        status_manager: Thread status manager instance

    Returns:
        StreamEventProcessor instance
    """
    return StreamEventProcessor(status_manager)
