from neuron_server.models import ThreadModel, MessageModel, PersonalityModel
from quart import websocket
from neuron_server.event_router import EventRouter, ErrorEvent
from neuron_server.controllers.events.thread_events import (
    GetThread,
    GetThreads,
    DeleteThread,
    CreateThread,
    GetThreadResponse,
    ThreadExtended,
    UpdateThread,
)
from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessageEvent,
    PartialMessage,
)
from langchain_core.messages import SystemMessage, HumanMessage
from neuron_server.llms.providers import get_provider
from neuron_server.llms.clean_eos_tokens import clean_eos_tokens

router = EventRouter()


@router.on(GetThread)
async def get_thread(event: GetThread):
    thread = ThreadModel.get(event.thread_id)
    if not thread:
        await websocket.send(ErrorEvent(message="Thread not found").model_dump_json())
        return

    message_count = MessageModel.count(thread_id=event.thread_id)
    response = ThreadExtended(**thread.model_dump(), message_count=message_count)

    await websocket.send(GetThreadResponse(thread=response).model_dump_json())


@router.on(GetThreads)
async def get_threads(event: GetThreads):
    for thread in ThreadModel.list(personality_id=event.personality_id):
        message_count = MessageModel.count(thread_id=thread.id)
        response = ThreadExtended(**thread.model_dump(), message_count=message_count)
        await websocket.send(GetThreadResponse(thread=response).model_dump_json())


@router.on(CreateThread)
async def create_thread(event: CreateThread):
    personality = PersonalityModel.get(event.personality_id)
    thread = ThreadModel.create(
        personality_id=personality.id,
        name=event.name,
        context=event.context,
        status="thinking",
    )
    response = ThreadExtended(**thread.model_dump())
    await websocket.send(GetThreadResponse(thread=response).model_dump_json())

    system_prompts = [
        prompt
        for prompt in [personality.get_context_prompt(), thread.get_context_prompt()]
        if prompt
    ]
    system_prompt = "\n".join(system_prompts) if system_prompts else None
    message = MessageModel.create(thread_id=thread.id, role="ai", content="")
    await websocket.send(
        PartialMessageEvent(
            message=PartialMessage(
                id=message.id,
                index=0,
                role=message.role,
                content=message.content,
                thread_id=thread.id,
                status="streaming",
            )
        ).model_dump_json()
    )
    provider = get_provider(event.provider_id)
    greeting = await provider.model.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content="Write a short welcome greeting message for the user to start the conversation and prompt next steps."
            ),
        ],
        {"run_name": "greeting", "metadata": {"thread_id": thread.id}},
    )
    MessageModel.update(id=message.id, content=clean_eos_tokens(greeting.content))
    await websocket.send(MessageEvent(message=message).model_dump_json())
    thread.status = "idle"
    thread.save()
    message_count = MessageModel.count(thread_id=thread.id)
    response = ThreadExtended(**thread.model_dump(), message_count=message_count)
    await websocket.send(GetThreadResponse(thread=response).model_dump_json())


@router.on(DeleteThread)
async def delete_thread(event: DeleteThread):
    ThreadModel.delete(event.thread_id)


@router.on(UpdateThread)
async def update_thread(event: UpdateThread):
    thread = ThreadModel.update(event.thread_id, event.name, event.context)
    message_count = MessageModel.count(thread_id=thread.id)
    response = ThreadExtended(**thread.model_dump(), message_count=message_count)
    await websocket.send(GetThreadResponse(thread=response).model_dump_json())
