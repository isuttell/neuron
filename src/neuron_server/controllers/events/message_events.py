from typing import Literal, Optional
from neuron_server.event_router import OutgoingEvent, IncomingEvent
from uuid import UUID
from langchain_core.messages import BaseMessage
from pydantic import ConfigDict


class ThreadMessage(BaseMessage):
    thread_id: UUID
    node: Optional[str] = None
    created_at: Optional[str] = None
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
