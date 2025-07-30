"""Default websocket callbacks for agent orchestration.

This module provides the default websocket-based callbacks that maintain
backward compatibility with the existing system.
"""

from uuid import UUID

from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessage,
    PartialMessageEvent,
    ThreadMessage,
)
from neuron_server.controllers.events.thread_events import GetThreadResponse
from neuron_server.event_router import ErrorEvent
from neuron_server.llms.callback_handlers import CallbackHandlers
from neuron_server.logger import logger
from neuron_server.models.thread_model import ThreadModel
from neuron_server.secure_pubsub import secure_pubsub
from neuron_server.tools.artifact_types import ToolMediaArtifact


async def on_human_message(message: ThreadMessage) -> None:
    """Publish human message via websocket."""
    await secure_pubsub.publish_thread_message(MessageEvent(message=message))


async def on_ai_message(message: ThreadMessage) -> None:
    """Publish AI message via websocket."""
    await secure_pubsub.publish_thread_message(MessageEvent(message=message))


async def on_tool_message(message: ThreadMessage) -> None:
    """Publish tool message via websocket."""
    await secure_pubsub.publish_thread_message(MessageEvent(message=message))


async def on_stream_token(partial_message: PartialMessage) -> None:
    """Publish streaming token via websocket."""
    await secure_pubsub.publish_partial_message(
        PartialMessageEvent(message=partial_message)
    )


async def on_thread_update(thread: ThreadModel) -> None:
    """Publish thread update via websocket."""
    await secure_pubsub.publish_thread_update(GetThreadResponse(thread=thread))


async def on_error(error_message: str, user_id: str | None) -> None:
    """Publish error to user via websocket."""
    if user_id:
        await secure_pubsub.publish_error_to_user(
            user_id, ErrorEvent(message=error_message)
        )
    else:
        logger.warning("Could not send error to user: user_id not available")


async def on_media_artifacts(artifacts: list[ToolMediaArtifact]) -> None:
    """Create media items from artifacts (for websocket flow).

    This is specific to the websocket flow where we want to persist
    media items to the database. Other flows might handle artifacts differently.
    """
    # For websocket flow, we need thread_id and user_id from somewhere
    # This is a limitation of the callback approach - we might need to
    # enhance the callback signature or use a closure to capture context
    logger.debug(f"Media artifacts callback received {len(artifacts)} artifacts")
    # Note: In the current implementation, media items are created in the
    # stream processor before this callback is invoked


async def on_status_change(
    thread_id: UUID, raw_status: str, generated_message: str, human_message: str | None
) -> None:
    """Update thread status with generated message and publish via websocket.

    Args:
        thread_id: The thread ID to update
        raw_status: The raw status (e.g., "update_memory", "thinking")
        generated_message: The AI-generated status message
        human_message: The user's message that triggered this
    """
    # Update the thread model with the generated status
    thread = await ThreadModel.get(thread_id)
    if thread:
        thread.status = generated_message
        await ThreadModel.set(thread_id, "status", generated_message)
        # Publish thread update via websocket
        await on_thread_update(thread)


def create_websocket_callbacks() -> CallbackHandlers:
    """Create default websocket callbacks for backward compatibility.

    Returns:
        CallbackHandlers configured for websocket publishing
    """
    return CallbackHandlers(
        on_human_message=on_human_message,
        on_ai_message=on_ai_message,
        on_tool_message=on_tool_message,
        on_stream_token=on_stream_token,
        on_thread_update=on_thread_update,
        on_error=on_error,
        on_media_artifacts=on_media_artifacts,
        on_status_change=on_status_change,
    )
