from quart import websocket
from neuron_server.event_router import EventRouter, ErrorEvent
from neuron_server.models import ThreadModel, MessageModel
from neuron_server.controllers.events.message_events import (
    GetThreadMessages,
    MessageEvent,
    PostMessage,
)
from neuron_server.llms.message import ainvoke

router = EventRouter()


@router.on(GetThreadMessages)
async def get_thread_messages(event: GetThreadMessages):
    thread = await ThreadModel.get(event.thread_id)
    if not thread:
        await websocket.send(ErrorEvent(message="Thread not found").model_dump_json())
        return

    messages = [
        message
        for message in await MessageModel.list(thread.id)
        if isinstance(message.content, str) and len(message.content) > 0
    ]
    for message in messages:
        await websocket.send(MessageEvent(message=message).model_dump_json())


@router.on(PostMessage)
async def post_message(event: PostMessage):
    return await ainvoke(
        event.thread_id, event.prompt, event.personality_id, event.provider_id
    )
