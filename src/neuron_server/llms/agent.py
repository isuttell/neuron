from neuron_server.logger import logger
from typing import List, TypedDict, Optional, Set, Dict, Any, Callable
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
    user_id: str = "auth0|677842260dc433462eaf13a6",
    username: str = "Isaac",
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
                HumanMessage(
                    content="I can't respond so please try you're best to fullful my next request but don't ask questions, or provide prompt suggestions. Just respond with the answer to my question."
                ),
                HumanMessage(content=prompt),
            ],
            "location": location,
            "username": username,
            "personality": personality.context,
            "now": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        config={
            "configurable": {
                "personality_id": str(personality_id),
                "user_id": str(user_id),
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


class Debouncer:
    def __init__(self, wait: float):
        self.wait = wait  # seconds
        self.task: Optional[asyncio.Task] = None
        self._future: Optional[asyncio.Future] = None
        self._next_args: Optional[tuple] = None
        self._next_kwargs: Optional[dict] = None
        self._coro_func: Optional[Callable] = None

    async def call(self, coro_func: Callable, *args, **kwargs):
        """
        Schedule a coroutine function to be executed with debouncing

        Args:
            coro_func: The async function to call
            *args: Positional arguments for the coroutine
            **kwargs: Keyword arguments for the coroutine
        """
        self._coro_func = coro_func
        self._next_args = args
        self._next_kwargs = kwargs

        if self.task and not self.task.done():
            if self._future:
                await self._future
            return

        self._future = asyncio.Future()
        self.task = asyncio.create_task(self._handle())
        await self._future

    async def _handle(self):
        try:
            await asyncio.sleep(self.wait)
            if (
                self._coro_func
                and self._next_args is not None
                and self._next_kwargs is not None
            ):
                await self._coro_func(*self._next_args, **self._next_kwargs)
        finally:
            if self._future and not self._future.done():
                self._future.set_result(None)
            self._coro_func = None
            self._next_args = None
            self._next_kwargs = None
            self._future = None


# Initialize a debouncer with a 100ms wait time
debounce_publish = Debouncer(wait=0.1)


async def _debounced_publish(channel: str, event: Any):
    """Debounces pubsub publishes to limit frequency."""
    await debounce_publish.call(pubsub.publish, channel, event)


async def update_thread_status(
    thread: ThreadModel, status: str, force_update: bool = True
):
    if thread.status != status or force_update:
        thread.status = status

        async def task():
            await ThreadModel.set(thread.id, "status", status)
            await _debounced_publish("app", GetThreadResponse(thread=thread))

        asyncio.create_task(task())


async def astream(
    thread_id: UUID,
    personality_id: UUID,
    user_id: UUID,
    username: str,
    prompt: str,
    location: str = "San Diego, California at -117.1860 W and 32.84 N.",
):
    start_time = datetime.now().astimezone()
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
        human_message.created_at = datetime.now().isoformat()
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
                "username": username,
                "now": start_time.astimezone().isoformat(timespec="seconds"),
            },
            config={
                "run_name": "message",
                "configurable": {
                    "thread_id": str(thread.id),
                    "personality_id": str(personality_id),
                    "user_id": str(user_id),
                },
            },
            version="v2",
        ):
            kind: str = body["event"]
            name: str = body["name"]
            data: dict = body["data"]
            run_id: str = body["run_id"]
            node: Optional[str] = body["metadata"].get("langgraph_node")

            if kind in ["on_chain_start", "on_chain_end"] and name in [
                "update_title",
                "update_memory",
            ]:
                if kind == "on_chain_start":
                    active_runs[run_id] = "thinking" if name == "message" else name
                elif kind == "on_chain_end":
                    del active_runs[run_id]

                if name == "update_title" and kind == "on_chain_end":
                    thread.name = data["output"]["title"]
                    await ThreadModel.set(thread.id, "name", thread.name)

                values = list(set(active_runs.values()))
                await update_thread_status(
                    thread,
                    ", ".join(values) if len(values) > 0 else "thinking",
                    force_update=True,
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
                if isinstance(content, str) and len(content) > 0:
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
                                node=node,
                                # Use a stable start time and don't create a new one per event
                                created_at=start_time.isoformat(),
                            )
                        ),
                    )

            elif kind == "on_tool_end" and isinstance(data["output"], ToolMessage):
                output: ToolMessage = data["output"]
                output.id = run_id if not output.id else output.id
                message = ThreadMessage(
                    **output.model_dump(),
                    thread_id=thread.id,
                    node=node,
                )
                await pubsub.publish("app", MessageEvent(message=message))
            elif kind == "on_chat_model_end":
                output: AIMessage = data["output"]
                if not "update_title" in active_runs.values():
                    # @TODO: This is a hack
                    message = ThreadMessage(
                        **output.model_dump(),
                        created_at=start_time.isoformat(),
                        thread_id=thread.id,
                        node=node,
                    )
                    await pubsub.publish("app", MessageEvent(message=message))
                await update_thread_status(thread, "thinking")
            elif kind == "error":
                logger.error(data)
    except Exception as e:
        logger.exception(e)
        logger.error(f"AgentError: {e!r}")
        await update_thread_status(thread, status="error")
        await pubsub.publish("app", ErrorEvent(message=str(e)))
    finally:
        state = await aget_state(thread_id=thread_id)
        thread.message_count = len(state.values.get("messages", []))
        await update_thread_status(thread, status="idle")
        logger.debug(f"Agent completed for {thread.id}")
        last_message: Optional[AIMessage] = (
            state.values.get("messages", [])[-1]
            if len(state.values.get("messages", [])) > 0
            else None
        )
        if not last_message:
            return None
        return get_message_content(last_message)
