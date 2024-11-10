from neuron_server.models import ThreadModel, MessageModel, PersonalityModel
from quart import websocket
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

router = EventRouter()


@router.on(GetThread)
async def get_thread(event: GetThread):
    thread = await ThreadModel.get(event.thread_id)
    if not thread:
        await websocket.send(ErrorEvent(message="Thread not found").model_dump_json())
        return

    thread.message_count = await MessageModel.count(thread_id=event.thread_id)

    await websocket.send(GetThreadResponse(thread=thread).model_dump_json())


@router.on(GetThreads)
async def get_threads(event: GetThreads):
    for thread in await ThreadModel.list(personality_id=event.personality_id):
        thread.message_count = await MessageModel.count(thread_id=thread.id)
        await websocket.send(GetThreadResponse(thread=thread).model_dump_json())


@router.on(CreateThread)
async def create_thread(event: CreateThread):
    personality = await PersonalityModel.get(event.personality_id)
    thread = await ThreadModel.create(
        personality_id=personality.id,
        name=event.name,
        context=event.context,
        status="thinking",
    )
    await websocket.send(GetThreadResponse(thread=thread).model_dump_json())

    system_prompts = [
        prompt
        for prompt in [personality.get_context_prompt(), thread.get_context_prompt()]
        if prompt
    ]
    system_prompt = "\n".join(system_prompts) if system_prompts else None
    message = await MessageModel.create(thread_id=thread.id, role="ai", content="")
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
    provider = await ProviderModelModel.get(event.provider_id)
    if not provider:
        raise ValueError(f"Provider with id {event.provider_id} not found")
    llm = provider.to_llm()
    greeting = await llm.model.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(
                content="Write a couple sentences greeting the user to start the conversation off and prompt next steps."
            ),
        ],
        {"run_name": "greeting", "metadata": {"thread_id": thread.id}},
    )
    await MessageModel.update(id=message.id, content=clean_eos_tokens(greeting.content))
    await websocket.send(MessageEvent(message=message).model_dump_json())
    thread.status = "idle"
    await thread.save()
    thread.message_count = await MessageModel.count(thread_id=thread.id)
    await websocket.send(GetThreadResponse(thread=thread).model_dump_json())


@router.on(DeleteThread)
async def delete_thread(event: DeleteThread):
    await ThreadModel.delete(event.thread_id)


@router.on(UpdateThread)
async def update_thread(event: UpdateThread):
    thread = await ThreadModel.update(event.thread_id, event.name, event.context)
    thread.message_count = await MessageModel.count(thread_id=thread.id)
    await websocket.send(GetThreadResponse(thread=thread).model_dump_json())
