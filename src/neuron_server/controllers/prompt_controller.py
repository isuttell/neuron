from quart import Blueprint, request, Response
from neuron_server.models.prompt_model import PromptModel
from uuid import UUID
from pydantic import BaseModel
from typing import Optional
from neuron_server.event_router import EventRouter
from werkzeug.exceptions import NotFound

router = EventRouter()
blueprint = Blueprint("prompt", __name__)


class CreatePrompt(BaseModel):
    name: str
    text: str
    personality_id: Optional[UUID] = None


class UpdatePrompt(CreatePrompt):
    pass


@blueprint.get("/<uuid:prompt_id>")
async def get_prompt(prompt_id: UUID):
    prompt = await PromptModel.get(prompt_id)
    if not prompt:
        raise NotFound("Prompt not found")
    return {"prompts": [prompt.model_dump()]}


@blueprint.get("/")
async def list_prompts():
    personality_id = request.args.get("personality_id")
    prompts = await PromptModel.list(
        personality_id=UUID(personality_id) if personality_id else None
    )
    return {"prompts": [prompt.model_dump() for prompt in prompts]}


@blueprint.post("/")
async def create_prompt():
    body = await request.get_json()
    payload = CreatePrompt(**body)
    prompt = await PromptModel.create(
        name=payload.name,
        text=payload.text,
        personality_id=payload.personality_id,
    )
    return {"prompts": [prompt.model_dump()]}


@blueprint.put("/<uuid:prompt_id>")
async def update_prompt(prompt_id: UUID):
    body = await request.get_json()
    payload = UpdatePrompt(**body)
    prompt = await PromptModel.get(prompt_id)
    if not prompt:
        raise NotFound("Prompt not found")
    prompt.name = payload.name
    prompt.text = payload.text
    prompt.personality_id = payload.personality_id
    await prompt.save()
    return {"prompts": [prompt.model_dump()]}


@blueprint.delete("/<uuid:prompt_id>")
async def delete_prompt(prompt_id: UUID):
    await PromptModel.delete(prompt_id)
    return Response(status=204)
