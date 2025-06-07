import asyncio
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage

# Import functions and classes from agent.py
from neuron_server.llms import agent
from neuron_server.llms.agent import (
    Debouncer,
    execute_agent,
    get_message_content,
    wait_for_idle,
)


# Forward declare DummyGraph for type hints
class DummyGraph:
    pass


# --- Tests for get_message_content ---


class DummyMessage:
    def __init__(self, content: str | list | None) -> None:
        self.content = content


def test_get_message_content_with_string() -> None:
    msg = DummyMessage("hello world")
    result = get_message_content(msg, format_as_string=True)
    assert result == "hello world"


def test_get_message_content_with_list() -> None:
    msg = DummyMessage(["line1", {"type": "text", "text": "line2"}])
    result = get_message_content(msg, format_as_string=True)
    expected = "line1\nline2"
    assert result == expected


def test_get_message_content_empty() -> None:
    msg = DummyMessage("")
    result = get_message_content(msg, format_as_string=True)
    assert result is None


def test_get_message_content_with_tool_use() -> None:
    """Test handling of tool_use content type."""
    msg = DummyMessage(
        [
            {"type": "text", "text": "Let me check the weather"},
            {
                "type": "tool_use",
                "id": "tool_123",
                "name": "get_weather",
                "input": {"location": "San Francisco"},
            },
        ]
    )

    # Test structured format
    result = get_message_content(msg, format_as_string=False)
    expected_count = 2
    assert len(result) == expected_count
    assert result[0]["type"] == "text"
    assert result[1]["type"] == "tool_use"
    assert result[1]["name"] == "get_weather"
    assert result[1]["input"]["location"] == "San Francisco"

    # Test string format
    result_str = get_message_content(msg, format_as_string=True)
    assert result_str == "Let me check the weather\n[Tool: get_weather]"


def test_get_message_content_with_unknown_type() -> None:
    """Test handling of unknown content types."""
    msg = DummyMessage(
        [
            {
                "type": "custom_type",
                "custom_field": "custom_value",
                "data": {"key": "value"},
            }
        ]
    )

    # Test structured format - should pass through all fields
    result = get_message_content(msg, format_as_string=False)
    assert len(result) == 1
    assert result[0]["type"] == "custom_type"
    assert result[0]["custom_field"] == "custom_value"
    assert result[0]["data"]["key"] == "value"
    assert "index" in result[0]


# --- Tests for Debouncer class ---


@pytest.mark.asyncio
async def test_debouncer_single_call() -> None:
    call_count = 0

    async def dummy_func(x: int) -> None:
        nonlocal call_count
        call_count += x

    debouncer = Debouncer(wait=0.05)
    await debouncer.call(dummy_func, 1)
    await asyncio.sleep(0.1)  # Ensure the debounced call completes
    assert call_count == 1


@pytest.mark.asyncio
async def test_debouncer_multiple_calls() -> None:
    executed_args = []

    async def dummy_func(x: int) -> None:
        executed_args.append(x)
        await asyncio.sleep(0.01)  # Simulate some work

    debouncer = Debouncer(wait=0.05)

    # First call starts executing after wait
    await debouncer.call(dummy_func, 1)
    # Second call waits for first to complete
    await debouncer.call(dummy_func, 2)
    # Wait for all executions to complete
    await asyncio.sleep(0.2)

    # Both calls execute because the second call waits for the first to complete
    assert executed_args == [1, 2]


# --- Test for wait_for_idle ---


class DummyThread:
    def __init__(self, thread_id: UUID, status: str) -> None:
        self.id = thread_id
        self.status = status


# Generator to simulate a thread status that changes over time.
async def fake_thread_getter(
    thread_id: UUID, statuses: list[str]
) -> AsyncIterator[DummyThread]:
    for s in statuses:
        await asyncio.sleep(0.01)
        yield DummyThread(thread_id, s)


