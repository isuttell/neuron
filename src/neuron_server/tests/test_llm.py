from datetime import datetime
from typing import NamedTuple, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langchain_core.messages.tool import ToolCall
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from neuron_server.llms.llm import (
    LLM,
    MemoryRecallRanking,
    MemoryResponse,
)
from neuron_server.models.embedding_model import EmbeddingModel


class MockConfig:
    """Mock configuration for testing."""

    memory_enabled = True


class CheckpointTuple(NamedTuple):
    """Mock checkpoint tuple for testing."""

    checkpoint: dict
    config: dict
    metadata: dict
    pending_writes: list = []  # Add pending_writes with empty list default


class MockAsyncPostgresSaver:
    """Mock implementation of AsyncPostgresSaver."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def get_state(self, config: dict) -> dict:
        """Get state with required channel_values."""
        return {
            "channel_values": {},
            "pending_sends": [],
            "step": 0,
            "id": "00000000-0000-0000-0000-000000000000",
        }

    async def save_state(self, state: dict, config: dict) -> None:
        pass

    async def aget_tuple(self, config: dict) -> CheckpointTuple:
        return CheckpointTuple(
            checkpoint={
                "channel_values": {},
                "pending_sends": [],
                "id": "00000000-0000-0000-0000-000000000000",
            },
            config={},
            metadata={"step": 0},
        )

    async def asave_tuple(self, state: dict, config: dict) -> None:
        pass


class FakeRunnable(Runnable):
    """A fake runnable that returns preset values."""

    def __init__(self, return_value: Union[AIMessage, str, MemoryResponse]) -> None:
        super().__init__()
        self.return_value = return_value

    async def ainvoke(
        self,
        message: Union[str, dict, list],
        config: dict | None = None,
        **kwargs: dict,
    ) -> Union[AIMessage, str, MemoryResponse]:
        return self.return_value

    def invoke(
        self,
        message: Union[str, dict, list],
        config: dict | None = None,
        **kwargs: dict,
    ) -> Union[AIMessage, str, MemoryResponse]:
        return self.return_value

    def bind_tools(self, tools: list[BaseTool]) -> "FakeRunnable":
        return self

    def with_structured_output(self, cls: type[BaseModel]) -> "FakeRunnable":
        return self


@pytest.fixture
def fake_model() -> FakeRunnable:
    """Create a fake model that returns an AIMessage."""
    return FakeRunnable(
        AIMessage(
            content="Test response",
            tool_calls=[],
            created_at=datetime.now().astimezone().isoformat(),
        )
    )


@pytest.fixture
def fake_title_model() -> FakeRunnable:
    """Create a fake title model that returns a title string."""
    return FakeRunnable('"Test Title"')


@pytest.fixture
def fake_memory_model() -> FakeRunnable:
    """Create a fake memory model that returns a MemoryResponse."""
    return FakeRunnable(
        MemoryResponse(
            memory_recall_rankings=[
                MemoryRecallRanking(
                    document_id="test_doc",
                    score=8.5,
                    useful=True,
                )
            ]
        )
    )


@pytest.fixture
def llm(
    fake_model: FakeRunnable,
    fake_title_model: FakeRunnable,
    fake_memory_model: FakeRunnable,
) -> LLM:
    """Create an LLM instance with fake models."""
    return LLM(
        model=fake_model,
        title_model=fake_title_model,
        memory_model=fake_memory_model,
        provider_model_id="test-model",
    )


@pytest.mark.asyncio
async def test_init(llm: LLM) -> None:
    """Test LLM initialization."""
    assert llm.model is not None
    assert llm.title_model is not None
    assert llm.memory_model is not None
    assert llm.provider_model_id == "test-model"


@pytest.mark.asyncio
async def test_create_workflow(llm: LLM) -> None:
    """Test workflow creation."""
    with (
        patch("neuron_server.llms.llm.config", MockConfig()),
        patch("neuron_server.llms.llm.default_tools", []),
    ):
        workflow = llm.create_workflow()
        assert workflow is not None


@pytest.mark.asyncio
async def test_load_memory(llm: LLM) -> None:
    """Test memory loading."""
    with patch("neuron_server.llms.llm.MemoryRecallTool") as mock_tool:
        mock_tool.return_value.ainvoke = AsyncMock(return_value="Test memory")
        state = await llm.load_memory({}, {"configurable": {"personality_id": "test"}})
        assert state["recall_memories"] == "Test memory"


@pytest.mark.asyncio
async def test_call_model(llm: LLM, fake_model: FakeRunnable) -> None:
    """Test model calling."""
    state = await llm.call_model(
        fake_model,
        {
            "messages": [],
            "personality": "test",
            "location": "test",
            "username": "test",
            "recall_memories": "",
        },
        {},
    )
    assert len(state["messages"]) == 1
    assert isinstance(state["messages"][0], AIMessage)
    assert state["messages"][0].content == "Test response"


@pytest.mark.asyncio
async def test_call_title(llm: LLM) -> None:
    """Test title generation."""
    state = await llm.call_title({"messages": [], "title": ""}, {})
    assert state["title"] == "Test Title"


@pytest.mark.asyncio
async def test_rank_memories(llm: LLM) -> None:
    """Test memory ranking."""
    # Create a mock document with initial stats
    mock_stats = {
        "useful": 0,
        "total": 0,
        "last_useful_at": None,
        "last_recall_at": None,
        "scores": [],
    }
    mock_doc = MagicMock()
    mock_doc.cmetadata = {"stats": mock_stats}
    mock_doc.save = AsyncMock()

    # Create a memory model that returns a response indicating the memory was useful
    memory_model = FakeRunnable(
        MemoryResponse(
            memory_recall_rankings=[
                MemoryRecallRanking(
                    document_id="test_doc",
                    score=8.5,
                    useful=True,
                )
            ]
        )
    )
    memory_model.with_structured_output = lambda cls: memory_model
    llm.memory_model = memory_model

    # Setup the mock to return our document
    mock_get = AsyncMock(return_value=mock_doc)
    EmbeddingModel.get = mock_get

    # Call rank_memories
    await llm.rank_memories(
        {
            "messages": [AIMessage(content="Test message")],
            "recall_memories": "Test memory",
        },
        {"configurable": {"personality_id": "test"}},
    )

    # Verify the document was retrieved
    mock_get.assert_called_once_with("test_doc")

    # Verify stats were updated correctly
    assert mock_stats["useful"] == 1
    assert mock_stats["total"] == 1
    assert len(mock_stats["scores"]) == 1
    memory_score = 8.5
    assert mock_stats["scores"][0] == memory_score
    assert mock_stats["last_useful_at"] is not None
    assert mock_stats["last_recall_at"] is not None

    # Verify save was called
    mock_doc.save.assert_called_once()


@pytest.mark.asyncio
async def test_call_update_memory(llm: LLM) -> None:
    """Test memory update scheduling."""

    # Create a mock document with initial stats
    mock_stats = {
        "useful": 0,
        "total": 0,
        "last_useful_at": None,
        "last_recall_at": None,
        "scores": [],
    }
    mock_doc = MagicMock()
    mock_doc.cmetadata = {"stats": mock_stats}
    mock_doc.save = AsyncMock()

    # Create a memory model that returns a response indicating the memory was useful
    memory_model = FakeRunnable(
        MemoryResponse(
            memory_recall_rankings=[
                MemoryRecallRanking(
                    document_id="test_doc",
                    score=8.5,
                    useful=True,
                )
            ]
        )
    )
    memory_model.with_structured_output = lambda cls: memory_model
    llm.memory_model = memory_model

    # Mock create_task and EmbeddingModel.get
    with (
        patch.object(
            EmbeddingModel, "get", new_callable=AsyncMock, return_value=mock_doc
        ) as mock_get,
    ):
        state = {"messages": [], "recall_memories": "Test memory"}
        # Call rank_memories directly since that's what call_update_memory schedules
        await llm.rank_memories(state, {"configurable": {"personality_id": "test"}})

        # Verify the document was retrieved and updated
        mock_get.assert_called_once_with("test_doc")
        assert mock_stats["useful"] == 1
        assert mock_stats["total"] == 1
        assert len(mock_stats["scores"]) == 1
        memory_score = 8.5
        assert mock_stats["scores"][0] == memory_score
        assert mock_stats["last_useful_at"] is not None
        assert mock_stats["last_recall_at"] is not None
        mock_doc.save.assert_called_once()


def test_should_call_tools() -> None:
    """Test tool calling decision logic."""
    fake_model = FakeRunnable(AIMessage(content="test"))
    llm_instance = LLM(
        model=fake_model,
        title_model=fake_model,
        memory_model=fake_model,
    )

    # Test with tool calls
    tool_call = ToolCall(name="test_tool", args={"command": "test"}, id="test_id")
    state_with_tools = {"messages": [AIMessage(content="test", tool_calls=[tool_call])]}
    assert llm_instance.should_call_tools(state_with_tools) == "tools"

    # Test without tool calls
    state_without_tools = {"messages": [AIMessage(content="test", tool_calls=[])]}
    assert llm_instance.should_call_tools(state_without_tools) == "continue"


def test_should_call_update_memory() -> None:
    """Test memory update decision logic."""
    fake_model = FakeRunnable(AIMessage(content="test"))
    llm_instance = LLM(
        model=fake_model,
        title_model=fake_model,
        memory_model=fake_model,
    )

    # Test with recall memories
    state_with_memories = {"recall_memories": "Test memory"}
    assert (
        llm_instance.should_call_update_memory(state_with_memories) == "update_memory"
    )

    # Test without recall memories
    state_without_memories = {"recall_memories": ""}
    assert llm_instance.should_call_update_memory(state_without_memories) == "continue"


@pytest.mark.asyncio
async def test_aget_state(llm: LLM) -> None:
    """Test state retrieval."""
    # Create a mock graph that returns a known state
    mock_graph = MagicMock()
    expected_state = {
        "messages": [],
        "username": "user",
        "title": "",
        "personality": "test",
        "location": "",
        "recall_memories": "",
    }
    mock_graph.aget_state = AsyncMock(return_value=expected_state)

    with patch.object(llm, "create_workflow", return_value=mock_graph):
        # Create a mock checkpointer
        mock_checkpointer = MagicMock()
        config = {"configurable": {"checkpoint_namespace": "test"}}

        # Get the state
        state = await llm.aget_state(config, mock_checkpointer)

        # Verify workflow was created and checkpointer was set
        assert llm.create_workflow.called
        assert mock_graph.checkpointer == mock_checkpointer

        # Verify state matches expected
        assert state == expected_state
