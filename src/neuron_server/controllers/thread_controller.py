import asyncio
from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint, Response, request
from werkzeug.exceptions import BadRequest, NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.message_controller import process_message_request
from neuron_server.event_router import EventRouter
from neuron_server.llms import agent
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.thread_model import ThreadModel

blueprint = Blueprint("thread", __name__)
router = EventRouter()


class UpdateThread(BaseModel):
    name: str
    context: str
    memory: str
    status: str


@blueprint.get("/<uuid:thread_id>")
@requires_auth
async def get_thread(thread_id: UUID) -> dict[str, list[dict]]:
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread or thread.user_id != request.token.user_id:
        raise NotFound("Thread not found")
    return {"threads": [thread.model_dump()]}


@blueprint.get("/personality/<uuid:personality_id>")
@requires_auth
async def get_threads(personality_id: UUID) -> dict[str, list[dict]]:
    threads = await ThreadModel.list(
        personality_id=personality_id,
        user_id=request.token.user_id
    )
    return {"threads": [thread.model_dump() for thread in threads]}


@blueprint.get("/recent")
@requires_auth
async def get_recent_threads() -> dict[str, list[dict]]:
    threads = await ThreadModel.get_recent_threads(
        hours=24,
        user_id=request.token.user_id
    )
    personality_ids = {thread.personality_id for thread in threads}
    personalities = await PersonalityModel.get_many(personality_ids)
    return {
        "threads": [thread.model_dump() for thread in threads],
        "personalities": [personality.model_dump() for personality in personalities],
    }


@blueprint.post("/")
@requires_auth
async def post_create_thread() -> dict[str, dict]:
    files = await request.files
    form = await request.form
    personality_id = form.get("personality_id")
    if not personality_id:
        raise BadRequest("personality_id is required")

    personality = await PersonalityModel.get(personality_id=UUID(personality_id))
    if not personality:
        raise BadRequest("Personality not found")

    # Create thread
    create_params = ThreadModel.CreateParams(
        personality_id=personality.id,
        user_id=request.token.user_id,
        name=form.get("name", ""),
        context=form.get("context", ""),
        memory=form.get("memory", ""),
        status="idle",
    )
    thread = await ThreadModel.create(params=create_params)

    # Check if we should start with a greeting
    greeting = str(form.get("greeting", "false")).lower() == "true"
    prompt: str | None = None
    if greeting:
        prompt = (
            "<|AI|>\nStart the conversation in a sentence or two and then "
            "provide some prompt suggestions as a list. Don't run any tools\n<|AI|>"
        )
    else:
        prompt = await process_message_request(files, form)

    if prompt and len(prompt.strip()) > 0:
        # Start the conversation and stream the response in the background
        asyncio.create_task(
            agent.astream(
                thread_id=thread.id,
                personality_id=personality.id,
                user_id=request.token.user_id,
                username=request.token.nickname,
                prompt=prompt,
            )
        )
        thread.message_count = 1
        await thread.save()

    return {"thread": thread.model_dump()}


@blueprint.delete("/<uuid:thread_id>")
@requires_auth
async def delete_thread(thread_id: UUID) -> Response:
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread or thread.user_id != request.token.user_id:
        raise NotFound("Thread not found")
    await ThreadModel.delete(thread_id=thread_id)
    return Response(status=204)


@blueprint.put("/<uuid:thread_id>")
@requires_auth
async def update_thread(thread_id: UUID) -> dict[str, list[dict]]:
    body = await request.get_json()
    payload = UpdateThread(**body)
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread or thread.user_id != request.token.user_id:
        raise NotFound("Thread not found")

    update_params = ThreadModel.UpdateParams(
        thread_id=thread_id,
        name=payload.name,
        context=payload.context,
        memory=payload.memory,
        status=payload.status,
        message_count=thread.message_count
    )
    thread = await ThreadModel.update(params=update_params)
    return {"threads": [thread.model_dump()]}
