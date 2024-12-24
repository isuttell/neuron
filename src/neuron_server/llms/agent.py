from neuron_server.logger import logger
from typing import List, TypedDict, Optional, Set, Dict
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
from neuron_server.pubsub import client as pubsub_client, pubsub
from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessageEvent,
    PartialMessage,
    ThreadMessage,
)
import asyncio
from neuron_server.controllers.events.thread_events import GetThreadResponse
from werkzeug.exceptions import BadRequest
from neuron_server.llms.tools import get_tools

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}


class ThreadConfig(TypedDict):
    thread_id: str


async def execute_agent(
    prompt: str,
    personality_id: UUID,
    location: str = "San Diego, California at -117.1860 W and 32.84 N.",
) -> str:
    personality = await PersonalityModel.get(personality_id)
    if personality is None:
        raise BadRequest("Personality not found")

    llm: LLM = ProviderModelModel.get_llm()
    tools = get_tools(personality.tool_set) if personality.tool_set else None
    graph = llm.create_workflow(tools)
    graph.checkpointer = None
    result: AIMessage = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(content=prompt),
            ],
            "location": location,
            "personality": personality.context,
            "memory": personality.memory,
            "now": datetime.now(timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S %Z"),
        },
        config={
            "run_name": "home_prompt",
            "configurable": {
                "personality_id": str(personality_id),
            },
        },
    )
    result: AIMessage = result["messages"][-1]
    assert isinstance(result, AIMessage)
    return (get_message_content(result) or "").strip()


async def aget_state(thread_id: UUID):
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
        # logger.debug(f"Updated thread status: {thread.id} {status}")
        await save_thread(thread)


async def astream(
    thread_id: UUID,
    personality_id: UUID,
    prompt: str,
    location: str = "San Diego, California at -117.1860 W and 32.84 N.",
):
    start_time = datetime.now(timezone.utc).astimezone()
    logger.debug(f"Agent started for {thread_id}")
    try:
        thread = await ThreadModel.get(thread_id)
        if not thread:
            raise Exception("Thread not found")
        await update_thread_status(thread, "thinking")

        personality = await PersonalityModel.get(personality_id)
        if personality is None:
            raise Exception("Personality not found")

        llm: LLM = ProviderModelModel.get_llm()
        tools = get_tools(personality.tool_set) if personality.tool_set else None
        graph = llm.create_workflow(tools)
        graph.checkpointer = AsyncPostgresSaver(pool)

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
        active_runs: Dict[str, str] = {}
        async for body in graph.astream_events(
            {
                "messages": [
                    human_message,
                ],
                "personality": personality.context,
                "title": thread.name or "",
                "location": location,
                "now": start_time.strftime("%Y-%m-%d %H:%M:%S %Z"),
            },
            config={
                "run_name": "message",
                "configurable": {
                    "thread_id": str(thread.id),
                    "personality_id": str(personality_id),
                },
            },
            version="v2",
        ):
            kind: str = body["event"]
            name: str = body["name"]
            data: dict = body["data"]
            run_id: str = body["run_id"]
            # logger.debug(f"Received event: {kind} {name}")

            if kind in ["on_chain_start", "on_chain_end"] and name in [
                "update_title",
                "update_memory",
            ]:
                if kind == "on_chain_start":
                    active_runs[run_id] = "thinking" if name == "message" else name
                elif kind == "on_chain_end":
                    del active_runs[run_id]
                values = list(set(active_runs.values()))
                await update_thread_status(
                    thread,
                    ", ".join(values) if len(values) > 0 else "thinking",
                )

            if kind in ["on_tool_start", "on_tool_end"]:
                if kind == "on_tool_start":
                    logger.debug(f"Starting tool {name}...")
                    active_runs[run_id] = (
                        name
                        if name not in ["store_memory", "recall_memory"]
                        else "update_memory"
                    )
                elif kind == "on_tool_end":
                    logger.debug(f"Finished tool {name}...")
                    del active_runs[run_id]
                values = list(set(active_runs.values()))
                await update_thread_status(
                    thread,
                    ", ".join(values) if len(values) > 0 else "thinking",
                )

            if kind == "on_chat_model_stream" and isinstance(data["chunk"], AIMessage):
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
            elif kind == "on_tool_end" and isinstance(data["output"], ToolMessage):
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
                and name == "update_title"
                and isinstance(data["output"], str)
            ):
                thread.name = data["output"]
                await thread.save()
            elif kind == "on_chat_model_end":
                output: AIMessage = data["output"]
                if not "update_title" in active_runs.values():
                    # @TODO: This is a hack
                    message = ThreadMessage(
                        **output.model_dump(),
                        thread_id=thread.id,
                    )
                    await pubsub.publish("app", MessageEvent(message=message))
                await update_thread_status(thread, "thinking")
            elif kind == "error":
                logger.error(data)

        await update_thread_status(thread, "idle")
    except Exception as e:
        logger.exception(e)
        logger.error(f"AgentError: {e!r}")
        thread.status = "error"
        await save_thread(thread)
        await pubsub.publish("app", ErrorEvent(message=str(e)))
    finally:
        state = await aget_state(thread_id=thread_id)
        thread.message_count = len(state.values.get("messages", []))
        thread.status = "idle"
        await save_thread(thread)
        logger.debug(f"Agent completed for {thread.id}")
        last_message: Optional[AIMessage] = (
            state.values.get("messages", [])[-1]
            if len(state.values.get("messages", [])) > 0
            else None
        )
        if not last_message:
            return None
        return get_message_content(last_message)
