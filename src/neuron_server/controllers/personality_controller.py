from neuron_server.models import PersonalityModel
from quart import websocket, Blueprint, request, Response
from neuron_server.event_router import EventRouter
from neuron_server.controllers.events.personality_events import (
    PostPersonalityPrompt,
    PersonalityPromptResponse,
)
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.llms.prompts import (
    personality_update_prompt,
    personality_description_prompt,
)
from langchain_core.messages import AIMessage
import re
from neuron_server.llms.llm import LLM
from neuron_server.config import config
from uuid import UUID
from werkzeug.exceptions import NotFound, BadRequest
from pydantic import BaseModel
from typing import Optional
from neuron_server.logger import logger
from langchain_core.output_parsers import StrOutputParser
from neuron_server.llms.tools import get_tools, default_tools

router = EventRouter()

blueprint = Blueprint("personality", __name__)


class CreatePersonality(BaseModel):
    name: str
    description: Optional[str] = None
    context: str
    memory: str
    tool_set: Optional[str] = None


class UpdatePersonality(CreatePersonality):
    pass


async def ainvoke_update_personality(
    llm: LLM, personality: PersonalityModel, context: str, prompt: str
) -> str:
    tools = get_tools(personality.tool_set) if personality.tool_set else default_tools
    chain = personality_update_prompt | llm.model.bind_tools(tools) | StrOutputParser()
    content: str = await chain.ainvoke({"context": context, "prompt": prompt})
    return re.sub(r"```(?:\w+)?\s*|\s*```", "", content.strip()).strip()


async def ainvoke_description(llm: LLM, context: str) -> str:
    chain = personality_description_prompt | llm.model | StrOutputParser()
    content: str = await chain.ainvoke({"context": context})
    return re.sub(r"```(?:\w+)?\s*|\s*```", "", content.strip()).strip()


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
    personality = await PersonalityModel.create(
        name=payload.name,
        description=payload.description,
        context=payload.context,
        memory=payload.memory,
        tool_set=payload.tool_set,
    )
    return {"personality": personality.model_dump()}


@blueprint.put("/<uuid:personality_id>")
async def update_personality(personality_id: UUID):
    body = await request.get_json()
    payload = UpdatePersonality(**body)

    llm: LLM = ProviderModelModel.get_llm()

    # If there is no description, generate one from the context
    description = payload.description
    if (description is None or len(description.strip()) == 0) and len(
        payload.context
    ) > 0:
        description = await ainvoke_description(llm=llm, context=payload.context)

    personality = await PersonalityModel.update(
        id=personality_id,
        name=payload.name,
        description=description,
        context=payload.context,
        memory=payload.memory,
        tool_set=payload.tool_set,
    )
    return {"personality": personality.model_dump()}


@blueprint.delete("/<uuid:personality_id>")
async def delete_personality(personality_id: UUID):
    await PersonalityModel.delete(personality_id)
    return Response(status=204)


@router.on(PostPersonalityPrompt)
async def post_personality_prompt(event: PostPersonalityPrompt):
    llm: LLM = ProviderModelModel.get_llm()
    personality = await PersonalityModel.get(event.personality_id)
    if personality is None:
        raise BadRequest("Personality not found")
    content = await ainvoke_update_personality(
        llm=llm,
        personality=personality,
        context=personality.context,
        prompt=event.prompt,
    )
    await websocket.send(PersonalityPromptResponse(context=content).model_dump_json())
