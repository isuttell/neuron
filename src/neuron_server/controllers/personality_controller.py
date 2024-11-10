from neuron_server.models import PersonalityModel
from quart import websocket
from neuron_server.event_router import EventRouter
from neuron_server.controllers.events.personality_events import (
    GetPersonality,
    GetPersonalities,
    GetPersonalityResponse,
    CreatePersonality,
    UpdatePersonality,
    DeletePersonality,
    PostPersonalityPrompt,
    PersonalityPromptResponse,
)
from neuron_server.llms.providers import get_provider
from neuron_server.llms.prompts import personality_update_prompt
from langchain_core.messages import AIMessage
import re
from neuron_server.llms.providers import LLM

router = EventRouter()


async def apply_personality_prompt(provider: LLM, context: str, prompt: str) -> str:
    chain = personality_update_prompt | provider.model
    message: AIMessage = await chain.ainvoke({"context": context, "prompt": prompt})
    return re.sub(r"```(?:\w+)?\s*|\s*```", "", message.content.strip()).strip()


@router.on(GetPersonality)
async def get_personality(event: GetPersonality):
    personality = await PersonalityModel.get(event.personality_id)
    if not personality:
        raise ValueError(f"Personality with id {event.personality_id} not found")
    await websocket.send(
        GetPersonalityResponse(personality=personality).model_dump_json()
    )


@router.on(GetPersonalities)
async def get_personalities(event: GetPersonalities):
    for personality in await PersonalityModel.list():
        await websocket.send(
            GetPersonalityResponse(personality=personality).model_dump_json()
        )


@router.on(CreatePersonality)
async def create_personality(event: CreatePersonality):
    provider = get_provider(event.provider_id)
    # Apply the personality prompt to the context to get the initial context
    context = await apply_personality_prompt(
        provider=provider, context="", prompt=event.context
    )
    personality = await PersonalityModel.create(
        name=event.name, context=context, memory=event.memory
    )
    await websocket.send(
        GetPersonalityResponse(personality=personality).model_dump_json()
    )


@router.on(UpdatePersonality)
async def update_personality(event: UpdatePersonality):
    personality = await PersonalityModel.update(
        id=event.id, name=event.name, context=event.context, memory=event.memory
    )
    await websocket.send(
        GetPersonalityResponse(personality=personality).model_dump_json()
    )


@router.on(DeletePersonality)
async def delete_personality(event: DeletePersonality):
    await PersonalityModel.delete(event.personality_id)


@router.on(PostPersonalityPrompt)
async def post_personality_prompt(event: PostPersonalityPrompt):
    provider = get_provider(event.provider_id)
    content = await apply_personality_prompt(
        provider=provider, context=event.context, prompt=event.prompt
    )
    await websocket.send(PersonalityPromptResponse(context=content).model_dump_json())
