"""Agent status management functionality."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from neuron_server.llms.callback_handlers import CallbackHandlers
from neuron_server.llms.status_agent import StatusAgent
from neuron_server.logger import logger
from neuron_server.models.thread_model import ThreadModel

# Type alias for status callbacks
# Parameters: thread_id, raw_status, generated_message, human_message
StatusCallback = Callable[[UUID, str, str, str | None], Coroutine[Any, Any, None]]


@dataclass
class StatusEvent:
    """Represents a status change event for tracking."""

    timestamp: datetime
    event_type: Literal["start", "end"]
    operation: str
    description: str


class AgentStatusManager:
    """Manages agent status generation and coordination."""

    # Tool descriptions for user-friendly status messages
    TOOL_DESCRIPTIONS = {
        # Memory operations
        "recall_memory": "Retrieving conversation context",
        "store_memory": "Saving conversation context",
        "update_memory": "Updating memory",
        "read_thread_memory": "Reading thread memory",
        "set_thread_memory": "Updating thread memory",
        # Image generation/processing
        "replicate_image_generation": "Creating AI-generated image",
        "replicate_kontext_image_edit": "Editing image with AI",
        "openai_image_generation": "Creating image with DALL-E",
        "automatic1111": "Generating image with Stable Diffusion",
        "app_image": "Processing application image",
        "inspect_image": "Analyzing image content",
        "inspect_webcam": "Capturing webcam image",
        "astro_finder_image": "Generating astronomy finder chart",
        # Audio/TTS/Music
        "replicate_audio_generation": "Creating AI-generated audio",
        "replicate_music_generation": "Generating music",
        "replicate_sound_effect_generation": "Creating sound effects",
        "elevenlabs_tts": "Converting text to speech",
        "elevenlabs_sound_effects": "Generating sound effects",
        "replicate_play_dialog_tts": "Synthesizing dialogue speech",
        "replicate_kokoro_tts": "Generating Kokoro voice",
        "openai_tts": "Converting text to speech with OpenAI",
        "glados_tts": "Synthesizing GLaDOS voice",
        "whisper_stt": "Transcribing audio to text",
        # Video
        "replicate_video_generation": "Creating AI-generated video",
        "ffmpeg": "Processing media file",
        "ffprobe": "Analyzing media file",
        # Document/Graph operations
        "document_inspect": "Analyzing document",
        "query_documents": "Searching documents",
        "graph_query_tool": "Querying knowledge graph",
        "graph_question_tool": "Answering from knowledge graph",
        "graph_import": "Importing to knowledge graph",
        "graph_arxiv_import": "Importing paper to graph",
        "graph_website_import": "Importing website to graph",
        # Search operations
        "arxiv_search": "Searching academic papers",
        "arxiv_summary": "Summarizing research paper",
        "arxiv_recall": "Recalling paper information",
        "arxiv_graph_import": "Importing paper to graph",
        "web_search": "Searching the web",
        "simbad_tap_search": "Searching astronomical database",
        # Astronomy tools
        "astro_coordinates": "Converting celestial coordinates",
        "astro_target_search": "Searching astronomical targets",
        "astro_object_search": "Finding celestial objects",
        "astro_observability": "Checking object visibility",
        "astrospheric_forecast": "Getting astronomy weather",
        "astrospheric_sky": "Checking sky conditions",
        "moon": "Getting moon information",
        "sun": "Getting sun information",
        "skyfield": "Computing astronomical positions",
        # Home automation
        "homeassistant_sensor": "Reading home sensor",
        "homeassistant_service": "Controlling home device",
        "security_camera": "Accessing security camera",
        "send_notification": "Sending notification",
        # Weather
        "openweathermap_forecast": "Getting weather forecast",
        "openweathermap_overview": "Getting weather overview",
        # Media lists
        "media_list_access": "Checking media list access",
        "media_list_add_item": "Adding to media list",
        "media_list_create": "Creating media list",
        "media_list_delete": "Deleting media list",
        "media_list_get_items": "Retrieving media items",
        "media_list_read": "Reading media list",
        "media_list_remove_item": "Removing from media list",
        "media_list_reorder_items": "Reordering media list",
        "media_list_update": "Updating media list",
        # Scheduling
        "schedule_prompt": "Scheduling task",
        "list_scheduled_prompts": "Listing scheduled tasks",
        "remove_scheduled_prompt": "Removing scheduled task",
        # Gaming
        "hd2_galactic_war_report": "Getting Helldivers 2 war status",
        "hd2_liberation_history": "Getting liberation history",
        "dice": "Rolling dice",
        # AI/Reasoning
        "deepseek_reasoning": "Deep reasoning analysis",
        "code_interpreter": "Executing code",
        "openai_compatible": "Running AI model",
        # Personality
        "personality_prompt": "Getting personality prompt",
        # System operations
        "thinking": "Processing your request",
        "streaming": "Writing response",
        "update_title": "Updating conversation title",
    }

    def __init__(self) -> None:
        """Initialize the thread status manager."""
        # Track status events per thread
        self._status_events: dict[UUID, list[StatusEvent]] = {}
        # Track status agents per thread
        self._status_agents: dict[UUID, StatusAgent] = {}
        # Track personality info per thread for status agents
        self._thread_personalities: dict[UUID, tuple[str, str]] = {}
        # Track cancelled threads to prevent status updates after cancellation
        self._cancelled_threads: set[UUID] = set()
        # Track status callbacks per thread
        self._status_callbacks: dict[UUID, list[StatusCallback]] = {}

    def set_personality_info(self, thread_id: UUID, name: str, context: str) -> None:
        """Set personality info for a thread."""
        self._thread_personalities[thread_id] = (name, context)

    def mark_cancelled(self, thread_id: UUID) -> None:
        """Mark a thread as cancelled."""
        self._cancelled_threads.add(thread_id)

    def unmark_cancelled(self, thread_id: UUID) -> None:
        """Remove cancelled marking from a thread."""
        self._cancelled_threads.discard(thread_id)

    def is_cancelled(self, thread_id: UUID) -> bool:
        """Check if a thread is marked as cancelled."""
        return thread_id in self._cancelled_threads

    def register_status_callback(
        self, thread_id: UUID, callback: StatusCallback
    ) -> None:
        """Register a status callback for a thread.

        Args:
            thread_id: The thread ID to register the callback for
            callback: Async function that receives (thread_id, status, description,
                human_message)
        """
        if thread_id not in self._status_callbacks:
            self._status_callbacks[thread_id] = []
        self._status_callbacks[thread_id].append(callback)
        logger.debug(f"Registered status callback for thread {thread_id}")

    def unregister_status_callback(
        self, thread_id: UUID, callback: StatusCallback | None = None
    ) -> None:
        """Unregister a status callback for a thread.

        Args:
            thread_id: The thread ID to unregister callbacks for
            callback: Specific callback to remove, or None to remove all
        """
        if thread_id in self._status_callbacks:
            if callback is None:
                # Remove all callbacks for this thread
                del self._status_callbacks[thread_id]
            else:
                # Remove specific callback
                try:
                    self._status_callbacks[thread_id].remove(callback)
                    # Clean up if no callbacks left
                    if not self._status_callbacks[thread_id]:
                        del self._status_callbacks[thread_id]
                except ValueError:
                    pass  # Callback not found, ignore

    async def add_tool_end_event(self, thread_id: UUID, tool_name: str) -> None:
        """Add a tool end event to the status tracking."""
        if thread_id in self._status_events:
            description = self.TOOL_DESCRIPTIONS.get(tool_name, f"Running {tool_name}")
            event = StatusEvent(
                timestamp=datetime.now(),
                event_type="end",
                operation=tool_name,
                description=description,
            )
            self._status_events[thread_id].append(event)

    async def update_thread_status(
        self,
        thread: ThreadModel,
        status: str,
        force_update: bool = False,
        human_message: str | None = None,
        callbacks: CallbackHandlers | None = None,
    ) -> None:
        """Update thread status and publish the change.

        Args:
            thread: Thread model instance to update
            status: New status to set
            force_update: Whether to update even if status hasn't changed
            human_message: The user's message that triggered this status update
            callbacks: Optional callback handlers for events
        """
        # Skip status updates for cancelled threads unless forcing to idle
        if thread.id in self._cancelled_threads and status != "idle":
            logger.debug(f"Skipping status update for cancelled thread {thread.id}")
            return

        if thread.status != status or force_update:
            # Initialize event tracking for this thread if needed
            if thread.id not in self._status_events:
                self._status_events[thread.id] = []

            # Get or create status agent for this thread
            if thread.id not in self._status_agents:
                # Get personality info if available
                personality_name = ""
                personality_context = ""
                if thread.id in self._thread_personalities:
                    personality_name, personality_context = self._thread_personalities[
                        thread.id
                    ]

                self._status_agents[thread.id] = StatusAgent(
                    thread.id,
                    personality_name=personality_name,
                    personality_context=personality_context,
                )

            status_agent = self._status_agents[thread.id]

            # Track the status change event
            # Handle comma-separated tools
            if "," in status:
                # Parse individual tools and create a combined description
                tools = [t.strip() for t in status.split(",")]
                descriptions = []
                for tool in tools:
                    desc = self.TOOL_DESCRIPTIONS.get(tool, tool)
                    descriptions.append(desc)
                description = f"Multiple operations: {', '.join(descriptions)}"
            else:
                description = self.TOOL_DESCRIPTIONS.get(status, status)

            event = StatusEvent(
                timestamp=datetime.now(),
                event_type="start",
                operation=status,
                description=description,
            )
            self._status_events[thread.id].append(event)

            # Get events since last update
            last_update_time = status_agent.last_execution_time or datetime.min
            recent_events = [
                e
                for e in self._status_events[thread.id]
                if e.timestamp > last_update_time
            ]

            # Define callback for status agent to use
            async def status_callback(
                thread_id: UUID,
                raw_status: str,
                generated_message: str,
                human_msg: str | None,
            ) -> None:
                """Invoke all registered callbacks for this thread."""
                if thread_id in self._status_callbacks:
                    logger.debug(
                        f"Found {len(self._status_callbacks[thread_id])} "
                        f"callbacks for thread {thread_id}"
                    )
                    for callback in self._status_callbacks[thread_id]:
                        try:
                            await callback(
                                thread_id, raw_status, generated_message, human_msg
                            )
                        except Exception as e:
                            logger.error(
                                f"Error in status callback for thread {thread_id}: {e}",
                                exc_info=True,
                            )

            # Use status agent to generate intelligent status message
            generated_status, was_generated = await status_agent.update_status(
                status, recent_events, human_message, status_callback
            )

            # If status is idle, update thread and clean up everything
            if status == "idle":
                # Update the thread status to idle
                thread.status = "idle"
                await ThreadModel.set(thread.id, "status", thread.status)
                if callbacks and callbacks.on_thread_update:
                    await callbacks.on_thread_update(thread)

                # Clean up the status agent and related data
                await self.cleanup_thread(thread.id)

    async def cleanup_thread(self, thread_id: UUID) -> None:
        """Clean up all data for a thread."""
        if thread_id in self._status_agents:
            self._status_agents[thread_id].reset()
            del self._status_agents[thread_id]
        if thread_id in self._status_events:
            del self._status_events[thread_id]
        if thread_id in self._thread_personalities:
            del self._thread_personalities[thread_id]
        if thread_id in self._status_callbacks:
            del self._status_callbacks[thread_id]

    async def reset_cancelled_thread(
        self, thread: ThreadModel, callbacks: CallbackHandlers | None = None
    ) -> None:
        """Reset a cancelled thread and clean up its status.

        Args:
            thread: Thread model instance to reset
            callbacks: Optional callback handlers for events
        """
        # Mark thread as cancelled to prevent future status updates
        self.mark_cancelled(thread.id)

        # Properly reset and clean up status agents
        await self.cleanup_thread(thread.id)

        # Set thread status to idle after cleaning up status agents
        thread.status = "idle"
        await ThreadModel.set(thread.id, "status", thread.status)
        if callbacks and callbacks.on_thread_update:
            await callbacks.on_thread_update(thread)


# Backward compatibility function
async def update_thread_status(
    thread: ThreadModel,
    status: str,
    force_update: bool = False,
    human_message: str | None = None,
) -> None:
    """Update thread status and publish the change.

    This is deprecated. Use ThreadStatusManager directly instead.
    """
    # For backward compatibility, create a temporary manager
    manager = AgentStatusManager()
    await manager.update_thread_status(thread, status, force_update, human_message)
