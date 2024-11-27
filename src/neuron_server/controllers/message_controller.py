from quart import websocket, request, Blueprint
from neuron_server.event_router import EventRouter, ErrorEvent
from neuron_server.models import ThreadModel
from neuron_server.controllers.events.message_events import (
    GetThreadMessages,
    MessageEvent,
    PostMessage,
)
from neuron_server.logger import logger
from pydantic import BaseModel
import asyncio
from neuron_server.controllers.events.thread_events import (
    GetThreadResponse,
)
from neuron_server.logger import logger
from typing import List
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.personality_model import PersonalityModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from datetime import datetime, timezone
from neuron_server.llms.message import get_message_content
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from neuron_server.database import DB_URI, pool
from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessageEvent,
    PartialMessage,
    ThreadMessage,
)
from uuid import UUID, uuid4
from neuron_server.llms.agent import aget_state

router = EventRouter()

blueprint = Blueprint("message", __name__)


async def send_message(message: BaseModel):
    asyncio.create_task(websocket.send(message.model_dump_json()))


@router.on(GetThreadMessages)
async def handle_get_thread_messages(event: GetThreadMessages):
    thread = await ThreadModel.get(event.thread_id)
    if not thread:
        await websocket.send(ErrorEvent(message="Thread not found").model_dump_json())
        return

    state = await aget_state(thread_id=event.thread_id, provider_id=event.provider_id)

    messages = [
        ThreadMessage(**message.model_dump(), thread_id=thread.id)
        for message in (state.values.get("messages", []))
        if message.type != "system"
    ]
    for message in messages:
        await send_message(MessageEvent(message=message))


@blueprint.get("/thread/<uuid:thread_id>")
async def get_thread_messages(event: GetThreadMessages):
    thread = await ThreadModel.get(event.thread_id)
    if not thread:
        await websocket.send(ErrorEvent(message="Thread not found").model_dump_json())
        return

    state = await aget_state(thread_id=event.thread_id, provider_id=event.provider_id)

    messages = [
        ThreadMessage(**message.model_dump(), thread_id=thread.id)
        for message in (state.values.get("messages", []))
        if message.type != "system"
    ]
    for message in messages:
        await send_message(MessageEvent(message=message))


async def save_thread(thread: ThreadModel):
    async def task():
        await thread.save()
        await send_message(GetThreadResponse(thread=thread))

    asyncio.create_task(task())


async def update_thread_status(thread: ThreadModel, status: str):
    if thread.status != status:
        thread.status = status
        await save_thread(thread)


@router.on(PostMessage)
async def post_message(event: PostMessage) -> None:
    start_time = datetime.now(timezone.utc).astimezone()
    try:

        thread = await ThreadModel.get(event.thread_id)
        if not thread:
            raise Exception("Thread not found")
        await update_thread_status(thread, "thinking")

        provider = await ProviderModelModel.get(event.provider_id)
        if provider is None:
            raise Exception("Provider not found")
        llm = provider.to_llm()
        personality = await PersonalityModel.get(event.personality_id)
        if personality is None:
            raise Exception("Personality not found")

        llm.executor.checkpointer = AsyncPostgresSaver(pool)

        human_message = HumanMessage(content=event.prompt, id=str(uuid4()))
        await send_message(
            MessageEvent(
                message=ThreadMessage(
                    **human_message.model_dump(),
                    thread_id=thread.id,
                )
            )
        )

        index = -1
        async for body in llm.executor.astream_events(
            {
                "messages": [
                    human_message,
                ],
                "personality": personality.context,
                "memory": personality.memory or "",
                "title": thread.name or "",
                "now": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            config={
                "run_name": "message",
                "configurable": {
                    "thread_id": str(thread.id),
                },
            },
            version="v2",
        ):
            kind: str = body["event"]
            name: str = body["name"]
            data: dict = body["data"]
            run_id: str = body["run_id"]
            # logger.debug(f"Received event: {kind} {name}")

            if kind == "on_chain_start" and name == "update_title":
                await update_thread_status(thread, "idle")
            elif kind == "on_chat_model_stream" and isinstance(
                data["chunk"], AIMessage
            ):
                chunk = data["chunk"]
                content = get_message_content(chunk)
                if (
                    isinstance(content, str)
                    and len(content) > 0
                    and body["metadata"]["langgraph_node"] == "agent"
                ):
                    await update_thread_status(thread, "streaming")
                    index += 1
                    await send_message(
                        PartialMessageEvent(
                            message=PartialMessage(
                                id=run_id,
                                type="ai",
                                content=content,
                                thread_id=thread.id,
                                index=index,
                                status="streaming",
                                # Use a stable start time and don't create a new one per event
                                created_at=start_time,
                            )
                        )
                    )
            elif kind == "on_tool_start":
                await update_thread_status(thread, "tools")
                logger.debug(
                    f"Starting tool: {body['name']} with inputs: {body['data'].get('input')}"
                )
            elif kind == "on_tool_end":
                output: ToolMessage = data["output"]
                message = ThreadMessage(
                    **output.model_dump(),
                    thread_id=thread.id,
                )
                if not message.id:
                    message.id = run_id
                await send_message(MessageEvent(message=message))
            elif (
                kind == "on_chain_end"
                and name == "update_memory"
                and isinstance(data["output"], str)
            ):
                personality.memory = data["output"]
                logger.debug(f"Updated memory: {personality.memory}")
                await personality.save()
            elif (
                kind == "on_chain_end"
                and name == "update_title"
                and isinstance(data["output"], str)
            ):
                thread.name = data["output"]
                logger.debug(f"Updated title: {thread.name}")
                await thread.save()

        await update_thread_status(thread, "idle")
    except Exception as e:
        logger.exception(e)
        await websocket.send(ErrorEvent(message=str(e)).model_dump_json())
    finally:
        state = await aget_state(
            thread_id=event.thread_id, provider_id=event.provider_id
        )
        thread.message_count = len(state.values.get("messages", []))
        thread.status = "idle"
        await save_thread(thread)
        logger.debug(f"Agent completed for {thread.id}")
