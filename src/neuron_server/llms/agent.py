import asyncio
from collections.abc import AsyncIterator, Callable
from datetime import datetime
from typing import Any, Protocol, TypedDict
from uuid import UUID, uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from werkzeug.exceptions import BadRequest

from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessage,
    PartialMessageEvent,
    ThreadMessage,
)
from neuron_server.controllers.events.thread_events import GetThreadResponse
from neuron_server.database import pool
from neuron_server.event_router import ErrorEvent
from neuron_server.llms.llm import LLM
from neuron_server.llms.tools import get_tools
from neuron_server.logger import logger
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.thread_model import ThreadModel
from neuron_server.pubsub import pubsub

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}



def get_message_content(message: BaseMessage) -> str | None:
    """Extract the content from a message and format it for display.

    Args:
        message: The message to extract content from

    Returns:
        The formatted message content or None if no content
    """
    if not message.content:
        return None

    if isinstance(message.content, str):
        return message.content

    if isinstance(message.content, list):
        text_parts = []
        for part in message.content:
            if isinstance(part, str):
                text_parts.append(part)
            elif isinstance(part, dict) and part.get("type") == "text":
                text_parts.append(part["text"])
        return "\n".join(text_parts)

    return str(message.content)

class ThreadConfig(TypedDict):
    thread_id: str


class PubSubEvent(Protocol):
    """Protocol for pubsub events to avoid using Any."""
    def model_dump(self) -> dict[str, Any]: ...


class ChainEventData(TypedDict):
    """Data structure for chain events."""
    kind: str
    name: str
    data: dict
    run_id: str
    active_runs: dict[str, str]


class WorkflowTool(TypedDict):
    """Type definition for workflow tools."""
    name: str
    description: str
    func: Callable[..., Any]


class WorkflowResult(TypedDict):
    """Type definition for workflow results."""
    messages: list[AIMessage | HumanMessage | ToolMessage]


class StreamGraph(Protocol):
    """Protocol for stream graph interface."""
    def create_workflow(
        self, tools: list[WorkflowTool] | None
    ) -> "StreamGraph": ...

    async def astream_events(
        self,
        inputs: dict[str, Any],
        config: dict[str, Any],
        version: str = "v2",
    ) -> AsyncIterator[dict[str, Any]]: ...

    async def ainvoke(
        self,
        inputs: dict[str, Any],
        config: dict[str, Any],
    ) -> WorkflowResult: ...


class StreamArgs(TypedDict, total=False):
    """Arguments for stream operations.

    Attributes:
        thread_id: The thread ID
        personality_id: The personality ID
        user_id: The user ID (optional)
        username: The username (optional)
        prompt: The prompt text
        location: The location string (default: San Diego coordinates)
    """
    thread_id: UUID
    personality_id: UUID
    user_id: str | None
    username: str | None
    prompt: str
    location: str


class StreamConfig(TypedDict):
    """Configuration for streaming agent responses."""
    thread_id: UUID
    personality_id: UUID
    user_id: UUID
    username: str
    prompt: str
    location: str


DEFAULT_LOCATION = "San Diego, California at -117.1860 W and 32.84 N."


async def execute_agent(
    prompt: str,
    personality_id: UUID,
    user_id: str = "auth0|677842260dc433462eaf13a6",
    username: str = "Isaac",
    location: str = DEFAULT_LOCATION,
) -> str:
    personality = await PersonalityModel.get(personality_id)
    if personality is None:
        raise BadRequest("Personality not found")

    llm: LLM = await ProviderModelModel.get_active_llm()
    tools = get_tools(personality.tool_set) if personality.tool_set else None
    graph = llm.create_workflow(tools)
    graph.checkpointer = None
    result: AIMessage = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content=(
                        "I can't respond so please try you're best to fulfill my "
                        "next request but don't ask questions or provide prompt "
                        "suggestions. Just respond with the answer to my question."
                    )
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


async def aget_state(thread_id: UUID) -> dict[str, Any]:
    checkpointer = AsyncPostgresSaver(pool)
    llm: LLM = await ProviderModelModel.get_active_llm()
    return await llm.aget_state(
        {"configurable": {"thread_id": str(thread_id)}}, checkpointer=checkpointer
    )


