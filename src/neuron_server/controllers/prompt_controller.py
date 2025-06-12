from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint, Response
from werkzeug.exceptions import NotFound

from neuron_server.controllers.auth import requires_auth
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
    prompts = await PromptModel.list()
    personality_ids = {prompt.personality_id for prompt in prompts}
    personalities = await PersonalityModel.get_many(personality_ids)
    return {
        "prompts": [prompt.model_dump() for prompt in prompts],
        "personalities": [personality.model_dump() for personality in personalities],
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
