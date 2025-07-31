import asyncio
import os
from uuid import UUID

import aiofiles
import tiktoken
from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable
from lxml import etree
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config
from neuron_server.controllers.events.message_events import (
    PersonalityMessageEvent,
)
from neuron_server.controllers.events.personality_events import (
    PersonalityRoomStatusUpdateEvent,
    PersonalityStatusUpdateEvent,
)
from neuron_server.controllers.events.personality_room_events import (
    PersonalityRoomUpdatedEvent,
)
from neuron_server.llms.agent import execute_agent_with_messages_streaming
from neuron_server.logger import logger
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.models.personality_message_media_item_model import (
    PersonalityMessageMediaItemModel,
)
from neuron_server.models.personality_message_model import PersonalityMessageModel
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.personality_room_model import PersonalityRoomModel
from neuron_server.models.personality_user_model import PersonalityUserModel
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.thread_model import ThreadModel
from neuron_server.models.user_model import UserModel
from neuron_server.secure_pubsub import secure_pubsub
from neuron_server.tools.artifact_types import ToolMediaArtifact

# Configuration constants
RESPONSE_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence to trigger auto-response
MAX_CHAT_HISTORY_TOKENS = 10000  # Maximum tokens for chat history context
MAX_MEDIA_DESCRIPTION_LENGTH = 1000  # Maximum characters for media item descriptions

# Initialize tokenizer for token counting
tokenizer = tiktoken.encoding_for_model("gpt-4o")


class PersonalityDirectedAnalysis(BaseModel):
    """Structured output for personality message direction analysis."""

    is_directed: bool = Field(
        description="Whether the message is directed at this personality, they should "
        "respond, or it's the first message in the room"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0", ge=0.0, le=1.0
    )
    reasoning: str = Field(description="Terse explanation of the decision")
    quick_response: str | None = Field(
        description=(
            "A brief response to provide immediately when personality is busy or if a "
            "terse response like a confirmation is appropriate "
            "(None if not busy or not directed)"
        ),
        default=None,
    )
    should_use_quick_response: bool = Field(
        description="Whether to use the quick response instead of full processing",
        default=False,
    )
    suggested_room_name: str | None = Field(
        description="Suggested new room name if it should be updated (max 50 chars)",
        default=None,
    )
    should_update_room_name: bool = Field(
        description=(
            "Whether the room name should be updated based on conversation context"
        ),
        default=False,
    )


class PersonalityStatusMessage(BaseModel):
    """Structured output for personality status message generation."""

    status: str = Field(
        description=(
            "Terse status message (under 4 words) in personality's style. "
            "Must indicate what the personality is doing."
        )
    )


