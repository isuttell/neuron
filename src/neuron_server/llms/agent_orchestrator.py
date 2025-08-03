"""Agent orchestration functionality."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import StateGraph

from neuron_server.controllers.events.message_events import ThreadMessage
from neuron_server.database import pool
from neuron_server.llms.agent_status_manager import AgentStatusManager
from neuron_server.llms.callback_handlers import CallbackHandlers
from neuron_server.llms.cancellation_manager import CancellationManager
from neuron_server.llms.llm import LLM
from neuron_server.llms.message_processor import get_message_content
from neuron_server.llms.stream_event_processor import StreamEventProcessor
from neuron_server.llms.tools import get_tools
from neuron_server.logger import logger
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.thread_model import ThreadModel


@dataclass
class StreamProcessingConfig:
    """Configuration for stream processing with cancellation."""

    thread: ThreadModel
    graph: StateGraph
    human_message: HumanMessage
    personality: PersonalityModel
    config: dict[str, Any]
    start_time: datetime


class AgentOrchestrator:
    """Orchestrates agent execution with all component coordination."""

    def __init__(
        self,
        status_manager: AgentStatusManager,
        stream_processor: StreamEventProcessor,
        cancellation_manager: CancellationManager,
    ) -> None:
        """Initialize the agent orchestrator.

        Args:
            status_manager: Thread status manager instance
            stream_processor: Stream event processor instance
            cancellation_manager: Cancellation manager instance
        """
        self.status_manager = status_manager
        self.stream_processor = stream_processor
        self.cancellation_manager = cancellation_manager

    async def _wait_for_idle(self, thread_id: UUID, timeout: int = 300) -> None:
        """Wait for thread status to become idle.

        Args:
            thread_id: The thread id to monitor
            timeout: Maximum time to wait in seconds (default 300 seconds / 5 minutes)

        Raises:
            TimeoutError: If thread doesn't become idle within timeout period
        """
        start_time = asyncio.get_event_loop().time()
        thread = await ThreadModel.get(thread_id)
        while thread and thread.status not in {"idle", "error"}:
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(
                    f"Thread {thread.id} did not become idle within {timeout} seconds"
                )
            logger.debug(f"Thread {thread.id} is {thread.status}. Waiting...")
            await asyncio.sleep(1)
            thread = await ThreadModel.get(thread_id)

    async def _update_title(
        self,
        thread: ThreadModel,
        llm: LLM,
        human_message: HumanMessage,
        personality_id: UUID,
        user_id: UUID,
    ) -> None:
        """Update thread title based on message content.

        Args:
            thread: Thread model instance to update
            llm: Language model instance
            human_message: Message to base title on
            personality_id: ID of personality context
            user_id: ID of user making request
        """
        try:
            logger.debug("Generating thread name...")
            title_response = await llm.call_title(
                state={
                    "title": thread.name,
                    "messages": [
                        human_message,
                    ],
                },
                config={
                    "configurable": {
                        "thread_id": str(thread.id),
                        "personality_id": str(personality_id),
                        "user_id": str(user_id),
                    },
                },
            )
            thread.name = title_response["title"]
            if thread.name:
                await ThreadModel.set(thread.id, "name", thread.name)
        except Exception as e:
            logger.error(e, exc_info=True)

    async def _get_final_state(self, thread_id: UUID) -> str | None:
        """Get final state and return last message content.

        Args:
            thread_id: Thread ID to get state for

        Returns:
            Final message content or None
        """
        checkpointer = AsyncPostgresSaver(pool)
        llm: LLM = await ProviderModelModel.get_active_llm()
        state = await llm.aget_state(
            {"configurable": {"thread_id": str(thread_id)}}, checkpointer=checkpointer
        )

        last_message: AIMessage | None = (
            state.values.get("messages", [])[-1]
            if len(state.values.get("messages", [])) > 0
            else None
        )
        if last_message:
            # Use format_as_string=True for backward compatibility with existing code
            return get_message_content(last_message, format_as_string=True)
        return None

    async def _setup_stream_processing(
        self,
        thread: ThreadModel,
        personality: PersonalityModel,
        human_message: HumanMessage,
        config: dict[str, Any],
        start_time: datetime,
    ) -> tuple[LLM, StateGraph]:
        """Set up stream processing components.

        Args:
            thread: Thread model instance
            personality: Personality model instance
            human_message: Human message to process
            config: Stream configuration
            start_time: Processing start time

        Returns:
            Tuple of (LLM instance, graph workflow)
        """
        llm: LLM = await ProviderModelModel.get_active_llm()
        tools = await get_tools(personality.tool_set) if personality.tool_set else None
        graph = llm.create_workflow(tools)
        graph.checkpointer = AsyncPostgresSaver(pool)

        # Update the thread name if it's not already set
        if not thread.name:
            asyncio.create_task(
                self._update_title(
                    thread,
                    llm,
                    human_message,
                    config["personality_id"],
                    config["user_id"],
                )
            )

        return llm, graph

    async def _process_stream_with_cancellation(
        self,
        stream_config: StreamProcessingConfig,
        callbacks: CallbackHandlers | None = None,
    ) -> tuple[str | None, list]:
        """Process stream events with cancellation support.

        Args:
            stream_config: Configuration for stream processing
            callbacks: Optional callbacks for various events

        Returns:
            Tuple of (final message content, media artifacts)
        """
        # Extract human message content for status updates (limit to 1000 chars)
        human_message_content_raw = get_message_content(
            stream_config.human_message, format_as_string=True
        )
        max_message_length = 1000
        human_message_content: str | None = None
        if human_message_content_raw and isinstance(human_message_content_raw, str):
            if len(human_message_content_raw) > max_message_length:
                human_message_content = (
                    human_message_content_raw[: max_message_length - 3] + "..."
                )
            else:
                human_message_content = human_message_content_raw

        # Store personality info for status agent
        self.status_manager.set_personality_info(
            stream_config.thread.id,
            stream_config.personality.name,
            stream_config.personality.context,
        )

        # Create event stream
        event_stream = stream_config.graph.astream_events(
            {
                "messages": [stream_config.human_message],
                "personality": stream_config.personality.context,
                "title": stream_config.thread.name,
                "location": stream_config.config["location"],
                "now": stream_config.start_time.astimezone().isoformat(
                    timespec="seconds"
                ),
            },
            config={
                "run_name": "message",
                "configurable": {
                    "thread_id": str(stream_config.thread.id),
                    "personality_id": str(stream_config.config["personality_id"]),
                    "username": stream_config.config["username"],
                    "user_id": str(stream_config.config["user_id"]),
                },
            },
            version="v2",
        )

        # Process events and collect media artifacts
        media_artifacts = await self.stream_processor.process_stream_events(
            stream_config.thread,
            event_stream,
            human_message_content,
            stream_config.start_time,
            callbacks,
        )

        # Always create media items from artifacts when present
        if media_artifacts:
            from neuron_server.util.artifact_to_media_converter import (
                create_media_items_from_artifacts,
            )

            # Convert media artifacts to dict format for the converter
            artifact_dicts = []
            for artifact in media_artifacts:
                if hasattr(artifact, "model_dump"):
                    artifact_dicts.append(artifact.model_dump())
                elif isinstance(artifact, dict):
                    artifact_dicts.append(artifact)

            if artifact_dicts:
                await create_media_items_from_artifacts(
                    artifacts=artifact_dicts,
                    thread_id=stream_config.thread.id,
                    user_id=stream_config.config.get("user_id"),
                )

        # Get final state
        final_message = await self._get_final_state(stream_config.config["thread_id"])
        return final_message, media_artifacts

    async def _validate_and_prepare_thread(self, config: dict[str, Any]) -> ThreadModel:
        """Validate and prepare thread for processing.

        Args:
            config: Stream configuration

        Returns:
            Thread model instance

        Raises:
            Exception: If thread is not found
        """
        thread = await ThreadModel.get(config["thread_id"])
        if not thread:
            raise Exception("Thread not found")
        if thread.status not in {"idle", "error"}:
            await self._wait_for_idle(config["thread_id"])

        return thread

    async def _create_message(
        self, thread: ThreadModel, config: dict[str, Any], args: dict[str, Any]
    ) -> HumanMessage:
        """Create human message.

        Args:
            thread: Thread model instance
            config: Stream configuration
            args: Original arguments

        Returns:
            Created human message
        """
        return HumanMessage(
            id=str(uuid4()),
            user_id=config["user_id"],
            content=f"<|AI|>User: {config['username']}<|AI|>\n{config['prompt']}",
            created_at=datetime.now().astimezone().isoformat(),
        )

    async def _setup_stream_tasks(  # noqa: PLR0913
        self,
        thread: ThreadModel,
        personality: PersonalityModel,
        human_message: HumanMessage,
        config: dict[str, Any],
        start_time: datetime,
        callbacks: CallbackHandlers | None = None,
    ) -> tuple[asyncio.Task, asyncio.Task]:
        """Set up stream processing and cancellation tasks.

        Args:
            thread: Thread model instance
            personality: Personality model instance
            human_message: Human message to process
            config: Stream configuration
            start_time: Processing start time
            callbacks: Optional callbacks for various events

        Returns:
            Tuple of (stream_task, cancel_task)
        """
        # Set up stream processing
        llm, graph = await self._setup_stream_processing(
            thread, personality, human_message, config, start_time
        )

        # Create cancellation event and start listener
        cancel_event = asyncio.Event()

        # Create tasks for stream processing and cancellation listening
        stream_config = StreamProcessingConfig(
            thread=thread,
            graph=graph,
            human_message=human_message,
            personality=personality,
            config=config,
            start_time=start_time,
        )
        stream_task = asyncio.create_task(
            self._process_stream_with_cancellation(stream_config, callbacks)
        )

        cancel_task = asyncio.create_task(
            self.cancellation_manager.listen_for_cancellation(
                config["thread_id"], cancel_event
            )
        )

        return stream_task, cancel_task

    async def _handle_stream_completion(
        self,
        stream_task: asyncio.Task,
        cancel_task: asyncio.Task,
        thread: ThreadModel,
        config: dict[str, Any],
    ) -> tuple[str | None, list]:
        """Handle stream completion and cancellation.

        Args:
            stream_task: Stream processing task
            cancel_task: Cancellation listening task
            thread: Thread model instance
            config: Stream configuration

        Returns:
            Tuple of (final result, media artifacts) or (None, []) if cancelled
        """
        # Handle cancellation or completion
        was_cancelled, result = await self.cancellation_manager.handle_cancellation(
            stream_task, cancel_task, config["thread_id"]
        )

        if was_cancelled:
            logger.info(f"Thread {config['thread_id']} cancelled and reset to idle")
            await self.status_manager.reset_cancelled_thread(thread)
            return None, []

        # Clean up pending tasks
        await self.cancellation_manager.cleanup_pending_tasks(
            {stream_task, cancel_task}
        )

        # Result is a tuple of (message, artifacts)
        return result if isinstance(result, tuple) else (result, [])

    async def execute_stream(  # noqa: PLR0912
        self, args: dict[str, Any], callbacks: CallbackHandlers | None = None
    ) -> tuple[str | None, list]:
        """Execute agent stream with full orchestration.

        Args:
            args: Stream arguments containing thread_id, personality_id, etc.
            callbacks: Optional callbacks for various events

        Returns:
            Tuple of (final message content, media artifacts)
        """
        default_location = "San Diego, California at -117.1860 W and 32.84 N."

        config = {
            "thread_id": args["thread_id"],
            "personality_id": args["personality_id"],
            "user_id": args.get("user_id") or "Unknown",
            "username": args.get("username") or "Unknown",
            "prompt": args["prompt"],
            "location": args.get("location", default_location),
            # Pass through any additional args like create_media_items
            **{
                k: v
                for k, v in args.items()
                if k
                not in [
                    "thread_id",
                    "personality_id",
                    "user_id",
                    "username",
                    "prompt",
                    "location",
                ]
            },
        }

        start_time = datetime.now().astimezone()
        logger.debug(f"Agent started for {config['thread_id']}")
        thread = None
        result: tuple[str | None, list] = (None, [])

        try:
            # Validate and prepare thread
            thread = await self._validate_and_prepare_thread(config)

            # Register callbacks if provided
            if callbacks and callbacks.on_status_change:
                self.status_manager.register_status_callback(
                    config["thread_id"], callbacks.on_status_change
                )

            # Set initial thinking status AFTER callback registration
            await self.status_manager.update_thread_status(
                thread, "thinking", human_message=config["prompt"], callbacks=callbacks
            )

            # Get personality
            personality = await PersonalityModel.get(config["personality_id"])
            if personality is None:
                raise Exception("Personality not found")

            # Create human message (publishing handled by callbacks if needed)
            human_message = await self._create_message(thread, config, args)

            # Notify callback if provided
            if callbacks and callbacks.on_human_message:
                message_data = human_message.model_dump()
                # Include temp_id if provided for optimistic updates
                if args.get("temp_id"):
                    message_data["temp_id"] = args["temp_id"]

                thread_message = ThreadMessage(
                    **message_data,
                    thread_id=thread.id,
                )
                await callbacks.on_human_message(thread_message)

            # Set up stream processing and cancellation tasks
            stream_task, cancel_task = await self._setup_stream_tasks(
                thread, personality, human_message, config, start_time, callbacks
            )

            # Handle completion and cleanup
            result = await self._handle_stream_completion(
                stream_task, cancel_task, thread, config
            )

        except asyncio.CancelledError:
            # Handle cancellation gracefully
            logger.info(f"Agent task cancelled for thread {config['thread_id']}")
            if thread:
                # Ensure thread is marked as idle
                thread.status = "idle"
                await ThreadModel.set(thread.id, "status", thread.status)
        except Exception as e:
            logger.error(e, exc_info=True)
            logger.error(f"AgentError: {e!r}")
            if thread:
                await self.status_manager.update_thread_status(
                    thread,
                    status="error",
                    human_message=config.get("prompt"),
                    callbacks=callbacks,
                )
            # Notify error callback if provided
            if callbacks and callbacks.on_error:
                user_id = config.get("user_id")
                await callbacks.on_error(
                    str(e), user_id if user_id != "Unknown" else None
                )

        finally:
            if thread:
                # Always set status to idle and trigger callback
                await self.status_manager.update_thread_status(
                    thread,
                    status="idle",
                    human_message=config.get("prompt"),
                    callbacks=callbacks,
                )
                # Clean up cancelled thread from tracking if it was cancelled
                if self.status_manager.is_cancelled(thread.id):
                    self.status_manager.unmark_cancelled(thread.id)
                logger.debug(f"Agent completed for {thread.id}")

            # Unregister status callback if it was registered
            if callbacks and callbacks.on_status_change and thread:
                self.status_manager.unregister_status_callback(
                    thread.id, callbacks.on_status_change
                )

        return result


# Factory function to create orchestrator with all dependencies
def create_agent_orchestrator() -> AgentOrchestrator:
    """Create an agent orchestrator with all dependencies.

    Returns:
        AgentOrchestrator instance
    """
    from neuron_server.llms.cancellation_manager import get_cancellation_manager
    from neuron_server.llms.stream_event_processor import create_stream_event_processor

    status_manager = AgentStatusManager()
    stream_processor = create_stream_event_processor(status_manager)
    cancellation_manager = get_cancellation_manager()

    return AgentOrchestrator(status_manager, stream_processor, cancellation_manager)
