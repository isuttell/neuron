import asyncio
from uuid import UUID

import tiktoken
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.runnables import Runnable
from lxml import etree
from pydantic import BaseModel, Field
from quart import Blueprint, Response
from werkzeug.exceptions import Forbidden, NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.controllers.events.message_events import (
    PersonalityMessageDeletedEvent,
    PersonalityMessageEvent,
)
from neuron_server.controllers.events.personality_events import (
    PersonalityStatusUpdateEvent,
)
from neuron_server.controllers.events.room_events import (
    JoinPersonalityRoom,
    LeavePersonalityRoom,
    RoomJoinedEvent,
    RoomLeftEvent,
    UserJoinedRoomEvent,
    UserLeftRoomEvent,
)
from neuron_server.event_router import EventRouter
from neuron_server.llms.agent import execute_agent_with_messages
from neuron_server.logger import logger
from neuron_server.models.personality_message_model import PersonalityMessageModel
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.personality_user_model import PersonalityUserModel
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.user_model import UserModel
from neuron_server.permission_service import permission_service
from neuron_server.room_manager import room_manager
from neuron_server.secure_pubsub import secure_pubsub
from neuron_server.tools.artifact_types import ToolMediaArtifact
from neuron_server.type_defs.request_proxy import request
from neuron_server.websocket_session_manager import WebSocketSession

blueprint = Blueprint("personality_message", __name__)
router = EventRouter()

# Configuration constants
RESPONSE_CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence to trigger auto-response
MAX_CHAT_HISTORY_TOKENS = 10000  # Maximum tokens for chat history context

# Initialize tokenizer for token counting
tokenizer = tiktoken.encoding_for_model("gpt-4o")


class CreatePersonalityMessage(BaseModel):
    content: str = Field(description="The message content")


class UpdatePersonalityMessage(BaseModel):
    content: str = Field(description="The updated message content")


class PersonalityDirectedAnalysis(BaseModel):
    """Structured output for personality message direction analysis."""
    is_directed: bool = Field(
        description="Whether the message is directed at this personality"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0", ge=0.0, le=1.0
    )
    reasoning: str = Field(description="Terse explanation of the decision")
    quick_response: str | None = Field(
        description="A brief response to provide immediately when personality is busy (None if not busy or not directed)",
        default=None
    )
    should_use_quick_response: bool = Field(
        description="Whether to use the quick response instead of full processing",
        default=False
    )


def count_message_tokens(content: str) -> int:
    """Count tokens in a message using tiktoken.

    Args:
        content: The message content to count tokens for

    Returns:
        Number of tokens in the content
    """
    return len(tokenizer.encode(content))


async def broadcast_personality_status_update(personality_id: UUID, status: str) -> None:
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
        await secure_pubsub.publish_personality_room_message(personality_id, status_event)
        logger.debug(f"Broadcast personality {personality_id} status: {status}")
    except Exception as e:
        logger.error(f"Error broadcasting personality status update: {e}", exc_info=True)


async def get_personality_users_dict(personality_id: UUID) -> dict[str, UserModel]:
    """Get all users who have access to a personality as a dictionary.

    Args:
        personality_id: The ID of the personality to get users for

    Returns:
        Dictionary mapping user_id to UserModel instances for all users
        with access to the personality
    """
    # Get all users associated with this personality
    personality_users = await PersonalityUserModel.get_personality_users(personality_id)

    if not personality_users:
        return {}

    # Extract user IDs
    user_ids = [pu.user_id for pu in personality_users]

    # Fetch user data in a single query
    user_models = await UserModel.get_by_ids(user_ids=user_ids)

    # Return as dictionary for easy lookup
    return {user.id: user for user in user_models}


