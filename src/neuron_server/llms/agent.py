from datetime import datetime
from typing import Any, TypedDict
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from werkzeug.exceptions import BadRequest

from neuron_server.database import pool
from neuron_server.llms.agent_orchestrator import (
    AgentOrchestrator,
    create_agent_orchestrator,
)
from neuron_server.llms.agent_status_manager import StatusCallback
from neuron_server.llms.llm import LLM
from neuron_server.llms.message_processor import get_message_content
from neuron_server.llms.tools import get_tools
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.thread_model import ThreadModel

# Type definitions for backward compatibility


class StreamArgs(TypedDict, total=False):
    """Arguments for stream operations.

    Attributes:
        thread_id: The thread ID
        personality_id: The personality ID
        user_id: The user ID (optional)
        username: The username (optional)
        prompt: The prompt text
        location: The location string (default: San Diego coordinates)
        temp_id: Temporary ID for optimistic updates (optional)
    """

    thread_id: UUID
    personality_id: UUID
    user_id: str | None
    username: str | None
    prompt: str
    location: str
    temp_id: str | None


# Default location for backward compatibility @TODO make dynamic
DEFAULT_LOCATION = "San Diego, California at -117.1860 W and 32.84 N."


# Singleton orchestrator management
class _OrchestratorManager:
    """Manages the singleton orchestrator instance."""

    def __init__(self) -> None:
        self._instance = None

    def get(self) -> "AgentOrchestrator":
        """Get or create the orchestrator instance."""
        if self._instance is None:
            self._instance = create_agent_orchestrator()
        return self._instance


# Create the singleton manager
_orchestrator_manager = _OrchestratorManager()


def get_orchestrator() -> "AgentOrchestrator":
    """Get or create the global orchestrator instance."""
    return _orchestrator_manager.get()


async def execute_agent_with_messages(  # noqa: PLR0913
    messages: list[HumanMessage | AIMessage],
    personality_id: UUID,
    user_id: str,
    username: str,
    location: str = DEFAULT_LOCATION,
    thread_id: UUID | None = None,
    create_media_items: bool = False,
) -> list[HumanMessage | AIMessage]:
    """Execute agent with custom messages list.

    Core function that handles graph creation and execution with a custom message list.
    This function can be reused by other parts of the system that need different
    message patterns while maintaining the same agent execution logic.

    Args:
        messages: List of messages to send to the agent
        personality_id: ID of personality to use
        user_id: ID of user making request
        username: Name of user
        location: Location string (default: San Diego)
        thread_id: Optional thread ID for creating media items (default: None)
        create_media_items: Whether to create MediaItem records from artifacts
            (default: False, requires thread_id)

    Returns:
        All messages from the agent execution, including tool calls and responses

    Raises:
        BadRequest: If personality not found
    """
    personality = await PersonalityModel.get(personality_id)
    if personality is None:
        raise BadRequest("Personality not found")

    llm: LLM = await ProviderModelModel.get_active_llm()
    tools = await get_tools(personality.tool_set) if personality.tool_set else None
    graph = llm.create_workflow(tools)
    graph.checkpointer = None
    result = await graph.ainvoke(
        {
            "messages": messages,
            "location": location,
            "username": username,
            "personality": personality.context,
            "now": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        },
        config={
            "configurable": {
                "personality_id": str(personality_id),
                "user_id": str(user_id),
            },
        },
    )

    result_messages = result["messages"]

    # Process artifacts and create media items if requested
    if create_media_items and thread_id:
        from langchain_core.messages import ToolMessage

        from neuron_server.util.artifact_to_media_converter import (
            create_media_items_from_artifacts,
        )

        # Process tool messages with artifacts
        for message in result_messages:
            if (
                isinstance(message, ToolMessage)
                and hasattr(message, "artifact")
                and message.artifact
            ):
                artifacts = (
                    message.artifact
                    if isinstance(message.artifact, list)
                    else [message.artifact]
                )
                await create_media_items_from_artifacts(
                    artifacts=artifacts,
                    thread_id=thread_id,
                    user_id=user_id,
                )

    return result_messages


