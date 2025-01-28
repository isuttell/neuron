from neuron_server.models import PersonalityModel
from quart import websocket, Blueprint, request, Response
from neuron_server.event_router import EventRouter
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
from langchain_core.runnables import Runnable
from neuron_server.models.embedding_model import EmbeddingModel
from neuron_server.controllers.auth import requires_auth

router = EventRouter()

blueprint = Blueprint("personality", __name__)


class CreatePersonality(BaseModel):
    name: str
    description: Optional[str] = None
    context: str
    memory: str
    logo: Optional[str] = None
    tool_set: Optional[str] = None


class UpdatePersonality(CreatePersonality):
    pass


async def ainvoke_update_personality(
    llm: LLM, personality: PersonalityModel, context: str, prompt: str
) -> str:
    tools = get_tools(personality.tool_set) if personality.tool_set else default_tools
    chain: Runnable = personality_update_prompt | llm.model | StrOutputParser()
    content: str = await chain.ainvoke({"context": context, "prompt": prompt})
    assert isinstance(content, str)
    match = re.search(r"<\|context\|>(.*?)</?\|context\|>", content, re.DOTALL)
    if not match:
        raise ValueError("No context tags found in response")
    return match.group(1).strip()


async def ainvoke_description(llm: LLM, context: str) -> str:
    chain = personality_description_prompt | llm.model | StrOutputParser()
    content: str = await chain.ainvoke({"context": context})
    return re.sub(r"```(?:\w+)?\s*|\s*```", "", content.strip()).strip()


@blueprint.get("/<uuid:personality_id>")
@requires_auth
async def get_personality(personality_id: UUID):
    personality = await PersonalityModel.get(personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")
    return {"personality": personality.model_dump()}


@blueprint.get("/<uuid:personality_id>/embeddings")
@requires_auth
async def get_personality_embeddings(personality_id: UUID):
    personality = await PersonalityModel.get(personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")
    embeddings = await EmbeddingModel.filter_by_metadata(
        key="personality_id", value=personality_id
    )

    return {
        "embeddings": [
            embedding.model_dump(exclude={"embedding"}) for embedding in embeddings
        ],
        "personalities": [personality.model_dump()],
    }


@blueprint.delete("/<uuid:personality_id>/embeddings/<embedding_id>")
@requires_auth
async def delete_personality_embedding(personality_id: UUID, embedding_id: str):
    personality = await PersonalityModel.get(personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")
    embedding = await EmbeddingModel.get(embedding_id)
    if not embedding:
        raise NotFound(f"Embedding with id {embedding_id} not found")
    await embedding.delete()
    return Response(None, status=204)


@blueprint.delete("/<uuid:personality_id>/embeddings")
@requires_auth
async def delete_personality_embeddings(personality_id: UUID):
    personality = await PersonalityModel.get(personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")
    embeddings = await EmbeddingModel.filter_by_metadata(
        key="personality_id", value=personality_id
    )
    for embedding in embeddings:
        await embedding.delete()
    return Response(None, status=204)


@blueprint.get("/")
@requires_auth
async def get_personalities():
    personalities = await PersonalityModel.list()
    return {
        "personalities": [personality.model_dump() for personality in personalities]
    }


@blueprint.post("/")
@requires_auth
async def create_personality():
    body = await request.get_json()
    payload = CreatePersonality(**body)
    personality = await PersonalityModel.create(
        name=payload.name,
        description=payload.description,
        context=payload.context,
        memory=payload.memory,
        logo=payload.logo,
        tool_set=payload.tool_set,
    )
    return {"personality": personality.model_dump()}


@blueprint.put("/<uuid:personality_id>")
@requires_auth
async def update_personality(personality_id: UUID):
    body = await request.get_json()
    payload = UpdatePersonality(**body)

    llm: LLM = await ProviderModelModel.get_active_llm()

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
        logo=payload.logo,
    )
    return {"personality": personality.model_dump()}


@blueprint.delete("/<uuid:personality_id>")
@requires_auth
async def delete_personality(personality_id: UUID):
    await PersonalityModel.delete(personality_id)
    return Response(status=204)


class PostPersonalityContext(BaseModel):
    context: str
    prompt: str


@blueprint.post("/<uuid:personality_id>/context")
@requires_auth
async def post_personality_context(personality_id: UUID):
    body = await request.get_json()
    payload = PostPersonalityContext(**body)
    llm: LLM = await ProviderModelModel.get_active_llm()
    personality = await PersonalityModel.get(personality_id)
    if personality is None:
        raise BadRequest("Personality not found")
    context = await ainvoke_update_personality(
        llm=llm,
        personality=personality,
        context=payload.context,
        prompt=payload.prompt,
    )
    return {"context": context}
