import re
from uuid import UUID

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from quart import Blueprint, Response, request
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

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
from neuron_server.models.personality_user_model import PersonalityUserModel
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.user_model import UserModel

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


class PersonalityUserPayload(BaseModel):
    user_id: str
    role: str = "user"


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
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )
    return {"personality": personality.model_dump()}


@blueprint.get("/<uuid:personality_id>/embeddings")
@requires_auth
async def get_personality_embeddings(personality_id: UUID) -> dict[str, list[dict]]:
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

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
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )
    if not has_admin:
        raise Forbidden(
            "You do not have permission to delete embeddings for this personality"
        )

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
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )
    if not has_admin:
        raise Forbidden(
            "You do not have permission to delete embeddings for this personality"
        )

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
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Get personalities the user has access to
    personalities = await PersonalityModel.list_for_user(user_id=user_id)
    return {
        "personalities": [personality.model_dump() for personality in personalities]
    }


@blueprint.post("/")
@requires_auth
async def create_personality() -> dict[str, dict]:
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    body = await request.get_json()
    payload = CreatePersonality(**body)
    create_params = PersonalityModel.CreateParams(
        name=payload.name,
        description=payload.description,
        context=payload.context,
        memory=payload.memory,
        logo=payload.logo,
        tool_set=payload.tool_set,
        creator_id=user_id,  # Pass the creator_id
    )
    personality = await PersonalityModel.create(params=create_params)
    return {"personality": personality.model_dump()}


@blueprint.put("/<uuid:personality_id>")
@requires_auth
async def update_personality(personality_id: UUID) -> dict[str, dict]:
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )
    if not has_admin:
        raise Forbidden("You do not have permission to update this personality")

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
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )
    if not has_admin:
        raise Forbidden("You do not have permission to delete this personality")

    await PersonalityModel.delete(personality_id=personality_id)
    return Response(status=204)