async def execute_agent(
    prompt: str,
    personality_id: UUID,
    user_id: str,
    username: str,
    location: str = DEFAULT_LOCATION,
) -> str:
    """Execute a one-off agent interaction without streaming.

    Args:
        prompt: User's input text
        personality_id: ID of personality to use
        user_id: ID of user making request
        username: Name of user
        location: Location string (default: San Diego)

    Returns:
        The agent's response text

    Raises:
        BadRequest: If personality not found
    """
    messages = [
        HumanMessage(
            content=(
                "I can't respond so please try you're best to fulfill my "
                "next request but don't ask questions or provide prompt "
                "suggestions. Just respond with the answer to my question."
            )
        ),
        HumanMessage(content=prompt),
    ]

    result_messages = await execute_agent_with_messages(
        messages, personality_id, user_id, username, location
    )

    # Get the last message for backward compatibility
    result: AIMessage = result_messages[-1]
    assert isinstance(result, AIMessage)

    # Use format_as_string=True to get a string result for backward compatibility
    content = get_message_content(result, format_as_string=True)
    if not content:
        return ""

    return content.strip() if isinstance(content, str) else ""


async def execute_agent_with_messages_streaming(  # noqa: PLR0913
    messages: list[HumanMessage | AIMessage],
    personality_id: UUID,
    user_id: str,
    username: str,
    location: str = DEFAULT_LOCATION,
    status_callback: StatusCallback | None = None,
) -> tuple[str, list]:
    """Execute agent with custom messages list using streaming and status callbacks.

    Similar to execute_agent_with_messages but uses the orchestrator to enable
    streaming and status callbacks. This is useful for personality chat where
    we want to track agent status changes.

    Args:
        messages: List of messages to send to the agent
        personality_id: ID of personality to use
        user_id: ID of user making request
        username: Name of user
        location: Location string (default: San Diego)
        status_callback: Optional callback for status updates

    Returns:
        Tuple of (response text, media artifacts)

    Raises:
        BadRequest: If personality not found
    """
    # Create a temporary thread for this execution
    thread = await ThreadModel.create(
        ThreadModel.CreateParams(
            personality_id=personality_id,
            user_id=user_id,
            name="Personality Chat Response",
        )
    )

    # Format the messages into a single prompt
    # For personality chat, we typically have a single HumanMessage with context
    prompt = ""
    for msg in messages:
        if isinstance(msg, HumanMessage):
            content = get_message_content(msg, format_as_string=True)
            if content:
                prompt = content
                break

    # Execute using the orchestrator with streaming
    args = StreamArgs(
        thread_id=thread.id,
        personality_id=personality_id,
        user_id=user_id,
        username=username,
        prompt=prompt,
        location=location,
    )

    # Create callbacks with just the status callback
    from neuron_server.llms.callback_handlers import CallbackHandlers

    callbacks = (
        CallbackHandlers(on_status_change=status_callback) if status_callback else None
    )

    # Use the global orchestrator
    orchestrator = get_orchestrator()
    result_text, media_artifacts = await orchestrator.execute_stream(args, callbacks)

    # Clean up the temporary thread
    await ThreadModel.delete(thread.id)

    return result_text or "", media_artifacts


async def aget_state(thread_id: UUID) -> dict[str, Any]:
    """Get the current state for a thread.

    Args:
        thread_id: ID of thread to get state for

    Returns:
        Dictionary containing thread state
    """
    checkpointer = AsyncPostgresSaver(pool)
    llm: LLM = await ProviderModelModel.get_active_llm()
    return await llm.aget_state(
        {"configurable": {"thread_id": str(thread_id)}}, checkpointer=checkpointer
    )


async def astream(args: StreamArgs) -> str | None:
    """Stream agent responses and handle message processing.

    Main entry point for streaming agent responses. Now delegates to the
    orchestrator for better maintainability.

    Args:
        args: StreamArgs containing thread_id, personality_id, and other parameters

    Returns:
        The final message content or None if no messages
    """
    from neuron_server.llms.websocket_callbacks import create_websocket_callbacks

    # Get orchestrator and execute with websocket callbacks
    orchestrator = get_orchestrator()
    result, _ = await orchestrator.execute_stream(args, create_websocket_callbacks())
    return result


# Backward compatibility functions
async def update_thread_status(
    thread: ThreadModel,
    status: str,
    force_update: bool = False,
    human_message: str | None = None,
) -> None:
    """Update thread status and publish the change.

    Backward compatibility wrapper for the status manager.
    """
    from neuron_server.llms.agent_status_manager import AgentStatusManager

    # Create a temporary status manager for backward compatibility
    status_manager = AgentStatusManager()
    await status_manager.update_thread_status(
        thread, status, force_update, human_message
    )


async def wait_for_idle(thread_id: UUID, timeout: int = 300) -> None:
    """Wait for thread status to become idle.

    Backward compatibility function.
    """
    orchestrator = get_orchestrator()
    await orchestrator._wait_for_idle(thread_id, timeout)
