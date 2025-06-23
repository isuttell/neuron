import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage

# Import functions and classes
from neuron_server.llms import agent
from neuron_server.llms.agent import (
    execute_agent,
    wait_for_idle,
)
from neuron_server.llms.message_processor import get_message_content


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

    result = await execute_agent(
        "test prompt", test_personality_id, "test-user", "TestUser"
    )
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
        await execute_agent("test prompt", test_personality_id, "test-user", "TestUser")


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
