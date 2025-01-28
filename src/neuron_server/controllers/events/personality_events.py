from typing import Literal
from uuid import UUID

from neuron_server.event_router import IncomingEvent, OutgoingEvent
from neuron_server.models.personality_model import PersonalityModel


class PostPersonalityPrompt(IncomingEvent):
    personality_id: UUID
    context: str
    prompt: str


class PersonalityPromptResponse(OutgoingEvent):
    type: Literal["personality_prompt_response"] = "personality_prompt_response"
    context: str


class GetPersonality(IncomingEvent):
    personality_id: UUID


class GetPersonalities(IncomingEvent):
    pass


class GetPersonalityResponse(OutgoingEvent):
    type: Literal["personality"] = "personality"
    personality: PersonalityModel


class GetPersonalitiesResponse(OutgoingEvent):
    type: Literal["personalities"] = "personalities"
    personalities: list[PersonalityModel]
