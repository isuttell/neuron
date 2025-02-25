import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from langchain_core.messages import AIMessage

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


def dummy_get_tools(tool_set: list | None) -> None:
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


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main(["-v", __file__]))
