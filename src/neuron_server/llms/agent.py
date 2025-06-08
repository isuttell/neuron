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


def _process_string_content(
    content: str, format_as_string: bool
) -> str | list[dict[str, Any]]:
    """Process string content based on format preference."""
    if format_as_string:
        return content
    return [{"type": "text", "text": content, "index": 0}]


def _process_list_content_as_string(content: list) -> str:
    """Process list content and return as a string."""
    text_parts = []
    for part in content:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict):
            part_type = part.get("type")
            if part_type == "text":
                text_parts.append(part.get("text", ""))
            elif part_type == "tool_use":
                # Include tool use in string representation
                tool_name = part.get("name", "unknown_tool")
                text_parts.append(f"[Tool: {tool_name}]")
    return "\n".join(text_parts)


def _process_list_content_as_structured(content: list) -> list[dict[str, Any]] | None:
    """Process list content and return as structured content."""
    contents = []
    index = 0
    for part in content:
        if isinstance(part, str):
            contents.append({"type": "text", "text": part, "index": index})
            index += 1
        elif isinstance(part, dict):
            content_type = part.get("type")
            if content_type == "text":
                contents.append(
                    {"type": "text", "text": part.get("text", ""), "index": index}
                )
                index += 1
            elif content_type == "thinking":
                contents.append(
                    {
                        "type": "thinking",
                        "thinking": part.get("thinking", ""),
                        "index": index,
                    }
                )
                index += 1
            elif content_type == "tool_use":
                # Handle tool use content
                contents.append(
                    {
                        "type": "tool_use",
                        "id": part.get("id", ""),
                        "name": part.get("name", ""),
                        "input": part.get("input", {}),
                        "index": index,
                    }
                )
                index += 1
            else:
                # Handle any other content types generically
                # Copy all fields from the original part
                generic_content = {"index": index}
                generic_content.update(part)
                contents.append(generic_content)
                index += 1
    return contents if contents else None


def get_message_content(
    message: BaseMessage, format_as_string: bool = False
) -> list[dict[str, Any]] | str | None:
    """Extract the content from a message and format it for display.

    Args:
        message: The message to extract content from
        format_as_string: If True, return content as a string
            (for backward compatibility)

    Returns:
        A list of content objects, a string, or None if no content
    """
    if not message.content:
        return None

    content = message.content

    # Process string content
    if isinstance(content, str):
        return _process_string_content(content, format_as_string)

    # Process list content
    if isinstance(content, list):
        if format_as_string:
            return _process_list_content_as_string(content)
        return _process_list_content_as_structured(content)

    # Fallback for other content types
    if format_as_string:
        return str(content)
    return [{"type": "text", "text": str(content), "index": 0}]


class ThreadConfig(TypedDict):
    """Configuration for thread operations.

    Attributes:
        thread_id: Unique identifier for the thread
    """

    thread_id: str


class PubSubEvent(Protocol):
    """Protocol for pubsub events to avoid using Any.

    Methods:
        model_dump: Convert event to dictionary format
    """

    def model_dump(self) -> dict[str, Any]: ...


class ChainEventData(TypedDict):
    """Data structure for chain events.

    Attributes:
        kind: Type of chain event (start/end)
        name: Name of the chain
        data: Event data payload
        run_id: Unique run identifier
        active_runs: Map of active run IDs to their status
    """

    kind: str
    name: str
    data: dict[str, Any]
    run_id: str
    active_runs: dict[str, str]


class WorkflowTool(TypedDict):
    """Type definition for workflow tools.

    Attributes:
        name: Tool name
        description: Tool description
        func: Callable function implementing the tool's logic
    """

    name: str
    description: str
    func: Callable[..., Any]


class WorkflowResult(TypedDict):
    """Type definition for workflow results.

    Attributes:
        messages: List of message objects from the workflow execution
    """

    messages: list[AIMessage | HumanMessage | ToolMessage]


class StreamGraph(Protocol):
    """Protocol for stream graph interface.

    Defines the interface for streaming graph operations including workflow creation
    and event streaming.
    """

    def create_workflow(self, tools: list[WorkflowTool] | None) -> "StreamGraph": ...

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


class ToolEventContext(TypedDict):
    """Context for tool event handling.

    Attributes:
        thread: Thread model instance
        kind: Event type (start/end)
        name: Tool name
        run_id: Unique run identifier
        active_runs: Map of active run IDs to their status
        data: Event data payload
        node: Graph node identifier
    """

    thread: ThreadModel
    kind: str
    name: str
    run_id: str
    active_runs: dict[str, str]
    data: dict[str, Any]
    node: str | None


