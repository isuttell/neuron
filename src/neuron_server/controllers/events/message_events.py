from typing import Literal
from neuron_server.event_router import OutgoingEvent, IncomingEvent
from uuid import UUID
from langchain_core.messages import BaseMessage


class ThreadMessage(BaseMessage):
    thread_id: UUID


class GetThreadMessages(IncomingEvent):
    thread_id: UUID


class MessageEvent(OutgoingEvent):
    type: Literal["message"] = "message"
    message: ThreadMessage


class PartialMessage(ThreadMessage):
    index: int
    status: str


class PartialMessageEvent(OutgoingEvent):
    type: Literal["partial_message"] = "partial_message"
    message: PartialMessage


class PostMessage(IncomingEvent):
    thread_id: UUID
    prompt: str
    personality_id: UUID