class PersonalityChatOrchestrator:
    """Orchestrates all personality chat functionality.

    Includes analysis, generation, and broadcasting.
    """

    def __init__(self) -> None:
        """Initialize the orchestrator."""
        pass

    def count_message_tokens(self, content: str) -> int:
        """Count tokens in a message using tiktoken.

        Args:
            content: The message content to count tokens for

        Returns:
            Number of tokens in the content
        """
        return len(tokenizer.encode(content))

    async def broadcast_personality_status_update(
        self, personality_id: UUID, status: str
    ) -> None:
        """Broadcast personality status update to all users with access.

        Args:
            personality_id: The ID of the personality
            status: The new status to broadcast
        """
        try:
            status_event = PersonalityStatusUpdateEvent(
                personality_id=personality_id,
                status=status,
            )
            await secure_pubsub.publish_personality_event(personality_id, status_event)
            logger.debug(f"Broadcast personality {personality_id} status: {status}")
        except Exception as e:
            logger.error(
                f"Error broadcasting personality status update: {e}", exc_info=True
            )

    async def broadcast_personality_room_status_update(
        self, personality_id: UUID, room_id: UUID, status: str
    ) -> None:
        """Broadcast personality room status update to users in that room.

        Args:
            personality_id: The ID of the personality
            room_id: The ID of the room
            status: The new status to broadcast
        """
        try:
            status_event = PersonalityRoomStatusUpdateEvent(
                personality_id=personality_id,
                room_id=room_id,
                status=status,
            )
            # Broadcast to room-specific channel
            await secure_pubsub.publish_personality_room_message(
                personality_id, room_id, status_event
            )
        except Exception as e:
            logger.error(f"Error broadcasting room status update: {e}", exc_info=True)

    async def get_personality_users_dict(
        self, personality_id: UUID
    ) -> dict[str, UserModel]:
        """Get all users who have access to a personality as a dictionary.

        Args:
            personality_id: The ID of the personality to get users for

        Returns:
            Dictionary mapping user_id to UserModel instances for all users
            with access to the personality
        """
        # Get all users associated with this personality
        personality_users = await PersonalityUserModel.get_personality_users(
            personality_id
        )

        if not personality_users:
            return {}

        # Extract user IDs
        user_ids = [pu.user_id for pu in personality_users]

        # Fetch user data in a single query
        user_models = await UserModel.get_by_ids(user_ids=user_ids)

        # Return as dictionary for easy lookup
        return {user.id: user for user in user_models}

    async def get_personality_fast_model(self, personality_id: UUID) -> Runnable:
        """Get the fast model for a personality's configured LLM.

        Or fallback to active LLM.

        Args:
            personality_id: The ID of the personality (currently unused but reserved
                           for future personality-specific LLM configurations)

        Returns:
            The fast model runnable for the personality or system default
        """
        # For now, use the active LLM's fast model
        # In the future, this could check personality-specific LLM configurations
        # using the personality_id parameter
        _ = personality_id  # Acknowledge parameter for future use
        active_llm = await ProviderModelModel.get_active_llm()

        if not active_llm.fast_model:
            raise ValueError("No fast model available for personality analysis")

        return active_llm.fast_model

    async def get_token_limited_message_history(
        self,
        personality_id: UUID,
        room_id: UUID,
        users: dict[str, UserModel] | None = None,
    ) -> list[PersonalityMessageModel]:
        """Get recent messages from a specific room, limited by token count.

        Args:
            personality_id: The ID of the personality
            room_id: The ID of the room to get messages from
            users: Dictionary mapping user_id to UserModel instances for token counting

        Returns:
            List of PersonalityMessageModel instances within token limit,
            ordered chronologically (oldest first)
        """
        # Get messages for this specific room ordered by creation time (newest first)
        all_messages = await PersonalityMessageModel.list(
            personality_id=personality_id, room_id=room_id, limit=1000, offset=0
        )

        if not all_messages:
            return []

        # We need to get the personality to count tokens accurately in XML format
        personality = await PersonalityModel.get(personality_id)
        if not personality:
            logger.error(f"Personality {personality_id} not found for token counting")
            return []

        # Start from newest messages and work backwards, accumulating token count
        selected_messages = []
        total_tokens = 0

        for message in all_messages:
            # Convert this single message to XML format to count tokens accurately
            temp_xml = await self.convert_to_chat_history([message], personality, users)
            message_tokens = self.count_message_tokens(temp_xml)

            # Check if adding this message would exceed our token limit
            if total_tokens + message_tokens > MAX_CHAT_HISTORY_TOKENS:
                # Skip this message and all older ones to stay within limit
                break

            selected_messages.append(message)
            total_tokens += message_tokens

        # Return messages in chronological order (oldest first) for proper context flow
        return list(reversed(selected_messages))

    async def convert_to_chat_history(  # noqa: PLR0912
        self,
        messages: list[PersonalityMessageModel],
        personality: PersonalityModel,
        users: dict[str, UserModel] | None = None,
    ) -> str:
        """Convert message history to readable XML chat format with media items.

        Args:
            messages: List of PersonalityMessageModel instances
            personality: The PersonalityModel instance
            users: Dictionary mapping user_id to UserModel instances

        Returns:
            Formatted chat history as XML string including media URLs
        """
        if not messages:
            root = etree.Element("chat_history")
            root.text = "No previous messages."
            return etree.tostring(root, encoding="unicode", pretty_print=True).strip()

        # Batch fetch media items for all messages to minimize database queries
        message_media_map = {}
        for message in messages:
            media_items = await PersonalityMessageMediaItemModel.get_media_for_message(
                message.id
            )
            if media_items:
                message_media_map[message.id] = media_items

        root = etree.Element("chat_history")

        for message in messages:
            if message.user_id is None:
                # AI/personality message
                username = personality.name
                msg_type = "personality"
            else:
                # User message
                if users and message.user_id in users:
                    username = users[message.user_id].nickname
                else:
                    username = "Unknown User"
                msg_type = "user"

            timestamp = message.created_at.isoformat()

            message_elem = etree.SubElement(root, "message")
            message_elem.set("username", username)
            message_elem.set("timestamp", timestamp)
            message_elem.set("type", msg_type)

            # Add content as a sub-element to accommodate media items
            content_elem = etree.SubElement(message_elem, "content")
            content_elem.text = message.content

            # Add media items if they exist
            media_items = message_media_map.get(message.id, [])
            if media_items:
                media_elem = etree.SubElement(message_elem, "media")
                for media_item in media_items:
                    item_elem = etree.SubElement(media_elem, "item")
                    item_elem.set("url", media_item.url)
                    item_elem.set("type", media_item.media_type)
                    if media_item.name:
                        item_elem.set("name", media_item.name)
                    if media_item.description:
                        # Limit description length to prevent overly long content
                        max_len = MAX_MEDIA_DESCRIPTION_LENGTH
                        description = media_item.description[:max_len]
                        if len(media_item.description) > max_len:
                            description += "..."
                        item_elem.set("description", description)

        return etree.tostring(root, encoding="unicode", pretty_print=True).strip()

    async def analyze_message_direction(
        self,
        personality_id: UUID,
        latest_message: PersonalityMessageModel,
        personality: PersonalityModel,
        current_status: str = "",
        current_room_name: str = "",
    ) -> PersonalityDirectedAnalysis:
        """Analyze if the latest user message is directed at the personality or
        the personality should otherwise respond.

        Args:
            personality_id: The ID of the personality
            latest_message: The latest message to analyze
            personality: The PersonalityModel instance
            current_status: Current status of the personality (empty if idle)
            current_room_name: Current name of the room

        Returns:
            PersonalityDirectedAnalysis with direction analysis and quick response
            if busy
        """
        try:
            # Get fast model
            fast_model = await self.get_personality_fast_model(personality_id)

            # Get all users who have access to this personality
            users = await self.get_personality_users_dict(personality_id)

            # Get token-limited message history from the same room
            messages = await self.get_token_limited_message_history(
                personality_id, latest_message.personality_room_id, users
            )
            chat_history = await self.convert_to_chat_history(
                messages, personality, users
            )

            # Create status-aware structured prompt
            personality_name = personality.name
            is_busy = bool(current_status.strip())

            # Build status-specific instructions clearly
            if is_busy:
                status_section = f"""BUSY STATE HANDLING:
Since {personality_name} is currently busy ({current_status}), if the message IS \
directed at the personality:
- Generate a brief, helpful quick_response that either:
  * Answers simple questions if possible within the personality \
context
  * Acknowledges the message and explains the current busy \
state
  * Suggests trying again later for complex \
requests
- Set should_use_quick_response to true"""
            else:
                status_section = f"""IDLE STATE HANDLING:
Since {personality_name} is available:
- Set should_use_quick_response to false for normal processing"""

            analysis_task = (
                f"Analyze the latest message to determine if it's directed at "
                f"{personality_name} and provide appropriate response handling."
            )
            prompt = f"""{analysis_task}

PERSONALITY CONTEXT:
Name: {personality.name}
Personality Custom Instructions for responses:
<instructions>{personality.context}</instructions>
Current Status: {current_status if is_busy else "Idle"}
Current Room Name: "{current_room_name}"

CHAT HISTORY:
{chat_history}

LATEST MESSAGE: <user>{latest_message.content}</user>

ANALYSIS REQUIREMENTS:
1. Determine if the message is directed at {personality_name}
2. Provide confidence score (0.0-1.0)
3. Explain your reasoning
4. Analyze if the room name should be updated based on conversation context

{status_section}

ROOM NAME ANALYSIS:
- Only suggest updating the room name if:
  * The conversation has established a clear, specific topic
  * The current room name is generic or doesn't reflect the conversation
  * There's enough context to create a meaningful name
- Keep suggested names:
  * Under 50 characters
  * Concise and descriptive
  * Relevant to the ongoing conversation topic
- Don't update room name for:
  * Casual greetings or small talk
  * Very early in the conversation
  * If the current name already fits well

CONSIDERATION FACTORS:
- This is {personality_name}'s personal chat room
- If no one is in the room, the personality should likely respond
- Direct mentions of the personality name
- Context clues from conversation flow
- Questions or statements directed at this specific personality
- @bot mentions or direct addressing
- Message urgency and complexity

OUTPUT: Provide structured analysis with direction and response handling."""

            # Use structured output
            structured_model = fast_model.with_structured_output(
                PersonalityDirectedAnalysis
            )
            return await structured_model.ainvoke([HumanMessage(content=prompt)])

        except Exception as e:
            logger.error(f"Error in analyze_message_direction: {e}", exc_info=True)
            # Return a safe default analysis
            return PersonalityDirectedAnalysis(
                is_directed=False,
                confidence=0.0,
                reasoning=f"Error during analysis: {str(e)}",
            )

    async def generate_personality_status_message(
        self,
        fast_model: Runnable,
        personality: PersonalityModel,
        chat_history: str,
        latest_message: str,
        action: str = "working on a request",
    ) -> str:
        """Generate personality-specific status message.

        Pure function - easy to unit test with mocked inputs.

        Args:
            fast_model: The fast model runnable for generation
            personality: The PersonalityModel instance
            chat_history: Formatted chat history string
            latest_message: The latest message content
            action: Type of status to generate (default: "working on a request")

        Returns:
            Generated status message string (under 20 characters)
        """
        try:
            prompt = f"""PERSONALITY CONTEXT:
Name: {personality.name}
Personality custom instructions for general responses. Only use it's style and tone:
<instructions>{personality.context}</instructions>

RECENT CONVERSATION:
{chat_history}

LATEST MESSAGE: <user>{latest_message}</user>

AGENT ACTION: {action}"""

            # Use structured output to ensure clean response
            structured_model = fast_model.with_structured_output(
                PersonalityStatusMessage
            )
            response = await structured_model.ainvoke([HumanMessage(content=prompt)])
            return response.status.strip()
        except Exception as e:
            logger.error(f"Error generating personality status: {e}", exc_info=True)
            return "working"

    async def update_status_with_generation(  # noqa: PLR0913
        self,
        personality_id: UUID,
        room_id: UUID,
        fast_model: Runnable,
        personality: PersonalityModel,
        chat_history: str,
        latest_message: str,
        user_id: str,
        action: str = "working on your request",
    ) -> None:
        """Generate and update personality status in background.

        Separate concerns: generation vs persistence/broadcasting.

        Args:
            personality_id: The ID of the personality
            fast_model: The fast model runnable for generation
            personality: The PersonalityModel instance
            chat_history: Formatted chat history string
            latest_message: The latest message content
            user_id: The ID of the user who triggered this status update
            action: Type of status to generate (default: "working on your request")
        """
        try:
            # Generate custom status
            custom_status = await self.generate_personality_status_message(
                fast_model=fast_model,
                personality=personality,
                chat_history=chat_history,
                latest_message=latest_message,
                action=action,
            )

            # Update room status instead of personality status
            await PersonalityRoomModel.update_status(room_id, custom_status)
            await self.broadcast_personality_room_status_update(
                personality_id, room_id, custom_status
            )

        except Exception as e:
            logger.error(f"Error in update_status_with_generation: {e}", exc_info=True)
            fallback_status = "working"
            await PersonalityRoomModel.update_status(room_id, fallback_status)
            await self.broadcast_personality_room_status_update(
                personality_id, room_id, fallback_status
            )

    async def _update_room_status_background(
        self, room_id: UUID, personality_id: UUID, status: str
    ) -> None:
        """Update room status in background without blocking agent execution.

        Args:
            room_id: The ID of the room to update
            personality_id: The ID of the personality
            status: The status message to set
        """
        try:
            await PersonalityRoomModel.update_status(room_id, status)
            await self.broadcast_personality_room_status_update(
                personality_id, room_id, status
            )
        except Exception as e:
            logger.error(
                f"Error updating room status in background: {e}", exc_info=True
            )

    async def generate_personality_response(  # noqa: PLR0913
        self,
        personality_id: UUID,
        room_id: UUID,
        personality: PersonalityModel,
        chat_history: str,
        message: PersonalityMessageModel,
        username: str,
    ) -> tuple[str, list[ToolMediaArtifact], UUID | None]:
        """Generate a personality response using the agent system.

        Args:
            personality_id: The ID of the personality
            room_id: The ID of the personality room
            personality: The PersonalityModel instance
            chat_history: Formatted chat history string
            message: The PersonalityMessageModel containing the user's message
            username: The username of the user who sent the message

        Returns:
            Tuple of (response text, list of media artifacts, thread_id).
            Response text is empty string if failed.
            Media artifacts list contains ToolMediaArtifact objects from agent.
            Thread ID is the UUID of the thread created for this agent execution.
        """
        try:
            # Create a thread for this agent execution
            thread_params = ThreadModel.CreateParams(
                personality_id=personality_id,
                user_id=message.user_id,
                name=f"Personality Chat - {personality.name[:30]}",  # Limit name length
                context="",
                memory="",
                status="idle",
            )
            thread = await ThreadModel.create(params=thread_params)

            # Fetch media items for this message
            media_items = await PersonalityMessageMediaItemModel.get_media_for_message(
                message.id
            )

            # Construct prompt with media content using XML structure
            prompt_root = etree.Element("message")

            # Add user message
            user_msg_elem = etree.SubElement(prompt_root, "user_message")
            user_msg_elem.text = message.content

            # Add attachments if any
            if media_items:
                attachments_elem = etree.SubElement(prompt_root, "attachments")

                # Define text file extensions
                text_extensions = [
                    ".md",
                    ".markdown",
                    ".txt",
                    ".csv",
                    ".json",
                    ".xml",
                    ".yaml",
                    ".yml",
                    ".toml",
                    ".ini",
                    ".log",
                ]

                for media_item in media_items:
                    # Extract extension from URL or name
                    filename = media_item.name or media_item.url.split("/")[-1]
                    ext = os.path.splitext(filename)[1].lower()

                    if ext in text_extensions:
                        # For text files, read full content
                        file_elem = etree.SubElement(attachments_elem, "file")
                        file_elem.set("name", filename)
                        file_elem.set("type", "text")

                        # Extract file path from URL
                        # URL format: {static_content_url}/user/{hash_filename}
                        hash_filename = media_item.url.split("/")[-1]
                        file_path = os.path.join(
                            neuron_config.static_folder, "user", hash_filename
                        )

                        try:
                            async with aiofiles.open(file_path, encoding="utf-8") as f:
                                content = await f.read()
                                file_elem.text = content
                        except Exception as e:
                            logger.error(f"Failed to read file {file_path}: {e}")
                            file_elem.text = f"[Error reading file: {e}]"
                    else:
                        # For non-text files, just include the link
                        file_elem = etree.SubElement(attachments_elem, "file")
                        file_elem.set("name", filename)
                        file_elem.set("type", media_item.media_type)
                        file_elem.set("url", media_item.url)

            # Convert XML to string for the prompt
            message_xml = etree.tostring(
                prompt_root, encoding="unicode", pretty_print=True
            )

            # Construct the full prompt
            prompt = (
                f"Based on this chat history, provide a brief, appropriate response "
                f"to the latest message.\n\n"
                f"Chat History:\n{chat_history}\n\n"
                f"Latest message with attachments:\n{message_xml}\n\n"
                f"Respond in plain text with a terse, conversational reply appropriate "
                f"for this chat format. Do not ask questions or provide lengthy "
                f"explanations. Keep it natural and brief."
            )

            # Create message list for agent
            messages = [HumanMessage(content=prompt)]

            # Create status callback that updates room status
            async def status_callback(
                thread_id: UUID,
                raw_status: str,
                generated_message: str,
                human_message: str | None,
            ) -> None:
                """Callback to update personality room status based on agent status.

                Args:
                    thread_id: The thread ID (temporary for personality chat)
                    raw_status: The raw status (e.g., "update_memory", "thinking")
                    generated_message: The AI-generated status message
                    human_message: The user's message that triggered this
                """
                logger.debug(
                    f"Status callback called: raw_status={raw_status}, "
                    f"generated_message={generated_message}"
                )

                # Don't update room status for idle/error
                if raw_status in ["idle", "error"]:
                    return

                # Execute status updates in background without blocking agent
                asyncio.create_task(
                    self._update_room_status_background(
                        room_id, personality_id, generated_message
                    )
                )

            # Execute agent with personality context and status callback
            response_result = await execute_agent_with_messages_streaming(
                messages=messages,
                personality_id=personality_id,
                user_id=message.user_id,
                username=username,  # Use actual username of message sender
                thread_id=thread.id,  # Use real thread_id
                status_callback=status_callback,
            )
            response_text, media_artifacts = response_result

            return response_text, media_artifacts, thread.id

        except Exception as e:
            logger.error(
                f"Error generating personality response for {personality.name}: {e}",
                exc_info=True,
            )
            return "", [], None

    async def create_and_broadcast_personality_response(  # noqa: PLR0913
        self,
        personality_id: UUID,
        room_id: UUID,
        response_content: str,
        user_id: str,
        media_artifacts: list[ToolMediaArtifact] = None,
        thread_id: UUID | None = None,
    ) -> None:
        """Create personality message and broadcast to chat room.

        Args:
            personality_id: The ID of the personality
            room_id: The ID of the personality room
            response_content: The response text to broadcast
            user_id: The ID of the user who triggered this response
            media_artifacts: Optional list of media artifacts to associate
            thread_id: Optional thread ID if agent was used for response
        """
        try:
            # Create AI response message (user_id=None indicates AI message)
            create_params = PersonalityMessageModel.CreateParams(
                personality_id=personality_id,
                personality_room_id=room_id,
                content=response_content,
                user_id=None,  # AI message
                thread_id=thread_id,  # Include thread_id if agent was used
            )
            ai_message = await PersonalityMessageModel.create(params=create_params)

            # Create media items from artifacts and associate them with the message
            created_media_items = []
            if media_artifacts:
                for artifact in media_artifacts:
                    for item in artifact.items:
                        # Create MediaItem record
                        media_params = MediaItemModel.CreateParams(
                            media_id=item.id,
                            url=item.url,
                            media_type=artifact.media_type,
                            name=item.caption,
                            description=item.description,
                            user_id=user_id,  # User who triggered this response
                            thread_id=None,  # No thread association
                        )
                        media_item = await MediaItemModel.create(params=media_params)
                        created_media_items.append(media_item)

                # Associate media items with the personality message
                if created_media_items:
                    media_item_ids = [item.id for item in created_media_items]
                    await PersonalityMessageModel.associate_media_items(
                        ai_message.id, media_item_ids
                    )

            # Broadcast to personality chat room
            media_items_data = [item.model_dump() for item in created_media_items]
            message_event = PersonalityMessageEvent(
                personality_id=personality_id,
                message_id=ai_message.id,
                room_id=room_id,
                content=ai_message.content,
                user_id=ai_message.user_id,  # None for AI
                created_at=ai_message.created_at.isoformat(),
                updated_at=ai_message.updated_at.isoformat(),
                media_items=media_items_data,
            )
            await secure_pubsub.publish_personality_room_message(
                personality_id, room_id, message_event
            )

            logger.info(f"Broadcast personality response: {response_content[:100]}...")

        except Exception as e:
            logger.error(
                f"Error creating/broadcasting personality response: {e}", exc_info=True
            )

    async def process_user_message(
        self, personality_id: UUID, message_id: UUID
    ) -> None:
        """Background task to analyze message direction and generate response.

        Args:
            personality_id: The ID of the personality
            message_id: The ID of the message to analyze
        """
        try:
            # Get message and personality
            message = await PersonalityMessageModel.get(message_id)
            personality = await PersonalityModel.get(personality_id)

            if not message or not personality or message.user_id is None:
                # Skip AI messages or missing data
                logger.debug(
                    f"Skipping direction analysis for message {message_id}: "
                    f"message exists: {message is not None}, "
                    f"personality exists: {personality is not None}, "
                    f"is user msg: {message.user_id is not None if message else False}"
                )
                return

            # Get the current room to get its name
            room = await PersonalityRoomModel.get(message.personality_room_id)
            if not room:
                logger.error(f"Room {message.personality_room_id} not found")
                return

            # Update room status instead of personality status
            await PersonalityRoomModel.update_status(
                message.personality_room_id, "contemplating"
            )
            await self.broadcast_personality_room_status_update(
                personality_id, message.personality_room_id, "contemplating"
            )

            # Analyze direction with current status and room name
            analysis = await self.analyze_message_direction(
                personality_id, message, personality, personality.status, room.name
            )

            # Log results for monitoring/debugging
            logger.debug(
                f"Message {message_id} directed at {personality.name}: "
                f"{analysis.is_directed} (confidence: {analysis.confidence:.2f}) - "
                f"{analysis.reasoning} | Quick: {analysis.should_use_quick_response}"
            )

            # Handle room name update if suggested
            if analysis.should_update_room_name and analysis.suggested_room_name:
                try:
                    # Update the room name
                    update_params = PersonalityRoomModel.UpdateParams(
                        room_id=message.personality_room_id,
                        name=analysis.suggested_room_name,
                    )
                    updated_room = await PersonalityRoomModel.update(update_params)

                    if updated_room:
                        # Broadcast room update event
                        room_update_event = PersonalityRoomUpdatedEvent(
                            personality_id=personality_id,
                            room_id=message.personality_room_id,
                            name=analysis.suggested_room_name,
                            room_type=updated_room.type,
                        )
                        await secure_pubsub.publish_personality_room_message(
                            personality_id,
                            message.personality_room_id,
                            room_update_event,
                        )
                        logger.debug(
                            f"Updated room {message.personality_room_id} name to: "
                            f"{analysis.suggested_room_name}"
                        )
                except Exception as e:
                    logger.error(f"Failed to update room name: {e}", exc_info=True)

            # Handle quick response for busy personality
            if analysis.should_use_quick_response and analysis.quick_response:
                # Create and broadcast quick response immediately
                await self.create_and_broadcast_personality_response(
                    personality_id,
                    message.personality_room_id,
                    analysis.quick_response,
                    message.user_id,
                )
                return

            # Generate automatic response if directed at personality and not busy
            if (
                analysis.is_directed
                and analysis.confidence >= RESPONSE_CONFIDENCE_THRESHOLD
                and not analysis.should_use_quick_response
            ):
                pass  # Generating full response

                # Get all users who have access to this personality
                users = await self.get_personality_users_dict(personality_id)

                # Get token-limited chat history for context from the same room
                messages = await self.get_token_limited_message_history(
                    personality_id, message.personality_room_id, users
                )
                chat_history = await self.convert_to_chat_history(
                    messages, personality, users
                )

                # Get fast model for initial status generation
                fast_model = await self.get_personality_fast_model(personality_id)

                # Generate initial custom status using fast model in background
                asyncio.create_task(
                    self.update_status_with_generation(
                        personality_id=personality_id,
                        room_id=message.personality_room_id,
                        fast_model=fast_model,
                        personality=personality,
                        chat_history=chat_history,
                        latest_message=message.content,
                        user_id=message.user_id,
                        action="thinking about your message",
                    )
                )

                # Get username for agent context
                username = "Unknown User"
                if message.user_id in users:
                    username = users[message.user_id].nickname

                # Generate personality response
                (
                    response_text,
                    media_artifacts,
                    thread_id,
                ) = await self.generate_personality_response(
                    personality_id=personality_id,
                    room_id=message.personality_room_id,
                    personality=personality,
                    chat_history=chat_history,
                    message=message,
                    username=username,
                )

                # Create and broadcast the response
                await self.create_and_broadcast_personality_response(
                    personality_id,
                    message.personality_room_id,
                    response_text,
                    message.user_id,
                    media_artifacts,
                    thread_id,
                )

        except Exception as e:
            logger.error(
                f"Error in background message direction analysis for "
                f"personality {personality_id}, message {message_id}: {e}",
                exc_info=True,
            )
        finally:
            # Clear room status
            try:
                if message and message.personality_room_id:
                    await PersonalityRoomModel.update_status(
                        message.personality_room_id, ""
                    )
                    await self.broadcast_personality_room_status_update(
                        personality_id, message.personality_room_id, ""
                    )
            except Exception as status_error:
                logger.error(f"Failed to clear room status after error: {status_error}")