DEFAULT_LOCATION = "San Diego, California at -117.1860 W and 32.84 N."


async def execute_agent(
    prompt: str,
    personality_id: UUID,
    user_id: str,
    username: str,
    location: str = DEFAULT_LOCATION,
) -> str:
    """Execute a one-off agent interaction without streaming.

    Args:
        prompt: User's input text
        personality_id: ID of personality to use
        user_id: ID of user making request
        username: Name of user
        location: Location string (default: San Diego)

    Returns:
        The agent's response text

    Raises:
        BadRequest: If personality not found
    """
    personality = await PersonalityModel.get(personality_id)
    if personality is None:
        raise BadRequest("Personality not found")

    llm: LLM = await ProviderModelModel.get_active_llm()
    tools = await get_tools(personality.tool_set) if personality.tool_set else None
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
            "now": datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
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

    # Use format_as_string=True to get a string result for backward compatibility
    content = get_message_content(result, format_as_string=True)
    if not content:
        return ""

    return content.strip() if isinstance(content, str) else ""


async def aget_state(thread_id: UUID) -> dict[str, Any]:
    """Get the current state for a thread.

    Args:
        thread_id: ID of thread to get state for

    Returns:
        Dictionary containing thread state
    """
    checkpointer = AsyncPostgresSaver(pool)
    llm: LLM = await ProviderModelModel.get_active_llm()
    return await llm.aget_state(
        {"configurable": {"thread_id": str(thread_id)}}, checkpointer=checkpointer
    )


