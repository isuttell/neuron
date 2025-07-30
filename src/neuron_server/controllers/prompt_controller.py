from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint, Response
from werkzeug.exceptions import Forbidden, NotFound

from neuron_server.controllers.auth import TokenPayload, requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.event_router import EventRouter
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.prompt_model import PromptModel
from neuron_server.type_defs.request_proxy import request

router = EventRouter()
blueprint = Blueprint("prompt", __name__)


class CreatePrompt(BaseModel):
    name: str
    text: str
    personality_id: UUID | None = None


class UpdatePrompt(CreatePrompt):
    pass


@blueprint.get("/<uuid:prompt_id>")
@requires_auth
async def get_prompt(prompt_id: UUID) -> dict[str, list[dict]]:
    prompt = await PromptModel.get(prompt_id=prompt_id)
    if not prompt:
        raise NotFound("Prompt not found")
    return {"prompts": [prompt.model_dump()]}


@blueprint.get("/")
@requires_auth
async def list_prompts() -> dict[str, list[dict]]:
    # Get user from token
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check for personality_id query parameter
    personality_id_param = request.args.get("personality_id")
    requested_personality_id = None
    if personality_id_param:
        try:
            requested_personality_id = UUID(personality_id_param)
        except ValueError as err:
            raise NotFound("Invalid personality ID format") from err

    # First get personalities the user has access to
    accessible_personalities = await PersonalityModel.list_for_user(user_id=user_id)
    accessible_personality_ids = {p.id for p in accessible_personalities}

    # If a specific personality was requested, verify access
    if requested_personality_id:
        if requested_personality_id not in accessible_personality_ids:
            raise Forbidden("You don't have access to this personality")
        # Filter to only the requested personality
        accessible_personalities = [
            p for p in accessible_personalities if p.id == requested_personality_id
        ]
        accessible_personality_ids = {requested_personality_id}

    # Get prompts filtered by accessible personalities
    all_prompts = await PromptModel.list(personality_id=requested_personality_id)
    filtered_prompts = [
        prompt
        for prompt in all_prompts
        if prompt.personality_id is None
        or prompt.personality_id in accessible_personality_ids
    ]

    return {
        "prompts": [prompt.model_dump() for prompt in filtered_prompts],
        "personalities": [
            personality.model_dump() for personality in accessible_personalities
        ],
    }


@blueprint.post("/")
@requires_auth
@requires_csrf
async def create_prompt() -> dict[str, list[dict]]:
    body = await request.get_json()
    payload = CreatePrompt(**body)
    create_params = PromptModel.CreateParams(
        name=payload.name, text=payload.text, personality_id=payload.personality_id
    )
    prompt = await PromptModel.create(params=create_params)
    return {"prompts": [prompt.model_dump()]}


@blueprint.put("/<uuid:prompt_id>")
@requires_auth
@requires_csrf
async def update_prompt(prompt_id: UUID) -> dict[str, list[dict]]:
    body = await request.get_json()
    payload = UpdatePrompt(**body)
    prompt = await PromptModel.get(prompt_id=prompt_id)
    if not prompt:
        raise NotFound("Prompt not found")
    prompt.name = payload.name
    prompt.text = payload.text
    prompt.personality_id = payload.personality_id
    await prompt.save()
    return {"prompts": [prompt.model_dump()]}


@blueprint.delete("/<uuid:prompt_id>")
@requires_auth
@requires_csrf
async def delete_prompt(prompt_id: UUID) -> Response:
    await PromptModel.delete(prompt_id=prompt_id)
    return Response(status=204)