async def get_personality_fast_model(personality_id: UUID) -> Runnable:
    """Get the fast model for a personality's configured LLM or fallback to active LLM.

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
    personality_id: UUID, users: dict[str, UserModel] | None = None
) -> list[PersonalityMessageModel]:
    """Get recent messages limited by token count for optimal context usage.

    Args:
        personality_id: The ID of the personality
        users: Dictionary mapping user_id to UserModel instances for token counting

    Returns:
        List of PersonalityMessageModel instances within token limit,
        ordered chronologically (oldest first)
    """
    # Get all messages for this personality ordered by creation time (newest first)
    all_messages = await PersonalityMessageModel.list(
        personality_id=personality_id, limit=1000, offset=0
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
        temp_xml = convert_to_chat_history([message], personality, users)
        message_tokens = count_message_tokens(temp_xml)

        # Check if adding this message would exceed our token limit
        if total_tokens + message_tokens > MAX_CHAT_HISTORY_TOKENS:
            # Skip this message and all older ones to stay within limit
            break

        selected_messages.append(message)
        total_tokens += message_tokens

    # Return messages in chronological order (oldest first) for proper context flow
    return list(reversed(selected_messages))


def convert_to_chat_history(
    messages: list[PersonalityMessageModel],
    personality: PersonalityModel,
    users: dict[str, UserModel] | None = None
) -> str:
    """Convert message history to readable XML chat format.

    Args:
        messages: List of PersonalityMessageModel instances
        personality: The PersonalityModel instance
        users: Dictionary mapping user_id to UserModel instances

    Returns:
        Formatted chat history as XML string
    """
    if not messages:
        root = etree.Element("chat_history")
        root.text = "No previous messages."
        return etree.tostring(root, encoding="unicode", pretty_print=True).strip()

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
        message_elem.text = message.content

    return etree.tostring(root, encoding="unicode", pretty_print=True).strip()


async def process_latest_message(
    personality_id: UUID,
    latest_message: PersonalityMessageModel,
    personality: PersonalityModel,
    current_status: str = "",
) -> PersonalityDirectedAnalysis:
    """Analyze if the latest user message is directed at the personality.

    Args:
        personality_id: The ID of the personality
        latest_message: The latest message to analyze
        personality: The PersonalityModel instance
        current_status: Current status of the personality (empty if idle)

    Returns:
        PersonalityDirectedAnalysis with direction analysis and quick response if busy
    """
    try:
        # Get fast model
        fast_model = await get_personality_fast_model(personality_id)

        # Get all users who have access to this personality
        users = await get_personality_users_dict(personality_id)

        # Get token-limited message history
        messages = await get_token_limited_message_history(personality_id, users)
        chat_history = convert_to_chat_history(messages, personality, users)

        # Create status-aware structured prompt
        personality_name = personality.name
        is_busy = bool(current_status.strip())

        # Build status-specific instructions clearly
        if is_busy:
            status_section = f"""BUSY STATE HANDLING:
Since {personality_name} is currently busy ({current_status}), if the message IS directed at the personality:
- Generate a brief, helpful quick_response that either:
  * Answers simple questions if possible within the personality context
  * Acknowledges the message and explains the current busy state
  * Suggests trying again later for complex requests
- Set should_use_quick_response to true"""
        else:
            status_section = f"""IDLE STATE HANDLING:
Since {personality_name} is available:
- Set should_use_quick_response to false for normal processing"""

        prompt = f"""Analyze the latest message to determine if it's directed at {personality_name} and provide appropriate response handling.

PERSONALITY CONTEXT:
Name: {personality.name}
Personality Custom Instructions for responses:
<instructions>{personality.context}</instructions>
Current Status: {current_status if is_busy else "Idle"}

CHAT HISTORY:
{chat_history}

LATEST MESSAGE: <user>{latest_message.content}</user>

ANALYSIS REQUIREMENTS:
1. Determine if the message is directed at {personality_name}
2. Provide confidence score (0.0-1.0)
3. Explain your reasoning

{status_section}

CONSIDERATION FACTORS:
- This is {personality_name}'s personal chat room
- Direct mentions of the personality name
- Context clues from conversation flow
- Questions or statements directed at this specific personality
- @bot mentions or direct addressing
- Message urgency and complexity

