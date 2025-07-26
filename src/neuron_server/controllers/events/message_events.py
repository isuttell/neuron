from typing import Literal
from uuid import UUID

from langchain_core.messages import BaseMessage
from pydantic import ConfigDict

from neuron_server.event_router import IncomingEvent, OutgoingEvent


class ThreadMessage(BaseMessage):
    thread_id: UUID
    user_id: str | None = None
    node: str | None = None
    created_at: str | None = None
    model_config = ConfigDict(
        extra="allow",
    )


class GetThreadMessages(IncomingEvent):
    thread_id: UUID


class MessageEvent(OutgoingEvent):
    type: Literal["message"] = "message"
    message: ThreadMessage


class PartialMessage(ThreadMessage):
    index: int
    status: str
    node: str
    model_config = ConfigDict(
        extra="allow",
    )


class PartialMessageEvent(OutgoingEvent):
    type: Literal["partial_message"] = "partial_message"
    message: PartialMessage


class PostMessage(IncomingEvent):
    thread_id: UUID
    prompt: str
    personality_id: UUID


class CancelMessage(IncomingEvent):
    thread_id: UUID


class PersonalityMessageEvent(OutgoingEvent):
    type: Literal["personality_message"] = "personality_message"
    personality_id: UUID
    message_id: UUID
    content: str
    user_id: str | None
    created_at: str
    updated_at: str
    media_items: list[dict] = []


class PersonalityMessageDeletedEvent(OutgoingEvent):
    type: Literal["personality_message_deleted"] = "personality_message_deleted"
    personality_id: UUID
    message_id: UUID