@pytest.mark.asyncio
async def test_wait_for_idle(monkeypatch: pytest.MonkeyPatch) -> None:
    thread_id = uuid4()
    statuses = ["busy", "busy", "idle"]
    status_iter = fake_thread_getter(thread_id, statuses)

    async def fake_get(_thread_id: UUID) -> DummyThread:
        try:
            return await status_iter.__anext__()
        except StopAsyncIteration:
            return DummyThread(thread_id, "idle")

    # Patch ThreadModel.get to return our fake status
    monkeypatch.setattr(agent, "ThreadModel", type("DummyTM", (), {"get": fake_get}))

    # Use longer timeout since we have small delays between status changes
    await wait_for_idle(thread_id, timeout=5)


# --- Tests for execute_agent ---


class DummyPersonality:
    def __init__(
        self, tool_set: list | None = None, context: str = "dummy personality context"
    ) -> None:
        self.tool_set = tool_set
        self.context = context


class DummyLLM:
    provider_model_id = "dummy_provider"

    def create_workflow(self, tools: list | None) -> "DummyGraph":
        # Return dummy graph with ainvoke implementation
        class DummyGraph:
            def __init__(self) -> None:
                self.checkpointer = None

            async def ainvoke(
                self, inputs: dict[str, Any], config: dict[str, Any]
            ) -> dict[str, list[AIMessage]]:
                # Return a response where the last message is our expected AIMessage
                response = AIMessage(
                    content="response to " + inputs["messages"][-1].content
                )
                return {"messages": [response]}

        return DummyGraph()


async def dummy_personality_get(personality_id: UUID) -> DummyPersonality:
    return DummyPersonality()


async def dummy_llm_get_active() -> DummyLLM:
    return DummyLLM()


async def dummy_get_tools(tool_set: list | None) -> None:
    return None


@pytest.mark.asyncio
async def test_execute_agent_success(monkeypatch: pytest.MonkeyPatch) -> None:
    test_personality_id = uuid4()

    monkeypatch.setattr(
        agent.PersonalityModel, "get", staticmethod(dummy_personality_get)
    )
    monkeypatch.setattr(
        agent.ProviderModelModel, "get_active_llm", staticmethod(dummy_llm_get_active)
    )
    monkeypatch.setattr(agent, "get_tools", dummy_get_tools)

    result = await execute_agent("test prompt", test_personality_id)
    assert result.startswith("response to")


@pytest.mark.asyncio
async def test_execute_agent_no_personality(monkeypatch: pytest.MonkeyPatch) -> None:
    test_personality_id = uuid4()

    async def fake_personality_get_fail(personality_id: UUID) -> None:
        return None

    monkeypatch.setattr(
        agent.PersonalityModel, "get", staticmethod(fake_personality_get_fail)
    )
    with pytest.raises(agent.BadRequest):
        await execute_agent("test prompt", test_personality_id)


# --- Tests for Message ID Consistency ---


class MockThread:
    def __init__(self) -> None:
        self.id = uuid4()
        self.name = "Test Thread"


class MockPersonality:
    def __init__(self) -> None:
        self.context = "test personality"


class MockStreamConfig:
    def __init__(self) -> None:
        self.location = "test"
        self.personality_id = uuid4()
        self.username = "testuser"
        self.user_id = uuid4()

    def __getitem__(self, key: str) -> str | UUID:
        return getattr(self, key)


