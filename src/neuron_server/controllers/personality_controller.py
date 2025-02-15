import re
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from quart import Blueprint, Response, request
from werkzeug.exceptions import BadRequest, NotFound

from neuron_server.controllers.auth import TokenPayload, requires_auth
from neuron_server.event_router import EventRouter
from neuron_server.llms.llm import LLM
from neuron_server.llms.prompts import (
    personality_description_prompt,
    personality_update_logo_prompt,
    personality_update_prompt,
)
from neuron_server.llms.tools import (
    AppImageTool,
    ReplicateImageGenerationTool,
    default_tools,
    get_tools,
)
from neuron_server.models import PersonalityModel
from neuron_server.models.embedding_model import EmbeddingModel
from neuron_server.models.provider_model import ProviderModelModel

router = EventRouter()

blueprint = Blueprint("personality", __name__)


class CreatePersonality(BaseModel):
    name: str
    description: str | None = None
    context: str
    memory: str
    logo: str | None = None
    tool_set: str | None = None


class UpdatePersonality(CreatePersonality):
    pass


class MissingContextError(Exception):
    def __init__(self, message: str, response: str) -> None:
        self.message = message
        self.response = response
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"MissingContextError: {self.message}\nResponse:\n{self.response}"


async def ainvoke_update_personality(
    llm: LLM, personality: PersonalityModel, context: str, prompt: str
) -> str:
    tools = get_tools(personality.tool_set) if personality.tool_set else default_tools
    chain: Runnable = (
        personality_update_prompt | llm.model.bind_tools(tools) | StrOutputParser()
    )
    content: str = await chain.ainvoke({"context": context, "prompt": prompt})
    assert isinstance(content, str)
    match = re.search(r"<\|context\|>(.*?)</?\|context\|>", content, re.DOTALL)
    if not match:
        raise MissingContextError("No context tags found in response", content)
    return match.group(1).strip()


async def ainvoke_description(llm: LLM, context: str) -> str:
    chain = personality_description_prompt | llm.model | StrOutputParser()
    content: str = await chain.ainvoke({"context": context})
    return re.sub(r"```(?:\w+)?\s*|\s*```", "", content.strip()).strip()


@blueprint.get("/<uuid:personality_id>")
@requires_auth
async def get_personality(personality_id: UUID) -> dict[str, dict]:
    personality = await PersonalityModel.get(personality_id=personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")
    return {"personality": personality.model_dump()}


@blueprint.get("/<uuid:personality_id>/embeddings")
@requires_auth
async def get_personality_embeddings(personality_id: UUID) -> dict[str, list[dict]]:
    personality = await PersonalityModel.get(personality_id=personality_id)
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
async def delete_personality_embedding(
    personality_id: UUID,
    embedding_id: str,
) -> Response:
    personality = await PersonalityModel.get(personality_id=personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")
    embedding = await EmbeddingModel.get(embedding_id)
    if not embedding:
        raise NotFound(f"Embedding with id {embedding_id} not found")
    await embedding.delete()
    return Response(None, status=204)


@blueprint.delete("/<uuid:personality_id>/embeddings")
@requires_auth
async def delete_personality_embeddings(personality_id: UUID) -> Response:
    personality = await PersonalityModel.get(personality_id=personality_id)
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
async def get_personalities() -> dict[str, list[dict]]:
    personalities = await PersonalityModel.list()
    return {
        "personalities": [personality.model_dump() for personality in personalities]
    }


@blueprint.post("/")
@requires_auth
async def create_personality() -> dict[str, dict]:
    body = await request.get_json()
    payload = CreatePersonality(**body)
    create_params = PersonalityModel.CreateParams(
        name=payload.name,
        description=payload.description,
        context=payload.context,
        memory=payload.memory,
        logo=payload.logo,
        tool_set=payload.tool_set,
    )
    personality = await PersonalityModel.create(params=create_params)
    return {"personality": personality.model_dump()}


@blueprint.put("/<uuid:personality_id>")
@requires_auth
async def update_personality(personality_id: UUID) -> dict[str, dict]:
    body = await request.get_json()
    payload = UpdatePersonality(**body)

    llm: LLM = await ProviderModelModel.get_active_llm()

    # If there is no description, generate one from the context
    description = payload.description
    if (description is None or len(description.strip()) == 0) and len(
        payload.context
    ) > 0:
        description = await ainvoke_description(llm=llm, context=payload.context)

    update_params = PersonalityModel.UpdateParams(
        personality_id=personality_id,
        name=payload.name,
        description=description,
        context=payload.context,
        memory=payload.memory,
        tool_set=payload.tool_set,
        logo=payload.logo,
    )
    personality = await PersonalityModel.update(params=update_params)
    return {"personality": personality.model_dump()}


@blueprint.delete("/<uuid:personality_id>")
@requires_auth
async def delete_personality(personality_id: UUID) -> Response:
    await PersonalityModel.delete(personality_id=personality_id)
    return Response(status=204)


class PostPersonalityContext(BaseModel):
    context: str
    prompt: str


@blueprint.post("/<uuid:personality_id>/context")
@requires_auth
async def post_personality_context(personality_id: UUID) -> dict[str, str]:
    body = await request.get_json()
    payload = PostPersonalityContext(**body)
    llm: LLM = await ProviderModelModel.get_active_llm()
    personality = await PersonalityModel.get(personality_id=personality_id)
    if personality is None:
        raise BadRequest("Personality not found")
    context = await ainvoke_update_personality(
        llm=llm,
        personality=personality,
        context=payload.context,
        prompt=payload.prompt,
    )
    return {"context": context}


def _extract_message_content(message: BaseMessage) -> str:
    """Extract text content from a message, handling both string and structured content."""
    if not isinstance(message.content, str) and isinstance(message.content, list):
        first_content = message.content[0]
        if (
            isinstance(first_content, dict)
            and "text" in first_content
            and isinstance(first_content["text"], str)
        ):
            return first_content["text"].strip()
    return str(message.content).strip()


@blueprint.post("/<uuid:personality_id>/logo")
@requires_auth
async def update_personality_logo(personality_id: UUID) -> dict[str, dict]:
    llm: LLM = await ProviderModelModel.get_active_llm()

    personality = await PersonalityModel.get(personality_id=personality_id)
    if personality is None:
        raise BadRequest("Personality not found")
    graph = create_react_agent(
        model=llm.model,
        prompt=personality_update_logo_prompt,
        tools=[ReplicateImageGenerationTool(), AppImageTool()],
    )
    assert isinstance(request.token, TokenPayload)
    response = await graph.ainvoke(
        input={
            "messages": [
                HumanMessage(
                    content="""Update the logo. Your text response will be shown as
                    a description in a toast letting the user know the logo has been
                    updated. Use the personality as custom instructions on how to
                    write the message. Response from their perspective. Keep it
                    short and concise.
                    """.strip(),
                ),
            ],
            "name": personality.name,
            "personality": personality.description,
        },
        config={
            "configurable": {
                "personality_id": str(personality_id),
                "user_id": request.token.user_id,
            },
        },
    )
    updated_personality = await PersonalityModel.get(personality.id)
    if personality.logo == updated_personality.logo:
        raise BadRequest("Logo not updated")

    return {
        "personalities": [updated_personality.model_dump()],
        "logo": updated_personality.logo,
        "response": _extract_message_content(response["messages"][-1]),
    }
