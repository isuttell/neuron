from typing import Literal, Optional
from neuron_server.event_router import OutgoingEvent, IncomingEvent, IncomingLLMEvent
from neuron_server.models import ThreadModel
from uuid import UUID


class GetThread(IncomingEvent):
    thread_id: UUID


class ThreadExtended(ThreadModel):
    message_count: int = 0


class GetThreadResponse(OutgoingEvent):
    type: Literal["thread"] = "thread"
    thread: ThreadExtended


class GetThreads(IncomingEvent):
    personality_id: Optional[UUID] = None


class CreateThread(IncomingLLMEvent):
    name: Optional[str] = None
    context: Optional[str] = None
    personality_id: UUID


class DeleteThread(IncomingEvent):
    thread_id: UUID


class UpdateThread(IncomingEvent):
    thread_id: UUID
    name: str
    context: str
