import asyncio
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage

from neuron_server.controllers.events.thread_events import GetThreadResponse
from neuron_server.llms.llm import LLM
from neuron_server.logger import logger
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.thread_model import ThreadModel
from neuron_server.pubsub import pubsub


class StatusAgent:
    """Generates intelligent status messages for thread activities with throttling."""

    def __init__(
        self, thread_id: UUID, personality_name: str = "", personality_context: str = ""
    ) -> None:
        self.thread_id = thread_id
        self.last_execution_time: Optional[datetime] = None
        self.pending_task: Optional[asyncio.Task] = None
        self.pending_status: Optional[str] = None
        self.throttle_seconds = 5

        # Build system message with personality context
        system_content = (
            "You are a professional status message generator for an AI "
            "assistant. Your role is to create informative, concise status "
            "messages that help users understand what the AI is currently "
            "doing.\n\n"
        )

        # Add personality information if provided
        if personality_name or personality_context:
            system_content += (
                f"The AI assistant is currently using the '{personality_name}' "
                "personality"
            )
            if personality_context:
                system_content += (
                    f" with the following custom instructions:\n{personality_context}\n"
                )
            system_content += (
                "\nReflect this personality's tone and style in your "
                "status messages.\n\n"
            )

        system_content += (
            "RULES:\n"
            "1. Keep messages under 100 characters\n"
            "2. Be informative about the actual operation\n"
            "3. Avoid repetition\n"
            "4. Focus on what's happening right now\n"
            "5. Use the personality to guide tone and style of the "
            "status message\n\n"
            "Use the converation history to understand progress and vary your "
            "messages accordingly. If the same operation appears multiple "
            "times, infer it's taking longer and adjust your message to "
            "reflect continued work. Your responses will be shown to the "
            "user while the main agent is busy, so keep them short."
        )

        # Initialize with system message for prompt caching
        self.message_history: list[BaseMessage] = [
            SystemMessage(content=system_content)
        ]

    async def update_status(
        self, thread: ThreadModel, status: str, recent_events: list = None
    ) -> str:
        """Update status with throttling."""
        # Special handling for idle - cancel everything
        if status == "idle":
            if self.pending_task and not self.pending_task.done():
                self.pending_task.cancel()
                logger.debug(
                    f"Cancelled pending status update for thread {self.thread_id}"
                )
            self.reset()

            # Still need to update the thread status to idle!
            thread.status = "idle"
            await self._publish_status_update(thread)

            return status  # Return "idle" directly, no LLM call

        now = datetime.now()

        # First call or enough time has passed - execute immediately
        if (
            not self.last_execution_time
            or (now - self.last_execution_time).total_seconds() >= self.throttle_seconds
        ):
            self.last_execution_time = now
            generated_status = await self._generate_status_message(
                status, recent_events or []
            )
            # Update thread with generated status
            thread.status = generated_status
            await self._publish_status_update(thread)
            return generated_status

        # Too soon - queue for later
        self.pending_status = status
        if not self.pending_task or self.pending_task.done():
            # Schedule execution exactly throttle_seconds after last execution
            wait_time = (
                self.throttle_seconds - (now - self.last_execution_time).total_seconds()
            )
            self.pending_task = asyncio.create_task(
                self._execute_pending(thread, wait_time)
            )
            logger.debug(
                f"Queued status update for thread {self.thread_id}, "
                f"will fire in {wait_time:.1f}s"
            )

        # Return the current raw status for now
        return status

    async def _execute_pending(self, thread: ThreadModel, wait_time: float) -> None:
        """Execute pending update after throttle period."""
        try:
            await asyncio.sleep(wait_time)
            if self.pending_status and self.pending_status != "idle":
                self.last_execution_time = datetime.now()
                # For pending updates, we don't have recent events
                generated_status = await self._generate_status_message(
                    self.pending_status, []
                )
                # Update thread with generated status
                thread.status = generated_status
                await self._publish_status_update(thread)
                self.pending_status = None
        except asyncio.CancelledError:
            logger.debug(f"Pending status update cancelled for thread {self.thread_id}")
            raise

    async def _publish_status_update(self, thread: ThreadModel) -> None:
        """Publish the thread status update."""
        await ThreadModel.set(thread.id, "status", thread.status)
        await pubsub.publish("app", GetThreadResponse(thread=thread))

    async def _generate_status_message(
        self, current_status: str, recent_events: list
    ) -> str:
        """Generate a human-friendly status message using LLM."""
        try:
            # Get the fast model (Haiku)
            llm = await ProviderModelModel.get_active_llm()
            fast_model = llm.fast_model

            # Format event history for this update only
            event_context = ""
            if recent_events:
                event_lines = []
                for event in recent_events[-5:]:  # Last 5 events
                    event_type = (
                        "Started" if event.event_type == "start" else "Completed"
                    )
                    event_lines.append(f"- {event_type}: {event.description}")
                event_context = "Recent activity:\n" + "\n".join(event_lines) + "\n\n"

            # Get description for current operation
            from neuron_server.llms.agent import TOOL_DESCRIPTIONS

            # Handle comma-separated tools
            if "," in current_status:
                tools = [t.strip() for t in current_status.split(",")]
                descriptions = []
                for tool in tools:
                    desc = TOOL_DESCRIPTIONS.get(tool, f"Running {tool}")
                    descriptions.append(desc)
                current_description = f"Multiple operations: {', '.join(descriptions)}"
            else:
                current_description = TOOL_DESCRIPTIONS.get(
                    current_status, f"Running {current_status}"
                )

            # Create new human message with only the diff since last update
            human_message = HumanMessage(
                content=(
                    f"{event_context}"
                    f"Current operation: {current_description}\n\n"
                    "Generate a professional status message for this operation."
                )
            )

            # Add the new human message to history
            self.message_history.append(human_message)

            # Apply caching to messages if using Anthropic
            messages_to_send = self._apply_caching_if_needed(self.message_history, llm)

            # Check if caching was applied
            caching_applied = messages_to_send != self.message_history

            # Time the LLM call
            start_time = time.time()

            # Generate the status message
            response: AIMessage = await fast_model.ainvoke(messages_to_send)

            # Calculate elapsed time
            elapsed_ms = (time.time() - start_time) * 1000

            if response.content:
                status_message = response.content.strip()

                # Extract token usage if available
                token_info = ""
                if (
                    hasattr(response, "response_metadata")
                    and response.response_metadata
                ):
                    usage = response.response_metadata.get("usage", {})
                    if usage:
                        prompt_tokens = usage.get("input_tokens", 0)
                        completion_tokens = usage.get("output_tokens", 0)
                        total_tokens = usage.get(
                            "total_tokens", prompt_tokens + completion_tokens
                        )
                        cache_read = usage.get("cache_read_input_tokens", 0)
                        cache_creation = usage.get("cache_creation_input_tokens", 0)

                        token_info = (
                            f" - Tokens: prompt={prompt_tokens}"
                            f" (cache_read={cache_read}, cache_create={cache_creation})"
                            f", completion={completion_tokens}, total={total_tokens}"
                        )

                logger.debug(
                    f"Status generation took {elapsed_ms:.0f}ms{token_info}"
                    f" - Caching: {'applied' if caching_applied else 'not applied'}"
                    f" - Status: '{status_message}' for thread {self.thread_id}"
                )

                # Add AI response to history
                self.message_history.append(response)

                # Limit message history to prevent unbounded growth
                # Keep system message + last 10 exchanges (20 messages)
                max_history_size = 21
                if len(self.message_history) > max_history_size:
                    self.message_history = (
                        [self.message_history[0]]  # Keep system message
                        + self.message_history[-20:]  # Keep last 10 exchanges
                    )

                return status_message

        except Exception as e:
            logger.error(f"Error generating status message: {e}")

        # Fallback to simple formatting
        return self._format_simple_status(current_status)

    def _format_simple_status(self, status: str) -> str:
        """Simple fallback formatting."""
        # Import here to avoid circular import
        from neuron_server.llms.agent import TOOL_DESCRIPTIONS

        # Handle comma-separated tools first
        if "," in status:
            tools = status.split(",")
            return f"Working on {len(tools)} tasks"

        # Use tool description if available
        if status in TOOL_DESCRIPTIONS:
            return TOOL_DESCRIPTIONS[status]

        # Default
        return f"Processing {status}"

    def _apply_caching_if_needed(
        self, messages: list[BaseMessage], llm: LLM
    ) -> list[BaseMessage]:
        """Apply Anthropic prompt caching if available."""
        # Always create a deep copy to avoid mutating the original
        messages_copy = [msg.model_copy(deep=True) for msg in messages]

        # Check if this is an Anthropic model with caching
        if (
            hasattr(llm, "provider")
            and llm.provider == "anthropic"
            and hasattr(llm, "_apply_caching_to_messages")
        ):
            return llm._apply_caching_to_messages(messages_copy)
        return messages_copy

    def reset(self) -> None:
        """Reset the agent when thread goes idle."""
        self.last_execution_time = None
        self.pending_task = None
        self.pending_status = None
        # Reset message history to just the system message
        self.message_history = [self.message_history[0]] if self.message_history else []
        logger.debug(f"Status agent reset for thread {self.thread_id}")