class Debouncer:
    """Implements debouncing for async function calls.

    Ensures that rapidly repeated function calls are throttled to prevent
    overwhelming the system.

    Attributes:
        wait: Time in seconds to wait before executing the debounced function
        task: Current async task if one is running
        _future: Future object for tracking completion
        _next_args: Arguments for next execution
        _next_kwargs: Keyword arguments for next execution
        _coro_func: Coroutine function to execute
    """

    def __init__(self, wait: float) -> None:
        """Initialize the debouncer.

        Args:
            wait: Time in seconds to wait before executing the debounced function
        """
        self.wait = wait  # seconds
        self.task: asyncio.Task[None] | None = None
        self._future: asyncio.Future[None] | None = None
        self._next_args: tuple[Any, ...] | None = None
        self._next_kwargs: dict[str, Any] | None = None
        self._coro_func: Callable[..., Any] | None = None

    async def call(
        self, coro_func: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> None:
        """Schedule a coroutine function to be executed with debouncing.

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
    """Debounces pubsub publishes to limit frequency.

    Args:
        channel: Channel to publish to
        event: Event to publish
    """
    await debounce_publish.call(pubsub.publish, channel, event)


async def update_thread_status(
    thread: ThreadModel, status: str, force_update: bool = False
) -> None:
    """Update thread status and publish the change.

    Args:
        thread: Thread model instance to update
        status: New status to set
        force_update: Whether to update even if status hasn't changed
    """
    if thread.status != status or force_update:
        thread.status = status

        async def update_task() -> None:
            """Inner task to update thread status and publish change."""
            await ThreadModel.set(thread.id, "status", status)
            await _debounced_publish("app", GetThreadResponse(thread=thread))

        asyncio.create_task(update_task())


async def wait_for_idle(thread_id: UUID, timeout: int = 300) -> None:
    """Wait for thread status to become idle, checking every second for up to 5 minutes.

    Args:
        thread_id: The thread id to monitor
        timeout: Maximum time to wait in seconds (default 300 seconds / 5 minutes)

    Raises:
        TimeoutError: If thread doesn't become idle within timeout period
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
    """Update thread title based on message content.

    Args:
        thread: Thread model instance to update
        llm: Language model instance
        human_message: Message to base title on
        personality_id: ID of personality context
        user_id: ID of user making request
    """
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
        if thread.name:
            await ThreadModel.set(thread.id, "name", thread.name)
            await _debounced_publish("app", GetThreadResponse(thread=thread))
    except Exception as e:
        logger.error(e, exc_info=True)


class ChainEvent(TypedDict):
    """Chain event data structure.

    Attributes:
        thread: Thread model instance
        event_data: Chain event data
    """

    thread: ThreadModel
    event_data: ChainEventData


async def _handle_chain_event(event: ChainEvent) -> None:
    """Handle chain start/end events.

    Processes chain lifecycle events and updates thread status accordingly.

    Args:
        event: Chain event data containing thread and event information
    """
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


async def _handle_tool_event(ctx: ToolEventContext) -> None:
    """Handle tool start/end events.

    Processes tool lifecycle events, updates thread status, and publishes
    tool messages.

    Args:
        ctx: Tool event context containing all event data
    """
    if ctx["kind"] == "on_tool_start":
        logger.debug(f"Starting tool {ctx['name']}...")
        ctx["active_runs"][ctx["run_id"]] = (
            ctx["name"]
            if ctx["name"] not in ["store_memory", "recall_memory"]
            else "update_memory"
        )
    elif ctx["kind"] == "on_tool_end":
        logger.debug(f"Finished tool {ctx['name']}...")
        del ctx["active_runs"][ctx["run_id"]]

    if ctx["kind"] == "on_tool_end" and isinstance(ctx["data"]["output"], ToolMessage):
        output: ToolMessage = ctx["data"]["output"]
        # Ensure tool messages have consistent IDs
        # Use the tool's run_id as the message ID for consistency
        message_data = output.model_dump()
        message_data["id"] = ctx["run_id"]

        message = ThreadMessage(
            **message_data,
            thread_id=ctx["thread"].id,
            node=ctx["node"],
        )
        await pubsub.publish("app", MessageEvent(message=message))

    values = list(set(ctx["active_runs"].values()))
    await update_thread_status(
        ctx["thread"],
        ", ".join(values) if len(values) > 0 else "thinking",
    )


class StreamEventContext(TypedDict):
    """Context for stream event processing.

    Attributes:
        thread: Thread model instance
        graph: Stream graph instance
        human_message: User's input message
        personality: Personality model instance
        config: Stream configuration
        start_time: Event start timestamp
    """

    thread: ThreadModel
    graph: StreamGraph
    human_message: HumanMessage
    personality: PersonalityModel
    config: StreamConfig
    start_time: datetime


async def _process_stream_events(ctx: StreamEventContext) -> str | None:
    """Process stream events and return the final message content.

    Handles the streaming of events from the language model, including:
    - Chain events (start/end)
    - Tool events (start/end)
    - Chat model streaming
    - Error events

    Args:
        ctx: Stream event context containing thread, graph, and config info

    Returns:
        The final message content or None if no messages
    """
    index = -1
    active_runs: dict[str, str] = {}
    state_result: str | None = None

    async for body in ctx["graph"].astream_events(
        {
            "messages": [ctx["human_message"]],
            "personality": ctx["personality"].context,
            "title": ctx["thread"].name,
            "location": ctx["config"]["location"],
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
                ToolEventContext(
                    thread=ctx["thread"],
                    kind=kind,
                    name=name,
                    run_id=run_id,
                    active_runs=active_runs,
                    data=data,
                    node=node,
                )
            )

        elif kind == "on_chat_model_stream" and isinstance(data["chunk"], AIMessage):
            chunk = data["chunk"]
            content = get_message_content(chunk)

            # Handle content which can now be a list of Content objects or a string
            if content:
                await update_thread_status(ctx["thread"], "streaming")
                index += 1

                # If content is still a string (for backward compatibility),
                # convert it to a Content object
                if isinstance(content, str):
                    content = [{"type": "text", "text": content, "index": 0}]

                await pubsub.publish(
                    "app",
                    PartialMessageEvent(
                        message=PartialMessage(
                            id=run_id,  # Use run_id directly as message ID
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
        elif kind == "on_chat_model_end":
            output: AIMessage = data["output"]
            if "update_title" not in active_runs.values():
                # Use the run_id as the message ID to match streaming messages
                message_data = output.model_dump()
                message_data["id"] = run_id

                message = ThreadMessage(
                    **message_data,
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
        # Use format_as_string=True for backward compatibility with existing code
        state_result = get_message_content(last_message, format_as_string=True)

    return state_result


async def astream(args: StreamArgs) -> str | None:
    """Stream agent responses and handle message processing.

    Main entry point for streaming agent responses. Handles:
    - Thread status management
    - Personality loading
    - LLM initialization
    - Message creation and publishing
    - Event streaming
    - Error handling

    Args:
        args: StreamArgs containing thread_id, personality_id, and other parameters

    Returns:
        The final message content or None if no messages

    Raises:
        Exception: If thread or personality not found
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

        # Create the human message first so we can return it quickly
        human_message = HumanMessage(
            id=str(uuid4()),
            user_id=config["user_id"],
            content=f"<|AI|>User: {config['username']}<|AI|>\n{config['prompt']}",
            created_at=datetime.now().astimezone().isoformat(),
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

        llm: LLM = await ProviderModelModel.get_active_llm()
        logger.debug(f"provider_model_id={llm.provider_model_id}")
        tools = await get_tools(personality.tool_set) if personality.tool_set else None
        graph = llm.create_workflow(tools)
        graph.checkpointer = AsyncPostgresSaver(pool)

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
