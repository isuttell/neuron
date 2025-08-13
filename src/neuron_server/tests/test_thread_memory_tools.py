"""Unit tests for thread memory tools."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.models.thread_model import ThreadModel
from neuron_server.tools.read_thread_memory_tool import ReadThreadMemoryTool
from neuron_server.tools.set_thread_memory_tool import SetThreadMemoryTool


@pytest.fixture
def mock_thread_id() -> str:
    """Create a mock thread ID."""
    return str(uuid4())


@pytest.fixture
def mock_config(mock_thread_id: str) -> RunnableConfig:
    """Create a mock RunnableConfig."""
    return {
        "configurable": {
            "thread_id": mock_thread_id,
            "personality_id": str(uuid4()),
            "user_id": "test-user-id",
        }
    }


@pytest.fixture
def sample_planning_board() -> str:
    """Create a sample planning board content."""
    return """# Authentication Refactor Plan

## Tasks:
- [x] Analyze current authentication implementation
- [x] Design new JWT-based auth system
- [ ] Implement user model changes
- [ ] Create JWT token generation
- [ ] Update API endpoints
- [ ] Write tests
- [ ] Update documentation

## Notes:
- Current system uses session-based auth
- Need to maintain backward compatibility
- JWT secret needs secure storage
"""


class TestSetThreadMemoryTool:
    """Tests for the SetThreadMemoryTool."""

    def test_tool_properties(self) -> None:
        """Test that the tool has correct properties."""
        tool = SetThreadMemoryTool()
        assert tool.name == "set_thread_memory"
        assert "internal task tracker" in tool.description.lower()
        assert "complex" in tool.description.lower()
        assert "checkboxes" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_successful_update_empty_previous(
        self, mock_config: RunnableConfig, sample_planning_board: str
    ) -> None:
        """Test successfully updating thread memory when previous was empty."""
        mock_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory="",  # Empty previous memory
        )

        with (
            patch.object(
                ThreadModel, "get", new_callable=AsyncMock, return_value=mock_thread
            ),
            patch.object(ThreadModel, "set", new_callable=AsyncMock) as mock_set,
        ):
            tool = SetThreadMemoryTool()
            result = await tool._arun(memory=sample_planning_board, config=mock_config)

            # Verify the update was called
            mock_set.assert_called_once_with(
                mock_config["configurable"]["thread_id"],
                "memory",
                sample_planning_board,
            )
            # Check the response tuple
            assert isinstance(result, tuple)
            assert len(result) == 2
            response_text, artifacts = result
            assert response_text == "Successfully updated your internal task tracker."
            assert isinstance(artifacts, list)
            assert len(artifacts) == 1
            assert artifacts[0]["type"] == "media"
            assert artifacts[0]["media_type"] == "text"
            assert len(artifacts[0]["items"]) == 1
            assert artifacts[0]["items"][0]["name"] == "Tasks Updated"
            assert artifacts[0]["items"][0]["description"] == sample_planning_board

    @pytest.mark.asyncio
    async def test_successful_update_with_previous(
        self, mock_config: RunnableConfig, sample_planning_board: str
    ) -> None:
        """Test successfully updating thread memory with previous content."""
        previous_content = "Old task list:\n- [x] Previous task"
        mock_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory=previous_content,
        )

        with (
            patch.object(
                ThreadModel, "get", new_callable=AsyncMock, return_value=mock_thread
            ),
            patch.object(ThreadModel, "set", new_callable=AsyncMock) as mock_set,
        ):
            tool = SetThreadMemoryTool()
            result = await tool._arun(memory=sample_planning_board, config=mock_config)

            # Verify the update was called
            mock_set.assert_called_once_with(
                mock_config["configurable"]["thread_id"],
                "memory",
                sample_planning_board,
            )
            # Check the response tuple
            assert isinstance(result, tuple)
            assert len(result) == 2
            response_text, artifacts = result
            assert "Successfully updated your internal task tracker" in response_text
            assert "Previous notes that were overwritten:" in response_text
            assert previous_content in response_text
            assert isinstance(artifacts, list)
            assert len(artifacts) == 1
            assert artifacts[0]["type"] == "media"
            assert artifacts[0]["media_type"] == "text"
            assert len(artifacts[0]["items"]) == 1
            assert artifacts[0]["items"][0]["name"] == "Tasks Updated"
            assert artifacts[0]["items"][0]["description"] == sample_planning_board

    @pytest.mark.asyncio
    async def test_missing_thread_id(self, sample_planning_board: str) -> None:
        """Test error when thread_id is missing from config."""
        invalid_config = {"configurable": {}}

        tool = SetThreadMemoryTool()
        with pytest.raises(RuntimeError, match="Failed to update thread memory"):
            await tool._arun(memory=sample_planning_board, config=invalid_config)

    @pytest.mark.asyncio
    async def test_thread_not_found(
        self, mock_config: RunnableConfig, sample_planning_board: str
    ) -> None:
        """Test error when thread is not found."""
        with patch.object(
            ThreadModel, "get", new_callable=AsyncMock, return_value=None
        ):
            tool = SetThreadMemoryTool()
            with pytest.raises(RuntimeError, match="Failed to update thread memory"):
                await tool._arun(memory=sample_planning_board, config=mock_config)

    @pytest.mark.asyncio
    async def test_database_error(
        self, mock_config: RunnableConfig, sample_planning_board: str
    ) -> None:
        """Test handling of database errors."""
        mock_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory="",
        )

        with (
            patch.object(
                ThreadModel, "get", new_callable=AsyncMock, return_value=mock_thread
            ),
            patch.object(
                ThreadModel,
                "set",
                new_callable=AsyncMock,
                side_effect=Exception("Database error"),
            ),
        ):
            tool = SetThreadMemoryTool()
            with pytest.raises(RuntimeError, match="Failed to update thread memory"):
                await tool._arun(memory=sample_planning_board, config=mock_config)

    def test_run_sync_wrapper(
        self, mock_config: RunnableConfig, sample_planning_board: str
    ) -> None:
        """Test the synchronous _run wrapper."""
        mock_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory="",
        )

        with (
            patch.object(
                ThreadModel, "get", new_callable=AsyncMock, return_value=mock_thread
            ),
            patch.object(ThreadModel, "set", new_callable=AsyncMock),
        ):
            tool = SetThreadMemoryTool()
            result = tool._run(memory=sample_planning_board, config=mock_config)
            # Check the response tuple
            assert isinstance(result, tuple)
            assert len(result) == 2
            response_text, artifacts = result
            assert "Successfully updated your internal task tracker" in response_text
            assert isinstance(artifacts, list)
            assert len(artifacts) == 1


class TestReadThreadMemoryTool:
    """Tests for the ReadThreadMemoryTool."""

    def test_tool_properties(self) -> None:
        """Test that the tool has correct properties."""
        tool = ReadThreadMemoryTool()
        assert tool.name == "read_thread_memory"
        assert "internal task tracker" in tool.description.lower()
        assert "working on" in tool.description.lower()
        assert "complex" in tool.description.lower()

    @pytest.mark.asyncio
    async def test_successful_read_with_content(
        self, mock_config: RunnableConfig, sample_planning_board: str
    ) -> None:
        """Test successfully reading thread memory with content."""
        mock_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory=sample_planning_board,
        )

        with patch.object(
            ThreadModel, "get", new_callable=AsyncMock, return_value=mock_thread
        ):
            tool = ReadThreadMemoryTool()
            result = await tool._arun(config=mock_config)

            assert result == f"Your internal task tracker:\n\n{sample_planning_board}"

    @pytest.mark.asyncio
    async def test_successful_read_empty_memory(
        self, mock_config: RunnableConfig
    ) -> None:
        """Test reading when thread memory is empty."""
        mock_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory="",  # Empty memory
        )

        with patch.object(
            ThreadModel, "get", new_callable=AsyncMock, return_value=mock_thread
        ):
            tool = ReadThreadMemoryTool()
            result = await tool._arun(config=mock_config)

            assert "internal task tracker is empty" in result
            assert "set_thread_memory" in result

    @pytest.mark.asyncio
    async def test_missing_thread_id(self) -> None:
        """Test error when thread_id is missing from config."""
        invalid_config = {"configurable": {}}

        tool = ReadThreadMemoryTool()
        with pytest.raises(RuntimeError, match="Failed to read internal task tracker"):
            await tool._arun(config=invalid_config)

    @pytest.mark.asyncio
    async def test_thread_not_found(self, mock_config: RunnableConfig) -> None:
        """Test error when thread is not found."""
        with patch.object(
            ThreadModel, "get", new_callable=AsyncMock, return_value=None
        ):
            tool = ReadThreadMemoryTool()
            with pytest.raises(
                RuntimeError, match="Failed to read internal task tracker"
            ):
                await tool._arun(config=mock_config)

    @pytest.mark.asyncio
    async def test_database_error(self, mock_config: RunnableConfig) -> None:
        """Test handling of database errors."""
        with patch.object(
            ThreadModel,
            "get",
            new_callable=AsyncMock,
            side_effect=Exception("Database error"),
        ):
            tool = ReadThreadMemoryTool()
            with pytest.raises(
                RuntimeError, match="Failed to read internal task tracker"
            ):
                await tool._arun(config=mock_config)

    def test_run_sync_wrapper(self, mock_config: RunnableConfig) -> None:
        """Test the synchronous _run wrapper."""
        mock_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory="Test content",
        )

        with patch.object(
            ThreadModel, "get", new_callable=AsyncMock, return_value=mock_thread
        ):
            tool = ReadThreadMemoryTool()
            result = tool._run(config=mock_config)
            assert "Your internal task tracker" in result
            assert "Test content" in result


class TestThreadMemoryToolsIntegration:
    """Integration tests for both thread memory tools working together."""

    @pytest.mark.asyncio
    async def test_set_then_read_workflow(
        self, mock_config: RunnableConfig, sample_planning_board: str
    ) -> None:
        """Test the workflow of setting memory then reading it back."""
        # Initial thread state (empty memory)
        initial_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory="",
        )

        # Updated thread state (with memory)
        updated_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory=sample_planning_board,
        )

        with (
            patch.object(ThreadModel, "set", new_callable=AsyncMock) as mock_set,
            patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get,
        ):
            # First get returns empty memory, then returns updated memory
            mock_get.side_effect = [initial_thread, updated_thread]

            # Set memory
            set_tool = SetThreadMemoryTool()
            set_result = await set_tool._arun(
                memory=sample_planning_board, config=mock_config
            )
            assert isinstance(set_result, tuple)
            response_text, _ = set_result
            assert response_text == "Successfully updated your internal task tracker."

            # Verify set was called
            mock_set.assert_called_once()

            # Read memory back
            read_tool = ReadThreadMemoryTool()
            read_result = await read_tool._arun(config=mock_config)
            assert sample_planning_board in read_result

    @pytest.mark.asyncio
    async def test_progressive_task_updates(self, mock_config: RunnableConfig) -> None:
        """Test progressive updates to task list."""
        # Initial task list
        initial_tasks = """# Task List
- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
"""

        # Updated task list with first task completed
        updated_tasks = """# Task List
- [x] Task 1
- [ ] Task 2
- [ ] Task 3
"""

        # Mock threads for each stage
        empty_thread = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory="",
        )

        thread_with_initial = ThreadModel(
            id=mock_config["configurable"]["thread_id"],
            user_id="test-user",
            personality_id=str(uuid4()),
            memory=initial_tasks,
        )

        with (
            patch.object(ThreadModel, "set", new_callable=AsyncMock) as mock_set,
            patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get,
        ):
            # First call returns empty, second returns initial tasks
            mock_get.side_effect = [empty_thread, thread_with_initial]

            set_tool = SetThreadMemoryTool()

            # Set initial tasks
            result1 = await set_tool._arun(memory=initial_tasks, config=mock_config)
            assert isinstance(result1, tuple)
            response_text1, _ = result1
            assert response_text1 == "Successfully updated your internal task tracker."
            assert mock_set.call_count == 1

            # Update with completed task
            result2 = await set_tool._arun(memory=updated_tasks, config=mock_config)
            assert isinstance(result2, tuple)
            response_text2, _ = result2
            assert "Previous notes that were overwritten:" in response_text2
            assert initial_tasks in response_text2
            expected_calls = 2
            assert mock_set.call_count == expected_calls

            # Verify the updates were called with correct content
            calls = mock_set.call_args_list
            assert calls[0][0][2] == initial_tasks  # First call with initial tasks
            assert calls[1][0][2] == updated_tasks  # Second call with updated tasks