OUTPUT: Provide structured analysis including direction determination and appropriate response handling."""

        # Use structured output
        structured_model = fast_model.with_structured_output(
            PersonalityDirectedAnalysis
        )
        return await structured_model.ainvoke([HumanMessage(content=prompt)])

    except Exception as e:
        logger.error(f"Error in process_latest_message: {e}", exc_info=True)
        # Return a safe default analysis
        return PersonalityDirectedAnalysis(
            is_directed=False,
            confidence=0.0,
            reasoning=f"Error during analysis: {str(e)}"
        )


async def generate_personality_status_message(
    fast_model: Runnable,
    personality: PersonalityModel,
    chat_history: str,
    latest_message: str,
    action: str = "working on a request"
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
        Generated status message string (under 50 characters)
    """
    try:
        prompt = f"""PERSONALITY CONTEXT:
Name: {personality.name}
Personality Custom Instructions for responses:
<instructions>{personality.context}</instructions>

RECENT CONVERSATION:
{chat_history}

LATEST MESSAGE: <user>{latest_message}</user>

AGENT ACTION: {action}

Generate a couple word status message in your personality's style.
Keep it under four words and be terse.

Status message:"""
        # Use the fast model to generate status
        response = await fast_model.ainvoke([HumanMessage(content=prompt)])
        # Extract and clean the response
        if not hasattr(response, 'content'):
            raise ValueError("No content in response")
        return response.content.strip()
    except Exception as e:
        logger.error(f"Error generating personality status: {e}", exc_info=True)
        return "working"


async def update_status_with_generation(
    personality_id: UUID,
    fast_model: Runnable,
    personality: PersonalityModel,
    chat_history: str,
    latest_message: str,
    action: str = "working on your request"
) -> None:
    """Generate and update personality status in background.

    Separate concerns: generation vs persistence/broadcasting.

    Args:
        personality_id: The ID of the personality
        fast_model: The fast model runnable for generation
        personality: The PersonalityModel instance
        chat_history: Formatted chat history string
        latest_message: The latest message content
        action: Type of status to generate (default: "working on your request")
    """
    try:
        # Generate custom status
        custom_status = await generate_personality_status_message(
            fast_model=fast_model,
            personality=personality,
            chat_history=chat_history,
            latest_message=latest_message,
            action=action
        )

        await PersonalityModel.update_status(personality_id, custom_status)
        await broadcast_personality_status_update(personality_id, custom_status)
        logger.debug(f"Updated {personality.name} status to: {custom_status}")

    except Exception as e:
        logger.error(f"Error in update_status_with_generation: {e}", exc_info=True)
        fallback_status = "working"
        await PersonalityModel.update_status(personality_id, fallback_status)
        await broadcast_personality_status_update(personality_id, fallback_status)


async def generate_personality_response(
    personality_id: UUID,
    personality: PersonalityModel,
    chat_history: str,
    latest_message: str,
    user_id: str,
) -> tuple[str, list[ToolMediaArtifact]]:
    """Generate a personality response using the agent system.

    Args:
        personality_id: The ID of the personality
        personality: The PersonalityModel instance
        chat_history: Formatted chat history string
        latest_message: The latest message content
        user_id: The user who sent the message

    Returns:
        Tuple of (response text, list of media artifacts).
        Response text is empty string if failed.
        Media artifacts list contains ToolMediaArtifact objects from agent execution.
    """
    try:
        # Construct contextual prompt for terse chat response
        prompt = (
            f"Based on this chat history, provide a brief, appropriate response "
            f"to the latest message.\n\n"
            f"Chat History:\n{chat_history}\n\n"
            f'Latest message: "{latest_message}"\n\n'
            f"Respond in plain text with a terse, conversational reply appropriate "
            f"for this chat format. Do not ask questions or provide lengthy "
            f"explanations. Keep it natural and brief."
        )

        # Create message list for agent
        messages = [HumanMessage(content=prompt)]

        # Execute agent with personality context
        result_messages = await execute_agent_with_messages(
            messages=messages,
            personality_id=personality_id,
            user_id=user_id,
            username="system",  # Generic username for personality responses
            create_media_items=False,  # No media items needed for personality chat
        )

        # Extract response text from last AI message
        response_text = ""
        if result_messages and isinstance(result_messages[-1], AIMessage):
            from neuron_server.llms.message_processor import get_message_content

            content = get_message_content(result_messages[-1], format_as_string=True)
            response_text = content.strip() if content else ""

        # Extract media artifacts from all tool messages
        media_artifacts = []
        for message in result_messages:
            if (isinstance(message, ToolMessage) and
                hasattr(message, "artifact") and message.artifact):
                # Handle both single artifact and list of artifacts
                artifacts = (message.artifact if isinstance(message.artifact, list)
                           else [message.artifact])

                for artifact_dict in artifacts:
                    # Only process media artifacts
                    if (isinstance(artifact_dict, dict) and
                        artifact_dict.get("type") == "media"):
                        try:
                            # Parse the artifact using Pydantic model for validation
                            artifact = ToolMediaArtifact.model_validate(artifact_dict)
                            media_artifacts.append(artifact)
                        except Exception as e:
                            logger.error(
                                f"Failed to parse media artifact: {e}", exc_info=True
                            )
                            continue

        return response_text, media_artifacts

    except Exception as e:
        logger.error(
            f"Error generating personality response for {personality.name}: {e}",
            exc_info=True,
        )
        return "", []


