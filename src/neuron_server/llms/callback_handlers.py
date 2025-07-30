"""Callback handlers for agent orchestration.

This module defines callback interfaces that allow the agent orchestrator
to be used in different contexts without tight coupling to specific
implementations like websockets.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from uuid import UUID

from neuron_server.controllers.events.message_events import (
    PartialMessage,
    ThreadMessage,
)
from neuron_server.models.thread_model import ThreadModel
from neuron_server.tools.artifact_types import ToolMediaArtifact

# Type aliases for callbacks
# Parameters: thread_id, raw_status, generated_message, human_message
StatusCallback = Callable[[UUID, str, str, str | None], Awaitable[None]]
MessageCallback = Callable[[ThreadMessage], Awaitable[None]]
PartialMessageCallback = Callable[[PartialMessage], Awaitable[None]]
ThreadUpdateCallback = Callable[[ThreadModel], Awaitable[None]]
ErrorCallback = Callable[[str, str | None], Awaitable[None]]
MediaArtifactsCallback = Callable[[list[ToolMediaArtifact]], Awaitable[None]]


@dataclass
class CallbackHandlers:
    """Collection of optional callbacks for agent orchestration events.

    All callbacks are optional. If a callback is None, the corresponding
    event will be ignored (no operation performed).
    """

    # Status changes (thread_id, raw_status, generated_message, human_message)
    on_status_change: StatusCallback | None = None

    # Message events
    on_human_message: MessageCallback | None = None
    on_ai_message: MessageCallback | None = None
    on_tool_message: MessageCallback | None = None

    # Streaming events
    on_stream_token: PartialMessageCallback | None = None

    # Thread events
    on_thread_update: ThreadUpdateCallback | None = None

    # Error events (error_message, user_id)
    on_error: ErrorCallback | None = None

    # Media artifacts
    on_media_artifacts: MediaArtifactsCallback | None = None
