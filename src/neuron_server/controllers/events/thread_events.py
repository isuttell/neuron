from typing import Literal, Optional
from neuron_server.event_router import OutgoingEvent, IncomingEvent
from neuron_server.models.thread_model import ThreadModel
from uuid import UUID
from pydantic import BaseModel


class GetThread(IncomingEvent):
    thread_id: UUID


class GetThreadResponse(OutgoingEvent):
    type: Literal["thread"] = "thread"
    thread: ThreadModel


class GetThreads(IncomingEvent):
    personality_id: Optional[UUID] = None


class CreateThread(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None
    personality_id: UUID


class DeleteThread(IncomingEvent):
    thread_id: UUID


class UpdateThread(IncomingEvent):
    thread_id: UUID
    name: str
    context: str