async def create_and_broadcast_personality_response(
    personality_id: UUID,
    response_content: str,
    media_artifacts: list[ToolMediaArtifact] = None,
) -> None:
    """Create personality message and broadcast to chat room.

    Args:
        personality_id: The ID of the personality
        response_content: The response text to broadcast
        media_artifacts: Optional list of media artifacts to associate with the message
    """
    try:
        # Create AI response message (user_id=None indicates AI message)
        create_params = PersonalityMessageModel.CreateParams(
            personality_id=personality_id,
            content=response_content,
            user_id=None,  # AI message
        )
        ai_message = await PersonalityMessageModel.create(params=create_params)

        # Create media items from artifacts and associate them with the message
        created_media_items = []
        if media_artifacts:
            from neuron_server.models.media_item_model import MediaItemModel

            for artifact in media_artifacts:
                for item in artifact.items:
                    # Create MediaItem record
                    media_params = MediaItemModel.CreateParams(
                        media_id=item.id,
                        url=item.url,
                        media_type=artifact.media_type,
                        name=item.caption,
                        description=item.description,
                        user_id="system",  # AI-generated media
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
            content=ai_message.content,
            user_id=ai_message.user_id,  # None for AI
            created_at=ai_message.created_at.isoformat(),
            updated_at=ai_message.updated_at.isoformat(),
            media_items=media_items_data,
        )
        await secure_pubsub.publish_personality_room_message(
            personality_id, message_event
        )

        logger.info(f"Broadcast personality response: {response_content[:100]}...")

    except Exception as e:
        logger.error(
            f"Error creating/broadcasting personality response: {e}", exc_info=True
        )


