import asyncio
import time
from datetime import datetime
from typing import Optional
from uuid import UUID

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from neuron_server.controllers.events.thread_events import GetThreadResponse
from neuron_server.llms.llm import LLM
from neuron_server.logger import logger
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.thread_model import ThreadModel
from neuron_server.pubsub import pubsub


class StatusMessage(BaseModel):
    """Structured output for status messages."""

    message: str = Field(
        max_length=50,
        description="Brief status message explaining the current operation",
    )


class StatusAgent:
    """Generates intelligent status messages for thread activities with throttling."""

    def __init__(
        self, thread_id: UUID, personality_name: str = "", personality_context: str = ""
    ) -> None:
        self.thread_id = thread_id
        self.last_execution_time: Optional[datetime] = None
        self.pending_task: Optional[asyncio.Task] = None
        self.pending_status: Optional[str] = None
        self.pending_human_message: Optional[str] = None
        self.throttle_seconds = 5

        # Build system message with personality context
        system_content = (
            "You are a status message generator for an AI "
            "assistant. Your role is to create informative, concise status "
            "messages that talk directly to the user. The goal is to help "
            "the users understand what the AI is currently "
            "doing at a glance. The messages are typically visible no "
            "longer than 5 seconds.\n\n"
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
                "\nYou must reflect this personality's tone, style, and emoji use in "
                "your status messages, focus on naturally explaining what's "
                "happening as the personality. That is your primary objective. \n\n"
            )

        system_content += (
            "RULES:\n"
            "1. Response in the personalities voice\n"
            "2. Keep messages under 50 characters\n"
            "3. Always mention the specific tool when they are running\n"
            "4. Treat this as an ongoing conversation - don't repeat\n"
            "5. Each status message should feel like a natural continuation "
            "from the last\n"
            "6. Don't mention usernamefs - focus on the status\n"
            "7. Don't reference specific times, or durations. Tools give no "
            "progress updates other than start/end, and durations can vary widely.\n\n"
            "Think of yourself as narrating what's happening right now. "
            "Each status update should explain the current operation(s) in "
            "context of what came before. Use the conversation history "
            "to ensure variety and avoid repetition."
        )

        # Initialize with system message for prompt caching
        self.message_history: list[BaseMessage] = [
            SystemMessage(content=system_content)
        ]

    async def update_status(
        self,
        thread: ThreadModel,
        status: str,
        recent_events: list = None,
        human_message: str | None = None,
    ) -> str:
        """Update status with throttling.

        Args:
            thread: The thread model to update
            status: The status operation being performed
            recent_events: List of recent status events
            human_message: The user's message that triggered this operation
        """
        # Special handling for idle - just reset and return
        if status == "idle":
            self.reset()
            return status  # Return "idle" directly, no LLM call

        now = datetime.now()

        # First call or enough time has passed - execute immediately
        if (
            not self.last_execution_time
            or (now - self.last_execution_time).total_seconds() >= self.throttle_seconds
        ):
            self.last_execution_time = now
            generated_status = await self._generate_status_message(
                status, recent_events or [], human_message
            )
            # Update thread with generated status
            thread.status = generated_status
            await self._publish_status_update(thread)
            return generated_status

        # Too soon - queue for later
        self.pending_status = status
        self.pending_human_message = human_message
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
            if self.pending_status:
                self.last_execution_time = datetime.now()
                # For pending updates, we might have human message
                generated_status = await self._generate_status_message(
                    self.pending_status, [], self.pending_human_message
                )
                # Update thread with generated status
                thread.status = generated_status
                await self._publish_status_update(thread)
                self.pending_status = None
                self.pending_human_message = None
        except asyncio.CancelledError:
            logger.debug(f"Pending status update cancelled for thread {self.thread_id}")
            raise

    async def _publish_status_update(self, thread: ThreadModel) -> None:
        """Publish the thread status update."""
        await ThreadModel.set(thread.id, "status", thread.status)
        await pubsub.publish("app", GetThreadResponse(thread=thread))

    async def _generate_status_message(
        self, current_status: str, recent_events: list, human_message: str | None = None
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
            from neuron_server.llms.thread_status_manager import ThreadStatusManager

            tool_descriptions = ThreadStatusManager.TOOL_DESCRIPTIONS

            # Handle comma-separated tools
            if "," in current_status:
                tools = [t.strip() for t in current_status.split(",")]
                descriptions = []
                for tool in tools:
                    desc = tool_descriptions.get(tool, f"Running {tool}")
                    descriptions.append(desc)
                current_description = f"Multiple operations: {', '.join(descriptions)}"
            else:
                current_description = tool_descriptions.get(
                    current_status, f"Running {current_status}"
                )

            # Build the prompt with user context if available
            prompt_content = f"{event_context}"

            # Add user request context if available
            if human_message:
                prompt_content += f"User request: {human_message}\n\n"

            prompt_content += (
                f"Current operation: {current_description}\n"
                f"Tool/Operation name: {current_status}\n\n"
                "Generate the next status message in our ongoing conversation."
            )

            # Create new human message with only the diff since last update
            status_prompt = HumanMessage(content=prompt_content)

            # Add the new human message to history
            self.message_history.append(status_prompt)

            # Apply caching to messages if using Anthropic
            messages_to_send = self._apply_caching_if_needed(self.message_history, llm)

            # Check if caching was applied
            caching_applied = messages_to_send != self.message_history

            # Time the LLM call
            start_time = time.time()

            # Generate the status message using structured output with raw output
            structured_model = fast_model.with_structured_output(
                StatusMessage, include_raw=True
            )
            response = await structured_model.ainvoke(messages_to_send)

            # Calculate elapsed time
            elapsed_ms = (time.time() - start_time) * 1000

            if response and response.get("parsed") and response["parsed"].message:
                status_message = response["parsed"].message

                # Extract token usage from raw response if available
                token_info = self._extract_token_info(response.get("raw"))

                logger.debug(
                    f"Status generation took {elapsed_ms:.0f}ms{token_info}"
                    f" - Caching: {'applied' if caching_applied else 'not applied'}"
                    f" - Status: '{status_message}' for thread {self.thread_id}"
                )

                # Add AI response to history as AIMessage
                ai_message = AIMessage(content=status_message)
                self.message_history.append(ai_message)

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
        from neuron_server.llms.thread_status_manager import ThreadStatusManager

        # Handle comma-separated tools first
        if "," in status:
            tools = status.split(",")
            return f"Working on {len(tools)} tasks"

        # Use tool description if available
        tool_descriptions = ThreadStatusManager.TOOL_DESCRIPTIONS
        if status in tool_descriptions:
            return tool_descriptions[status]

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
        # Cancel any pending task
        if self.pending_task and not self.pending_task.done():
            self.pending_task.cancel()
            logger.debug(f"Cancelled pending task for thread {self.thread_id}")

        # Clear all state and throttle
        self.last_execution_time = None
        self.pending_task = None
        self.pending_status = None
        self.pending_human_message = None
        # Reset message history to just the system message
        self.message_history = [self.message_history[0]] if self.message_history else []
        logger.debug(f"Status agent reset for thread {self.thread_id}")

    def _extract_token_info(self, raw_response: AIMessage | None) -> str:
        """Extract token usage information from raw response."""
        if not (
            raw_response
            and hasattr(raw_response, "response_metadata")
            and raw_response.response_metadata
        ):
            return ""

        usage = raw_response.response_metadata.get("usage", {})
        if not usage:
            return ""

        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
        cache_read = usage.get("cache_read_input_tokens", 0)
        cache_creation = usage.get("cache_creation_input_tokens", 0)

        return (
            f" - Tokens: prompt={prompt_tokens}"
            f" (cache_read={cache_read}, cache_create={cache_creation})"
            f", completion={completion_tokens}, total={total_tokens}"
        )
