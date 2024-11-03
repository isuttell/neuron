from typing import Literal, Optional
from neuron_server.event_router import OutgoingEvent, IncomingEvent, IncomingLLMEvent
from neuron_server.models import MessageModel
from uuid import UUID


class GetThreadMessages(IncomingEvent):
    thread_id: UUID


class MessageEvent(OutgoingEvent):
    type: Literal["message"] = "message"
    message: MessageModel


class PartialMessage(MessageModel):
    index: int
    status: Literal["thinking", "tools", "streaming"]


class PartialMessageEvent(OutgoingEvent):
    type: Literal["partial_message"] = "partial_message"
    message: PartialMessage


class PostMessage(IncomingLLMEvent):
    thread_id: UUID
    prompt: str
    personality_id: Optional[UUID]
