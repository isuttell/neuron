from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from neuron_server.event_router import IncomingEvent, OutgoingEvent
from neuron_server.models.thread_model import ThreadModel


class GetThread(IncomingEvent):
    thread_id: UUID


class GetThreadResponse(OutgoingEvent):
    type: Literal["thread"] = "thread"
    thread: ThreadModel


class GetThreads(IncomingEvent):
    personality_id: UUID | None = None


class CreateThread(BaseModel):
    name: str | None = None
    context: str | None = None
    personality_id: UUID


class DeleteThread(IncomingEvent):
    thread_id: UUID


class UpdateThread(IncomingEvent):
    thread_id: UUID
    name: str
    context: str