async def process_agent_response(
    personality_id: UUID, message_id: UUID
) -> None:
    """Background task to analyze message direction without blocking the request.

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
                f"is user message: {message.user_id is not None if message else False}"
            )
            return

        await PersonalityModel.update_status(personality_id, "contemplating")
        await broadcast_personality_status_update(personality_id, "contemplating")

        # Analyze direction with current status
        analysis = await process_latest_message(personality_id, message, personality, personality.status)

        # Log results for monitoring/debugging
        logger.debug(
            f"Message {message_id} directed at {personality.name}: "
            f"{analysis.is_directed} (confidence: {analysis.confidence:.2f}) - "
            f"{analysis.reasoning} | Quick response needed: {analysis.should_use_quick_response}"
        )

        # Handle quick response for busy personality
        if analysis.should_use_quick_response and analysis.quick_response:
            # Create and broadcast quick response immediately
            await create_and_broadcast_personality_response(
                personality_id, analysis.quick_response
            )
            return

        # Generate automatic response if message is directed at personality and not busy
        if (analysis.is_directed and
            analysis.confidence >= RESPONSE_CONFIDENCE_THRESHOLD and
            not analysis.should_use_quick_response):
            logger.debug(
                f"Generating full response for message directed at {personality.name}"
            )

            # Get all users who have access to this personality
            users = await get_personality_users_dict(personality_id)

            # Get token-limited chat history for context
            messages = await get_token_limited_message_history(personality_id, users)
            chat_history = convert_to_chat_history(messages, personality, users)

            # Get fast model for status generation
            fast_model = await get_personality_fast_model(personality_id)

            # Generate dynamic status message in background and broadcast update
            asyncio.create_task(update_status_with_generation(
                personality_id=personality_id,
                fast_model=fast_model,
                personality=personality,
                chat_history=chat_history,
                latest_message=message.content
            ))

            # Generate personality response
            response_text, media_artifacts = await generate_personality_response(
                personality_id=personality_id,
                personality=personality,
                chat_history=chat_history,
                latest_message=message.content,
                user_id=message.user_id,
            )

            # Create and broadcast the response
            await create_and_broadcast_personality_response(
                personality_id, response_text, media_artifacts
            )

    except Exception as e:
        logger.error(
            f"Error in background message direction analysis for "
            f"personality {personality_id}, message {message_id}: {e}",
            exc_info=True
        )
    finally:
        # Clear personality status
        try:
            await PersonalityModel.update_status(personality_id, "")
            await broadcast_personality_status_update(personality_id, "")
        except Exception as status_error:
            logger.error(f"Failed to clear personality status after error: {status_error}")


@blueprint.get("/<uuid:personality_id>")
@requires_auth
async def get_personality_messages(personality_id: UUID) -> dict[str, list[dict]]:
    """Get messages for a personality.

    Args:
        personality_id: The ID of the personality to get messages for

    Returns:
        A dictionary with a list of personality messages

    Raises:
        NotFound: If the personality doesn't exist or user doesn't have access
    """
    user_id = request.token.user_id

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Get query parameters for pagination
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    # Validate pagination parameters
    limit = min(limit, 100)
    if limit < 1:
        limit = 50
    offset = max(offset, 0)

    # Get messages for the personality
    messages = await PersonalityMessageModel.list(
        personality_id=personality_id, limit=limit, offset=offset
    )

    # Get all users who have access to this personality
    users_dict = await get_personality_users_dict(personality_id)
    users = list(users_dict.values())

    # Get media items for each message and include them in the response
    from neuron_server.models.personality_message_media_item_model import (
        PersonalityMessageMediaItemModel,
    )

    messages_with_media = []
    for message in messages:
        message_data = message.model_dump()
        # Get associated media items
        media_items = await PersonalityMessageMediaItemModel.get_media_for_message(
            message.id
        )
        message_data["media_items"] = [item.model_dump() for item in media_items]
        messages_with_media.append(message_data)

    return {
        "personality_messages": messages_with_media,
        "personality": personality.model_dump(),
        "users": [user.model_dump() for user in users],
    }


@blueprint.post("/<uuid:personality_id>")
@requires_auth
@requires_csrf
async def create_personality_message(personality_id: UUID) -> dict[str, dict]:
    """Create a new message for a personality.

    Args:
        personality_id: The ID of the personality to create a message for

    Returns:
        A dictionary with the created message

    Raises:
        NotFound: If the personality doesn't exist or user doesn't have access
        BadRequest: If the request data is invalid
    """
    user_id = request.token.user_id

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Note: Allow messages even when personality is busy - quick responses will be handled during analysis

    # Parse request body
    body = await request.get_json()
    payload = CreatePersonalityMessage(**body)

    # Create the message
    create_params = PersonalityMessageModel.CreateParams(
        personality_id=personality_id,
        content=payload.content,
        user_id=user_id,  # Message is from the user
    )
    message = await PersonalityMessageModel.create(params=create_params)

    # Broadcast the new message to users in the personality chat room
    message_event = PersonalityMessageEvent(
        personality_id=personality_id,
        message_id=message.id,
        content=message.content,
        user_id=message.user_id,
        created_at=message.created_at.isoformat(),
        updated_at=message.updated_at.isoformat(),
    )
    await secure_pubsub.publish_personality_room_message(personality_id, message_event)

    # Start background task to analyze message direction (non-blocking)
    asyncio.create_task(process_agent_response(personality_id, message.id))

    return {"personality_message": message.model_dump()}


@blueprint.put("/<uuid:personality_id>/messages/<uuid:message_id>")
@requires_auth
@requires_csrf
async def update_personality_message(
    personality_id: UUID, message_id: UUID
) -> dict[str, dict]:
    """Update a personality message.

    Args:
        personality_id: The ID of the personality
        message_id: The ID of the message to update

    Returns:
        A dictionary with the updated message

    Raises:
        NotFound: If the personality or message doesn't exist or user lacks access
        Forbidden: If the user doesn't own the message
    """
    user_id = request.token.user_id

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Get the message to verify ownership
    message = await PersonalityMessageModel.get(message_id)
    if not message:
        raise NotFound(f"Message with id {message_id} not found")

    # Verify the message belongs to this personality
    if message.personality_id != personality_id:
        raise NotFound(f"Message does not belong to personality {personality_id}")

    # Verify the user owns the message (can't edit personality responses)
    if message.user_id != user_id:
        raise Forbidden("You can only edit your own messages")

    # Parse request body
    body = await request.get_json()
    payload = UpdatePersonalityMessage(**body)

    # Update the message
    update_params = PersonalityMessageModel.UpdateParams(
        message_id=message_id,
        content=payload.content,
    )
    updated_message = await PersonalityMessageModel.update(params=update_params)

    if not updated_message:
        raise NotFound(f"Message with id {message_id} not found")

    # Broadcast the updated message to users in the personality chat room
    message_event = PersonalityMessageEvent(
        personality_id=personality_id,
        message_id=updated_message.id,
        content=updated_message.content,
        user_id=updated_message.user_id,
        created_at=updated_message.created_at.isoformat(),
        updated_at=updated_message.updated_at.isoformat(),
    )
    await secure_pubsub.publish_personality_room_message(personality_id, message_event)

    return {"personality_message": updated_message.model_dump()}


@blueprint.delete("/<uuid:personality_id>/messages/<uuid:message_id>")
@requires_auth
@requires_csrf
async def delete_personality_message(
    personality_id: UUID, message_id: UUID
) -> Response:
    """Delete a personality message.

    Args:
        personality_id: The ID of the personality
        message_id: The ID of the message to delete

    Returns:
        204 No Content

    Raises:
        NotFound: If the personality or message doesn't exist or user lacks access
        Forbidden: If the user doesn't have permission to delete the message
    """
    user_id = request.token.user_id

    # Check if user has admin access to the personality
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )

    # If not admin, check if user has regular access and owns the message
    if not has_admin:
        personality = await PersonalityModel.get_for_user(
            personality_id=personality_id, user_id=user_id
        )
        if not personality:
            raise NotFound(
                f"Personality {personality_id} not found or you don't have access"
            )

        # Get the message to verify ownership
        message = await PersonalityMessageModel.get(message_id)
        if not message:
            raise NotFound(f"Message with id {message_id} not found")

        # Verify the message belongs to this personality
        if message.personality_id != personality_id:
            raise NotFound(f"Message does not belong to personality {personality_id}")

        # Non-admin users can only delete their own messages
        if message.user_id != user_id:
            raise Forbidden("You can only delete your own messages")
    else:
        # Admin can delete any message, but verify message exists
        message = await PersonalityMessageModel.get(message_id)
        if not message:
            raise NotFound(f"Message with id {message_id} not found")

        if message.personality_id != personality_id:
            raise NotFound(f"Message does not belong to personality {personality_id}")

    # Delete the message
    await PersonalityMessageModel.delete(message_id)

    # Broadcast the message deletion to users in the personality chat room
    delete_event = PersonalityMessageDeletedEvent(
        personality_id=personality_id,
        message_id=message_id,
    )
    await secure_pubsub.publish_personality_room_message(personality_id, delete_event)

    return Response(status=204)


@router.on(JoinPersonalityRoom)
async def ajoin_personality_room(
    event: JoinPersonalityRoom, session: WebSocketSession | None = None
) -> None:
    """Handle joining a personality chat room with permission checks."""
    if not session:
        logger.error("JoinPersonalityRoom event received without session context")
        return

    user_id = session.user_id
    nickname = session.nickname
    personality_id = event.personality_id

    # Check if user has access to this personality
    has_access = await permission_service.user_has_personality_access(
        user_id, personality_id
    )
    if not has_access:
        logger.warning(
            f"User {user_id} denied access to personality room {personality_id}"
        )
        return

    # Join the personality room
    # Debug: Check room state before join
    current_members = await room_manager.get_personality_room_members(personality_id)
    logger.debug(f"Current members in room {personality_id} before join: {current_members}")
    
    joined = await room_manager.join_personality_room(personality_id, user_id, nickname)

    if joined:
        # Send confirmation to the user who joined
        member_count = len(
            await room_manager.get_personality_room_members(personality_id)
        )
        join_event = RoomJoinedEvent(
            room_type="personality",
            room_id=str(personality_id),
            member_count=member_count,
        )
        await secure_pubsub.publish_to_user(user_id, join_event)

        # Notify other room members that this user joined
        room_members = await room_manager.get_personality_room_members(personality_id)
        other_members = [member for member in room_members if member != user_id]

        if other_members:
            user_joined_event = UserJoinedRoomEvent(
                room_type="personality",
                room_id=str(personality_id),
                user_id=user_id,
                nickname=nickname,
            )
            await secure_pubsub.publish_to_users(other_members, user_joined_event)

        logger.info(
            f"User {user_id} ({nickname}) joined personality room {personality_id}"
        )
    else:
        # User already in room - treat as successful rejoin
        # Send confirmation to the user so their client state updates
        member_count = len(
            await room_manager.get_personality_room_members(personality_id)
        )
        join_event = RoomJoinedEvent(
            room_type="personality",
            room_id=str(personality_id),
            member_count=member_count,
        )
        await secure_pubsub.publish_to_user(user_id, join_event)
        
        logger.info(
            f"User {user_id} ({nickname}) rejoined personality room {personality_id}"
        )


@router.on(LeavePersonalityRoom)
async def aleave_personality_room(
    event: LeavePersonalityRoom, session: WebSocketSession | None = None
) -> None:
    """Handle leaving a personality chat room."""
    if not session:
        logger.error("LeavePersonalityRoom event received without session context")
        return

    user_id = session.user_id
    nickname = session.nickname
    personality_id = event.personality_id

    # Get current room members before leaving
    room_members = await room_manager.get_personality_room_members(personality_id)
    other_members = [member for member in room_members if member != user_id]

    # Leave the personality room
    left = await room_manager.leave_personality_room(personality_id, user_id)

    if left:
        # Send confirmation to the user who left
        leave_event = RoomLeftEvent(
            room_type="personality", room_id=str(personality_id)
        )
        await secure_pubsub.publish_to_user(user_id, leave_event)

        # Notify other room members that this user left
        if other_members:
            user_left_event = UserLeftRoomEvent(
                room_type="personality",
                room_id=str(personality_id),
                user_id=user_id,
                nickname=nickname,
            )
            await secure_pubsub.publish_to_users(other_members, user_left_event)

        logger.info(
            f"User {user_id} ({nickname}) left personality room {personality_id}"
        )
    else:
        logger.debug(f"User {user_id} was not in personality room {personality_id}")


async def cleanup_user_personality_rooms(session: WebSocketSession) -> None:
    """Clean up user from all personality rooms when they disconnect."""
    user_id = session.user_id
    nickname = session.nickname
    logger.info(f"Starting cleanup of user {user_id} from all personality rooms")

    # Get all rooms the user is in
    user_rooms = await room_manager.get_user_rooms(user_id)
    logger.info(f"Found {len(user_rooms)} rooms for user {user_id}: {user_rooms}")

    for room_info in user_rooms:
        room_type = room_info["room_type"]
        room_id = room_info["room_id"]

        # Only clean up personality rooms since this controller only handles those
        if room_type != "personality":
            continue

        # Get current room members before leaving
        room_members = await room_manager.get_room_members(room_type, room_id)
        other_members = [member for member in room_members if member != user_id]

        # Leave the room
        left = await room_manager.leave_room(room_type, room_id, user_id)
        logger.info(f"User {user_id} left room {room_type}:{room_id} - success: {left}")

        if left and other_members:
            # Notify other room members that this user left
            user_left_event = UserLeftRoomEvent(
                room_type=room_type, room_id=room_id, user_id=user_id, nickname=nickname
            )
            await secure_pubsub.publish_to_users(other_members, user_left_event)

    # Also use the room manager's cleanup method for personality rooms
    await room_manager.cleanup_user_from_all_rooms(user_id)