@blueprint.get("/<uuid:personality_id>/users")
@requires_auth
async def get_personality_users(personality_id: UUID) -> dict[str, list[dict]]:
    """Get all users associated with a personality.

    Args:
        personality_id: The ID of the personality to get users for

    Returns:
        A dictionary with a list of user objects including their roles

    Raises:
        Forbidden: If the user doesn't have admin access to the personality
        NotFound: If the personality doesn't exist
    """
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )
    if not has_admin:
        raise Forbidden("You do not have permission to view users for this personality")

    # Check if personality exists
    personality = await PersonalityModel.get(personality_id=personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")

    # Get all users with access to the personality
    personality_users = await PersonalityUserModel.get_personality_users(
        personality_id=personality_id
    )

    # Get full user details for each user
    user_ids = [pu.user_id for pu in personality_users]
    users = await UserModel.get_by_ids(user_ids=user_ids)

    # Add role to each user
    result = []
    for user in users:
        user_dict = user.model_dump()
        # Find role from personality_users
        for pu in personality_users:
            if pu.user_id == user.id:
                user_dict["role"] = pu.role
                break
        result.append(user_dict)

    return {"users": result}


@blueprint.post("/<uuid:personality_id>/users")
@requires_auth
async def add_personality_user(personality_id: UUID) -> dict[str, dict]:
    """Add a user to a personality.

    Args:
        personality_id: The ID of the personality to add the user to

    Returns:
        A dictionary with the created personality user

    Raises:
        Forbidden: If the user doesn't have admin access to the personality
        NotFound: If the personality or user doesn't exist
        BadRequest: If the user is already associated with the personality
    """
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    body = await request.get_json()
    payload = PersonalityUserPayload(**body)

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )
    if not has_admin:
        raise Forbidden("You do not have permission to add users to this personality")

    # Check if personality exists
    personality = await PersonalityModel.get(personality_id=personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")

    # Check if user exists
    users = await UserModel.get_by_ids(user_ids=[payload.user_id])
    if not users:
        raise NotFound(f"User with id {payload.user_id} not found")

    # Check if user is already associated with the personality
    existing = await PersonalityUserModel.get(
        personality_id=personality_id, user_id=payload.user_id
    )
    if existing:
        raise BadRequest("User is already associated with this personality")

    # Add user to personality
    await PersonalityModel.add_user(
        personality_id=personality_id,
        user_id=payload.user_id,
        role=payload.role,
    )

    # Get the created personality user
    personality_user = await PersonalityUserModel.get(
        personality_id=personality_id, user_id=payload.user_id
    )
    if not personality_user:
        raise BadRequest("Failed to add user to personality")

    return {"personality_user": personality_user.model_dump()}


@blueprint.put("/<uuid:personality_id>/users/<string:user_id>")
@requires_auth
async def update_personality_user(
    personality_id: UUID, user_id: str
) -> dict[str, dict]:
    """Update a user's role for a personality.

    Args:
        personality_id: The ID of the personality
        user_id: The ID of the user to update

    Returns:
        A dictionary with the updated personality user

    Raises:
        Forbidden: If the user doesn't have admin access to the personality
        NotFound: If the personality or user doesn't exist
        BadRequest: If the user is not associated with the personality
    """
    assert isinstance(request.token, TokenPayload)
    requester_id = request.token.user_id

    body = await request.get_json()
    payload = PersonalityUserPayload(**body)

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=requester_id
    )
    if not has_admin:
        raise Forbidden(
            "You do not have permission to update user roles for this personality"
        )

    # Check if personality exists
    personality = await PersonalityModel.get(personality_id=personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")

    # Check if user is associated with the personality
    existing = await PersonalityUserModel.get(
        personality_id=personality_id, user_id=user_id
    )
    if not existing:
        raise NotFound(
            f"User with id {user_id} is not associated with this personality"
        )

    # Update user role
    try:
        personality_user = await PersonalityUserModel.update_role(
            personality_id=personality_id, user_id=user_id, role=payload.role
        )
    except ValueError as err:
        raise BadRequest(f"Failed to update user role: {str(err)}") from err

    return {"personality_user": personality_user.model_dump()}


@blueprint.delete("/<uuid:personality_id>/users/<string:user_id>")
@requires_auth
async def remove_personality_user(personality_id: UUID, user_id: str) -> Response:
    """Remove a user from a personality.

    Args:
        personality_id: The ID of the personality
        user_id: The ID of the user to remove

    Returns:
        204 No Content

    Raises:
        Forbidden: If the user doesn't have admin access to the personality
        NotFound: If the personality doesn't exist
        BadRequest: If trying to remove the last admin
    """
    assert isinstance(request.token, TokenPayload)
    requester_id = request.token.user_id

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=requester_id
    )
    if not has_admin:
        raise Forbidden(
            "You do not have permission to remove users from this personality"
        )

    # Check if personality exists
    personality = await PersonalityModel.get(personality_id=personality_id)
    if not personality:
        raise NotFound(f"Personality with id {personality_id} not found")

    # Get all users with admin role
    personality_users = await PersonalityUserModel.get_personality_users(
        personality_id=personality_id
    )
    admin_users = [pu for pu in personality_users if pu.role == "admin"]

    # Check if trying to remove the last admin
    if len(admin_users) == 1 and admin_users[0].user_id == user_id:
        raise BadRequest("Cannot remove the last admin from a personality")

    # Remove user from personality
    await PersonalityModel.remove_user(personality_id=personality_id, user_id=user_id)

    return Response(status=204)


class PostPersonalityContext(BaseModel):
    context: str
    prompt: str


@blueprint.post("/<uuid:personality_id>/context")
@requires_auth
async def post_personality_context(personality_id: UUID) -> dict[str, str]:
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )
    if not has_admin:
        raise Forbidden(
            "You do not have permission to update this personality's context"
        )

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
    """Extract text content from a message handling both string and
    structured content."""
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
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has admin access
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )
    if not has_admin:
        raise Forbidden("You do not have permission to update this personality's logo")

    llm: LLM = await ProviderModelModel.get_active_llm()

    personality = await PersonalityModel.get(personality_id=personality_id)
    if personality is None:
        raise BadRequest("Personality not found")

    graph = create_react_agent(
        model=llm.model,
        prompt=personality_update_logo_prompt,
        tools=[ReplicateImageGenerationTool(), AppImageTool()],
    )

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
                "user_id": user_id,
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