class Debouncer:
    def __init__(self, wait: float) -> None:
        self.wait = wait  # seconds
        self.task: asyncio.Task | None = None
        self._future: asyncio.Future | None = None
        self._next_args: tuple | None = None
        self._next_kwargs: dict | None = None
        self._coro_func: Callable | None = None

    async def call(
        self, coro_func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
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

    async def _handle(self) -> None:
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


async def _debounced_publish(channel: str, event: PubSubEvent) -> None:
    """Debounces pubsub publishes to limit frequency."""
    await debounce_publish.call(pubsub.publish, channel, event)


async def update_thread_status(
    thread: ThreadModel, status: str, force_update: bool = False
) -> None:
    if thread.status != status or force_update:
        thread.status = status

        async def task() -> None:
            await ThreadModel.set(thread.id, "status", status)
            await _debounced_publish("app", GetThreadResponse(thread=thread))

        asyncio.create_task(task())


async def wait_for_idle(thread_id: UUID, timeout: int = 300) -> None:
    """
    Wait for thread status to become idle, checking every second for up to 5 minutes.

    Args:
        thread_id: The thread id to monitor
        timeout: Maximum time to wait in seconds (default 300 seconds / 5 minutes)

    Raises:
        asyncio.TimeoutError: If thread doesn't become idle within timeout period
    """
    start_time = asyncio.get_event_loop().time()
    thread = await ThreadModel.get(thread_id)
    while thread and thread.status not in {"idle", "error"}:
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(
                f"Thread {thread.id} did not become idle within {timeout} seconds"
            )
        logger.debug(f"Thread {thread.id} is {thread.status}. Waiting...")
        await asyncio.sleep(1)
        thread = await ThreadModel.get(thread_id)


async def update_title(
    thread: ThreadModel,
    llm: LLM,
    human_message: HumanMessage,
    personality_id: UUID,
    user_id: UUID,
) -> None:
    try:
        logger.debug("Generating thread name...")
        title_response = await llm.call_title(
            state={
                "title": thread.name,
                "messages": [
                    human_message,
                ],
            },
            config={
                "configurable": {
                    "thread_id": str(thread.id),
                    "personality_id": str(personality_id),
                    "user_id": str(user_id),
                },
            },
        )
        thread.name = title_response["title"]
        await ThreadModel.set(thread.id, "name", thread.name)
        await _debounced_publish("app", GetThreadResponse(thread=thread))
    except Exception as e:
        logger.error(e, exc_info=True)


class ChainEvent(TypedDict):
    """Chain event data structure."""
    thread: ThreadModel
    event_data: ChainEventData


async def _handle_chain_event(event: ChainEvent) -> None:
    """Handle chain start/end events."""
    thread = event["thread"]
    data = event["event_data"]

    if data["kind"] == "on_chain_start":
        data["active_runs"][data["run_id"]] = (
            "thinking" if data["name"] == "message" else data["name"]
        )
    elif data["kind"] == "on_chain_end":
        del data["active_runs"][data["run_id"]]

    if data["name"] == "update_title" and data["kind"] == "on_chain_end":
        thread.name = data["data"]["output"]["title"]
        await ThreadModel.set(thread.id, "name", thread.name)

    values = list(set(data["active_runs"].values()))
    await update_thread_status(
        thread,
        ", ".join(values) if len(values) > 0 else "thinking",
        force_update=True,
    )


async def _handle_tool_event(
    thread: ThreadModel,
    kind: str,
    name: str,
    run_id: str,
    active_runs: dict[str, str],
) -> None:
    """Handle tool start/end events."""
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


class StreamEventContext(TypedDict):
    """Context for stream event processing."""
    thread: ThreadModel
    graph: StreamGraph
    human_message: HumanMessage
    personality: PersonalityModel
    config: StreamConfig
    start_time: datetime


async def _process_stream_events(ctx: StreamEventContext) -> str | None:
    """Process stream events and return the final message content."""
    index = -1
    active_runs: dict[str, str] = {}
    state_result: str | None = None

    async for body in ctx["graph"].astream_events(
        {
            "messages": [ctx["human_message"]],
            "personality": ctx["personality"].context,
            "title": ctx["thread"].name,
            "location": ctx["config"]["location"],
            "username": ctx["config"]["username"],
            "now": ctx["start_time"].astimezone().isoformat(timespec="seconds"),
        },
        config={
            "run_name": "message",
            "configurable": {
                "thread_id": str(ctx["thread"].id),
                "personality_id": str(ctx["config"]["personality_id"]),
                "username": ctx["config"]["username"],
                "user_id": str(ctx["config"]["user_id"]),
            },
        },
        version="v2",
    ):
        kind: str = body["event"]
        name: str = body["name"]
        data: dict = body["data"]
        run_id: str = body["run_id"]
        node: str | None = body["metadata"].get("langgraph_node")

        if kind in ["on_chain_start", "on_chain_end"] and name in [
            "update_title",
            "update_memory",
        ]:
            await _handle_chain_event(
                ChainEvent(
                    thread=ctx["thread"],
                    event_data=ChainEventData(
                        kind=kind,
                        name=name,
                        data=data,
                        run_id=run_id,
                        active_runs=active_runs,
                    ),
                )
            )

        elif kind in ["on_tool_start", "on_tool_end"]:
            await _handle_tool_event(
                ctx["thread"], kind, name, run_id, active_runs
            )

        elif kind == "on_chat_model_stream" and isinstance(data["chunk"], AIMessage):
            chunk = data["chunk"]
            content = get_message_content(chunk)
            if isinstance(content, str) and len(content) > 0:
                await update_thread_status(ctx["thread"], "streaming")
                index += 1
                await pubsub.publish(
                    "app",
                    PartialMessageEvent(
                        message=PartialMessage(
                            id=run_id,
                            type="ai",
                            content=content,
                            thread_id=ctx["thread"].id,
                            index=index,
                            status="streaming",
                            node=node,
                            created_at=ctx["start_time"].isoformat(),
                        )
                    ),
                )

        elif kind == "on_tool_end" and isinstance(data["output"], ToolMessage):
            output: ToolMessage = data["output"]
            output.id = run_id if not output.id else output.id
            message = ThreadMessage(
                **output.model_dump(),
                thread_id=ctx["thread"].id,
                node=node,
            )
            await pubsub.publish("app", MessageEvent(message=message))

        elif kind == "on_chat_model_end":
            output: AIMessage = data["output"]
            if "update_title" not in active_runs.values():
                message = ThreadMessage(
                    **output.model_dump(),
                    thread_id=ctx["thread"].id,
                    node=node,
                )
                if not message.created_at:
                    message.created_at = ctx["start_time"].isoformat()
                await pubsub.publish("app", MessageEvent(message=message))
            await update_thread_status(ctx["thread"], "thinking")

        elif kind == "error":
            logger.error(data)

    # Get final state outside the finally block
    state = await aget_state(thread_id=ctx["config"]["thread_id"])
    ctx["thread"].message_count = len(state.values.get("messages", []))
    last_message: AIMessage | None = (
        state.values.get("messages", [])[-1]
        if len(state.values.get("messages", [])) > 0
        else None
    )
    if last_message:
        state_result = get_message_content(last_message)

    return state_result


async def astream(args: StreamArgs) -> str | None:
    """Stream agent responses and handle message processing.

    Args:
        args: StreamArgs containing all necessary parameters

    Returns:
        The final message content or None if no messages
    """
    config = StreamConfig(
        thread_id=args["thread_id"],
        personality_id=args["personality_id"],
        user_id=args.get("user_id") or "Unknown",
        username=args.get("username") or "Unknown",
        prompt=args["prompt"],
        location=args.get("location", DEFAULT_LOCATION),
    )
    start_time = datetime.now().astimezone()
    logger.debug(f"Agent started for {config['thread_id']}")
    thread = None
    result: str | None = None

    try:
        thread = await ThreadModel.get(config["thread_id"])
        if not thread:
            raise Exception("Thread not found")
        if thread.status not in {"idle", "error"}:
            await wait_for_idle(config["thread_id"])

        await update_thread_status(thread, "thinking")

        personality = await PersonalityModel.get(config["personality_id"])
        if personality is None:
            raise Exception("Personality not found")

        llm: LLM = await ProviderModelModel.get_active_llm()
        logger.debug(f"provider_model_id={llm.provider_model_id}")
        tools = get_tools(personality.tool_set) if personality.tool_set else None
        graph = llm.create_workflow(tools)
        graph.checkpointer = AsyncPostgresSaver(pool)

        # Create the human message
        human_message = HumanMessage(
            id=str(uuid4()),
            content=config["prompt"],
            created_at=datetime.now().astimezone().isoformat(),
        )

        # Update the thread name if it's not already set
        if not thread.name:
            asyncio.create_task(
                update_title(
                    thread,
                    llm,
                    human_message,
                    config["personality_id"],
                    config["user_id"],
                )
            )

        await pubsub.publish(
            "app",
            MessageEvent(
                message=ThreadMessage(
                    **human_message.model_dump(),
                    thread_id=thread.id,
                )
            ),
        )

        result = await _process_stream_events(
            StreamEventContext(
                thread=thread,
                graph=graph,
                human_message=human_message,
                personality=personality,
                config=config,
                start_time=start_time,
            )
        )

    except Exception as e:
        logger.error(e, exc_info=True)
        logger.error(f"AgentError: {e!r}")
        if thread:
            await update_thread_status(thread, status="error")
        await pubsub.publish("app", ErrorEvent(message=str(e)))

    finally:
        if thread:
            await update_thread_status(thread, status="idle")
            logger.debug(f"Agent completed for {thread.id}")

    return result