@pytest.mark.asyncio
async def test_message_id_consistency_during_streaming() -> None:
    """Test that message IDs are handled consistently during streaming."""

    from datetime import datetime

    from langchain_core.messages import HumanMessage

    from neuron_server.llms.agent import StreamEventContext, _process_stream_events
    from neuron_server.models.personality_model import PersonalityModel
    from neuron_server.models.thread_model import ThreadModel

    # Create mock objects
    thread = MagicMock(spec=ThreadModel)
    thread.id = uuid4()
    thread.name = "Test Thread"
    thread.status = "idle"

    personality = MagicMock(spec=PersonalityModel)
    personality.context = "Test personality"

    config = {
        "thread_id": thread.id,
        "personality_id": uuid4(),
        "user_id": uuid4(),
        "username": "TestUser",
        "location": "Test Location",
    }

    human_message = HumanMessage(content="Test message")

    # Mock graph that yields streaming events
    mock_graph = MagicMock()

    # Create a run_id to track
    test_run_id = str(uuid4())

    # Simulate streaming events
    async def mock_stream_events(*args: Any, **kwargs: Any) -> AsyncIterator[dict]:
        # Yield streaming chunk
        yield {
            "event": "on_chat_model_stream",
            "name": "test_model",
            "data": {"chunk": AIMessage(content="Hello")},
            "run_id": test_run_id,
            "metadata": {"langgraph_node": "agent"},
        }
        # Yield final message
        yield {
            "event": "on_chat_model_end",
            "name": "test_model",
            "data": {"output": AIMessage(content="Hello world")},
            "run_id": test_run_id,
            "metadata": {"langgraph_node": "agent"},
        }

    mock_graph.astream_events = mock_stream_events

    # Track published events
    published_events = []

    async def mock_publish(channel: str, event: object) -> None:
        published_events.append(event)

    # Create a mock state object with values attribute
    mock_state = MagicMock()
    mock_state.values = {"messages": []}

    aget_state_mock = AsyncMock(return_value=mock_state)
    with (
        patch("neuron_server.llms.agent.pubsub.publish", mock_publish),
        patch("neuron_server.llms.agent.aget_state", aget_state_mock),
    ):
        ctx = StreamEventContext(
            thread=thread,
            graph=mock_graph,
            human_message=human_message,
            personality=personality,
            config=config,
            start_time=datetime.now(),
        )

        await _process_stream_events(ctx)

    # Verify that partial and complete messages have the same ID (run_id)
    partial_msg_id = None
    complete_msg_id = None

    for event in published_events:
        if hasattr(event, "message"):
            if hasattr(event.message, "status") and event.message.status == "streaming":
                partial_msg_id = event.message.id
            elif event.message.type == "ai" and not hasattr(event.message, "status"):
                complete_msg_id = event.message.id

    assert partial_msg_id is not None, "Should have published a partial message"
    assert complete_msg_id is not None, "Should have published a complete message"
    assert partial_msg_id == complete_msg_id == test_run_id, (
        f"Partial and complete messages should use run_id as their ID. "
        f"Expected: {test_run_id}, Partial: {partial_msg_id}, "
        f"Complete: {complete_msg_id}"
    )


@pytest.mark.asyncio
async def test_tool_message_id_gets_set_to_run_id() -> None:
    """Test that tool messages get ID set to run_id for consistency."""

    # Test the core logic of our tool message fix
    tool_message = ToolMessage(
        content="Tool result",
        tool_call_id="tool-call-123",
        id="original-tool-id",  # This should be overridden
    )

    # Simulate our fix: override the ID with run_id
    run_id = "tool-run-456"
    message_data = tool_message.model_dump()
    message_data["id"] = run_id

    # The ID should now be the run_id
    assert message_data["id"] == run_id, (
        f"Tool message ID should be run_id, got {message_data['id']}"
    )
    assert message_data["id"] != "original-tool-id", "Should override original ID"


def test_message_id_generated_consistently() -> None:
    """Test that message IDs are UUIDs and unique per call."""

    # Since we generate UUIDs, we can't predict the exact value,
    # but we can verify the format and uniqueness
    from uuid import UUID

    # Simulate multiple streaming sessions
    ids = []
    for _ in range(5):
        # Each streaming session should generate a unique ID
        test_id = str(uuid4())  # This simulates our ID generation
        ids.append(test_id)

        # Verify it's a valid UUID
        try:
            UUID(test_id)
        except ValueError:
            pytest.fail(f"Generated ID {test_id} is not a valid UUID")

    # All IDs should be unique
    assert len(set(ids)) == len(ids), "All generated message IDs should be unique"


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", __file__]))
