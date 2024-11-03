from neuron_server.models import PersonalityModel
from quart import websocket
from neuron_server.event_router import EventRouter
from neuron_server.controllers.events.personality_events import (
    GetPersonalities,
    GetPersonalityResponse,
    CreatePersonality,
    UpdatePersonality,
    DeletePersonality,
)

router = EventRouter()


@router.on(GetPersonalities)
async def get_personalities(event: GetPersonalities):
    personalities = PersonalityModel.list()
    for personality in personalities:
        await websocket.send(
            GetPersonalityResponse(personality=personality).model_dump_json()
        )


@router.on(CreatePersonality)
async def create_personality(event: CreatePersonality):
    personality = PersonalityModel.create(
        name=event.name, context=event.context, memory=event.memory
    )
    await websocket.send(
        GetPersonalityResponse(personality=personality).model_dump_json()
    )


@router.on(UpdatePersonality)
async def update_personality(event: UpdatePersonality):
    personality = PersonalityModel.update(
        id=event.id, name=event.name, context=event.context, memory=event.memory
    )
    await websocket.send(
        GetPersonalityResponse(personality=personality).model_dump_json()
    )


@router.on(DeletePersonality)
async def delete_personality(event: DeletePersonality):
    PersonalityModel.delete(event.personality_id)
