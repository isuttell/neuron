from neuron_server.models import PersonalityModel
from quart import websocket, Blueprint, request, Response
from neuron_server.event_router import EventRouter
from neuron_server.controllers.events.personality_events import (
    PostPersonalityPrompt,
    PersonalityPromptResponse,
)
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.llms.prompts import personality_update_prompt
from langchain_core.messages import AIMessage
import re
from neuron_server.llms.llm import LLM
from neuron_server.config import config
from uuid import UUID
from werkzeug.exceptions import NotFound, BadRequest
from pydantic import BaseModel

router = EventRouter()

blueprint = Blueprint("personality", __name__)


class CreatePersonality(BaseModel):
    name: str
    context: str
    memory: str


class UpdatePersonality(CreatePersonality):
    pass


async def apply_personality_prompt(llm: LLM, context: str, prompt: str) -> str:
    chain = personality_update_prompt | llm.model
    message: AIMessage = await chain.ainvoke({"context": context, "prompt": prompt})
    return re.sub(r"```(?:\w+)?\s*|\s*```", "", message.content.strip()).strip()


@blueprint.get("/<uuid:personality_id>")
async def get_personality(personality_id: UUID):
    personality = await PersonalityModel.get(personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")
    return {"personality": personality.model_dump()}


@blueprint.get("/")
async def get_personalities():
    personalities = await PersonalityModel.list()
    return {
        "personalities": [personality.model_dump() for personality in personalities]
    }


@blueprint.post("/")
async def create_personality():
    body = await request.get_json()
    payload = CreatePersonality(**body)
    # Apply the personality prompt to the context to get the initial context
    llm: LLM = ProviderModelModel.get_llm()
    context = await apply_personality_prompt(
        llm=llm, context="", prompt=payload.context
    )
    personality = await PersonalityModel.create(
        name=payload.name, context=context, memory=payload.memory
    )
    return {"personality": personality.model_dump()}


@blueprint.put("/<uuid:personality_id>")
async def update_personality(personality_id: UUID):
    body = await request.get_json()
    payload = UpdatePersonality(**body)
    personality = await PersonalityModel.update(
        id=personality_id,
        name=payload.name,
        context=payload.context,
        memory=payload.memory,
    )
    return {"personality": personality.model_dump()}


@blueprint.delete("/<uuid:personality_id>")
async def delete_personality(personality_id: UUID):
    await PersonalityModel.delete(personality_id)
    return Response(status=204)


@router.on(PostPersonalityPrompt)
async def post_personality_prompt(event: PostPersonalityPrompt):
    llm: LLM = ProviderModelModel.get_llm()
    content = await apply_personality_prompt(
        llm=llm, context=event.context, prompt=event.prompt
    )
    await websocket.send(PersonalityPromptResponse(context=content).model_dump_json())
