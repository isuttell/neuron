"""Agent orchestration functionality."""

import asyncio
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from neuron_server.controllers.events.message_events import MessageEvent, ThreadMessage
from neuron_server.database import pool
from neuron_server.event_router import ErrorEvent
from neuron_server.llms.cancellation_manager import CancellationManager
from neuron_server.llms.llm import LLM
from neuron_server.llms.message_processor import get_message_content
from neuron_server.llms.stream_event_processor import StreamEventProcessor
from neuron_server.llms.thread_status_manager import ThreadStatusManager
from neuron_server.llms.tools import get_tools
from neuron_server.logger import logger
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.thread_model import ThreadModel
from neuron_server.pubsub import pubsub


class AgentOrchestrator:
    """Orchestrates agent execution with all component coordination."""

    def __init__(
        self,
        status_manager: ThreadStatusManager,
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
    ) -> tuple[LLM, Any]:
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
        logger.debug(f"provider_model_id={llm.provider_model_id}")
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
        thread: ThreadModel,
        graph: Any,
        human_message: HumanMessage,
        personality: PersonalityModel,
        config: dict[str, Any],
        start_time: datetime,
    ) -> str | None:
        """Process stream events with cancellation support.

        Args:
            thread: Thread model instance
            graph: LLM workflow graph
            human_message: Human message to process
            personality: Personality model instance
            config: Stream configuration
            start_time: Processing start time

        Returns:
            Final message content or None if cancelled
        """
        # Extract human message content for status updates (limit to 1000 chars)
        human_message_content = get_message_content(
            human_message, format_as_string=True
        )
        max_message_length = 1000
        if human_message_content and len(human_message_content) > max_message_length:
            human_message_content = (
                human_message_content[: max_message_length - 3] + "..."
            )

        # Store personality info for status agent
        self.status_manager.set_personality_info(
            thread.id, personality.name, personality.context
        )

        # Create event stream
        event_stream = graph.astream_events(
            {
                "messages": [human_message],
                "personality": personality.context,
                "title": thread.name,
                "location": config["location"],
                "now": start_time.astimezone().isoformat(timespec="seconds"),
            },
            config={
                "run_name": "message",
                "configurable": {
                    "thread_id": str(thread.id),
                    "personality_id": str(config["personality_id"]),
                    "username": config["username"],
                    "user_id": str(config["user_id"]),
                },
            },
            version="v2",
        )

        # Process events
        await self.stream_processor.process_stream_events(
            thread, event_stream, human_message_content, start_time
        )

        # Get final state
        return await self._get_final_state(config["thread_id"])

    async def execute_stream(self, args: dict[str, Any]) -> str | None:
        """Execute agent stream with full orchestration.

        Args:
            args: Stream arguments containing thread_id, personality_id, etc.

        Returns:
            Final message content or None if cancelled or no messages
        """
        default_location = "San Diego, California at -117.1860 W and 32.84 N."

        config = {
            "thread_id": args["thread_id"],
            "personality_id": args["personality_id"],
            "user_id": args.get("user_id") or "Unknown",
            "username": args.get("username") or "Unknown",
            "prompt": args["prompt"],
            "location": args.get("location", default_location),
        }

        start_time = datetime.now().astimezone()
        logger.debug(f"Agent started for {config['thread_id']}")
        thread = None
        result: str | None = None

        try:
            # Get and validate thread
            thread = await ThreadModel.get(config["thread_id"])
            if not thread:
                raise Exception("Thread not found")
            if thread.status not in {"idle", "error"}:
                await self._wait_for_idle(config["thread_id"])

            await self.status_manager.update_thread_status(
                thread, "thinking", human_message=config["prompt"]
            )

            # Get personality
            personality = await PersonalityModel.get(config["personality_id"])
            if personality is None:
                raise Exception("Personality not found")

            # Create and publish human message
            human_message = HumanMessage(
                id=str(uuid4()),
                user_id=config["user_id"],
                content=f"<|AI|>User: {config['username']}<|AI|>\n{config['prompt']}",
                created_at=datetime.now().astimezone().isoformat(),
            )

            message_data = human_message.model_dump()
            # Include temp_id if provided for optimistic updates
            if args.get("temp_id"):
                message_data["temp_id"] = args["temp_id"]

            await pubsub.publish(
                "app",
                MessageEvent(
                    message=ThreadMessage(
                        **message_data,
                        thread_id=thread.id,
                    )
                ),
            )

            # Set up stream processing
            llm, graph = await self._setup_stream_processing(
                thread, personality, human_message, config, start_time
            )

            # Create cancellation event and start listener
            cancel_event = asyncio.Event()

            # Create tasks for stream processing and cancellation listening
            stream_task = asyncio.create_task(
                self._process_stream_with_cancellation(
                    thread, graph, human_message, personality, config, start_time
                )
            )

            cancel_task = asyncio.create_task(
                self.cancellation_manager.listen_for_cancellation(
                    config["thread_id"], cancel_event
                )
            )

            # Handle cancellation or completion
            was_cancelled, result = await self.cancellation_manager.handle_cancellation(
                stream_task, cancel_task, config["thread_id"]
            )

            if was_cancelled:
                logger.info(f"Thread {config['thread_id']} cancelled and reset to idle")
                await self.status_manager.reset_cancelled_thread(thread)
                result = None

            # Clean up pending tasks
            await self.cancellation_manager.cleanup_pending_tasks(
                {stream_task, cancel_task}
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
                    thread, status="error", human_message=config.get("prompt")
                )
            await pubsub.publish("app", ErrorEvent(message=str(e)))

        finally:
            if thread:
                # Only update status if thread wasn't cancelled
                if not self.status_manager.is_cancelled(thread.id):
                    await self.status_manager.update_thread_status(
                        thread, status="idle", human_message=config.get("prompt")
                    )
                else:
                    # Clean up cancelled thread from tracking
                    self.status_manager.unmark_cancelled(thread.id)
                logger.debug(f"Agent completed for {thread.id}")

        return result


# Factory function to create orchestrator with all dependencies
def create_agent_orchestrator() -> AgentOrchestrator:
    """Create an agent orchestrator with all dependencies.

    Returns:
        AgentOrchestrator instance
    """
    from neuron_server.llms.cancellation_manager import get_cancellation_manager
    from neuron_server.llms.stream_event_processor import create_stream_event_processor
    from neuron_server.llms.thread_status_manager import get_status_manager

    status_manager = get_status_manager()
    stream_processor = create_stream_event_processor(status_manager)
    cancellation_manager = get_cancellation_manager()

    return AgentOrchestrator(status_manager, stream_processor, cancellation_manager)
