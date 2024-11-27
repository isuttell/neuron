from neuron_server.logger import logger
from typing import List, TypedDict, Optional
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.event_router import ErrorEvent
from neuron_server.models.personality_model import PersonalityModel
from uuid import UUID, uuid4
from langchain_core.messages import HumanMessage, AIMessage
from datetime import datetime, timezone
from neuron_server.llms.message import get_message_content
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from neuron_server.database import pool
from neuron_server.llms.llm import LLM
from neuron_server.models.thread_model import ThreadModel
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from neuron_server.pubsub import pubsub
from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessageEvent,
    PartialMessage,
    ThreadMessage,
)
import asyncio
from neuron_server.controllers.events.thread_events import GetThreadResponse

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}


class ThreadConfig(TypedDict):
    thread_id: str


class AgentConfig(TypedDict):
    run_name: str
    configurable: ThreadConfig


async def execute_agent(
    prompt: str,
    config: AgentConfig,
    personality_id: UUID,
) -> str:

    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    llm: LLM = ProviderModelModel.get_llm()
    personality = await PersonalityModel.get(personality_id)
    if personality is None:
        raise Exception("Personality not found")

    llm.executor.checkpointer = checkpointer

    result: AIMessage = await llm.executor.ainvoke(
        {
            "messages": [
                HumanMessage(content=prompt),
            ],
            "personality": personality.context,
            "memory": personality.memory,
            "now": datetime.now(timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S"),
        },
        config=config,
    )
    result: AIMessage = result["messages"][-1]
    assert isinstance(result, AIMessage)
    content = (get_message_content(result) or "").strip()
    logger.debug(f"Agent {config['run_name']} returned: {content}")
    return content


async def aget_state(thread_id: UUID):
    await pool.open(wait=True)
    checkpointer = AsyncPostgresSaver(pool)
    llm: LLM = ProviderModelModel.get_llm()
    return await llm.aget_state(
        {"configurable": {"thread_id": str(thread_id)}}, checkpointer=checkpointer
    )


async def save_thread(thread: ThreadModel):
    async def task():
        await thread.save()
        await pubsub.publish("app", GetThreadResponse(thread=thread))

    asyncio.create_task(task())


async def update_thread_status(thread: ThreadModel, status: str):
    if thread.status != status:
        thread.status = status
        await save_thread(thread)


async def astream(thread_id: UUID, personality_id: UUID, prompt: str):
    start_time = datetime.now(timezone.utc).astimezone()
    try:
        await pool.open(wait=True)
        thread = await ThreadModel.get(thread_id)
        if not thread:
            raise Exception("Thread not found")
        await update_thread_status(thread, "thinking")

        personality = await PersonalityModel.get(personality_id)
        if personality is None:
            raise Exception("Personality not found")

        llm: LLM = ProviderModelModel.get_llm()
        llm.executor.checkpointer = AsyncPostgresSaver(pool)

        human_message = HumanMessage(content=prompt, id=str(uuid4()))
        await pubsub.publish(
            "app",
            MessageEvent(
                message=ThreadMessage(
                    **human_message.model_dump(),
                    thread_id=thread.id,
                )
            ),
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
                    await pubsub.publish(
                        "app",
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
                        ),
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
                await pubsub.publish("app", MessageEvent(message=message))
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
        await pubsub.publish("app", ErrorEvent(message=str(e)))
    finally:
        state = await aget_state(thread_id=thread_id)
        thread.message_count = len(state.values.get("messages", []))
        thread.status = "idle"
        await save_thread(thread)
        logger.debug(f"Agent completed for {thread.id}")
        last_message: Optional[AIMessage] = state.values.get("messages", [])[-1]
        if not last_message:
            return None
        return get_message_content(last_message)
