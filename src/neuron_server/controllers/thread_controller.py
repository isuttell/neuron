from neuron_server.models import ThreadModel, MessageModel, PersonalityModel
from quart import websocket, Blueprint, request
from neuron_server.event_router import EventRouter, ErrorEvent
from neuron_server.controllers.events.thread_events import (
    GetThread,
    GetThreads,
    DeleteThread,
    CreateThread,
    GetThreadResponse,
    UpdateThread,
)
from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessageEvent,
    PartialMessage,
)
from langchain_core.messages import SystemMessage, HumanMessage
from neuron_server.llms.clean_eos_tokens import clean_eos_tokens
from neuron_server.models.provider_model import ProviderModelModel
from uuid import UUID
from neuron_server.controllers.message_controller import aget_state


router = EventRouter()
blueprint = Blueprint("thread", __name__)


@router.on(GetThread)
async def handle_get_thread(event: GetThread):
    thread = await ThreadModel.get(event.thread_id)
    if not thread:
        await websocket.send(ErrorEvent(message="Thread not found").model_dump_json())
        return

    thread.message_count = await MessageModel.count(thread_id=event.thread_id)

    await websocket.send(GetThreadResponse(thread=thread).model_dump_json())


@blueprint.get("/<uuid:thread_id>")
async def get_thread(thread_id: UUID):
    thread = await ThreadModel.get(thread_id)
    if not thread:
        raise ValueError("Thread not found")
    return {
        "thread": thread.model_dump(),
    }


@router.on(GetThreads)
async def handle_get_threads(event: GetThreads):
    for thread in await ThreadModel.list(personality_id=event.personality_id):
        await websocket.send(GetThreadResponse(thread=thread).model_dump_json())


@blueprint.get("/personality/<uuid:personality_id>")
async def get_threads(personality_id: UUID):
    threads = await ThreadModel.list(personality_id=personality_id)
    return {
        "threads": [thread.model_dump() for thread in threads],
    }


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

    return {
        "thread": thread.model_dump(),
    }


@router.on(DeleteThread)
async def delete_thread(event: DeleteThread):
    await ThreadModel.delete(event.thread_id)


@router.on(UpdateThread)
async def update_thread(event: UpdateThread):
    thread = await ThreadModel.update(event.thread_id, event.name, event.context)
    thread.message_count = await MessageModel.count(thread_id=thread.id)
    await websocket.send(GetThreadResponse(thread=thread).model_dump_json())
