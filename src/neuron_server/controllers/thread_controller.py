from neuron_server.models import ThreadModel, PersonalityModel
from quart import Blueprint, request, Response
from neuron_server.event_router import EventRouter
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from neuron_server.llms.agent import astream
import asyncio
from werkzeug.exceptions import BadRequest

router = EventRouter()
blueprint = Blueprint("thread", __name__)


@blueprint.get("/<uuid:thread_id>")
async def get_thread(thread_id: UUID):
    thread = await ThreadModel.get(thread_id)
    if not thread:
        raise BadRequest("Thread not found")
    return {
        "thread": thread.model_dump(),
    }


@blueprint.get("/personality/<uuid:personality_id>")
async def get_threads(personality_id: UUID):
    threads = await ThreadModel.list(personality_id=personality_id)
    return {
        "threads": [thread.model_dump() for thread in threads],
    }


class CreateThread(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None
    greeting: Optional[bool] = None
    prompt: Optional[str] = None
    personality_id: UUID


@blueprint.post("/")
async def post_create_thread():

    data = await request.get_json()
    body = CreateThread(**data)
    personality = await PersonalityModel.get(body.personality_id)
    if not personality:
        raise ValueError("Personality not found")

    thread = await ThreadModel.create(
        personality_id=personality.id,
        name=body.name,
        context=body.context,
    )
    # Start the conversation and stream the response
    if body.greeting or body.prompt:
        asyncio.create_task(
            astream(
                prompt=body.prompt
                or f"<|AI|>Start the conversation in a sentence or two. Don't run any tools.<|AI|>",
                personality_id=personality.id,
                thread_id=thread.id,
            )
        )
    return {
        "thread": thread.model_dump(),
    }


@blueprint.delete("/<uuid:thread_id>")
async def delete_thread(thread_id: UUID):
    await ThreadModel.delete(thread_id)
    return Response(status=204)


class UpdateThread(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None


@blueprint.put("/<uuid:thread_id>")
async def update_thread(thread_id: UUID):
    body = await request.get_json()
    payload = UpdateThread(**body)
    thread = await ThreadModel.get(thread_id)
    if not thread:
        raise ValueError("Thread not found")
    thread.name = payload.name
    thread.context = payload.context
    await thread.save()
    return {
        "thread": thread.model_dump(),
    }
