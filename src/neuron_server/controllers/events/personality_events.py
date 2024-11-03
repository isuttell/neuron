from typing import Literal, List
from neuron_server.event_router import OutgoingEvent, IncomingEvent
from neuron_server.models import PersonalityModel
from uuid import UUID


class GetPersonalities(IncomingEvent):
    pass


class GetPersonalityResponse(OutgoingEvent):
    type: Literal["personality"] = "personality"
    personality: PersonalityModel


class GetPersonalitiesResponse(OutgoingEvent):
    type: Literal["personalities"] = "personalities"
    personalities: List[PersonalityModel]


class CreatePersonality(IncomingEvent):
    name: str
    context: str
    memory: str


class UpdatePersonality(IncomingEvent):
    id: UUID
    name: str
    context: str
    memory: str


class DeletePersonality(IncomingEvent):
    personality_id: UUID
