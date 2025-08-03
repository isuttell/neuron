"""Tests for PyodideCodeInterpreterTool."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.tools.pyodide_code_interpreter_tool import (
    PyodideCodeInterpreterTool,
    PyodideCodeInterpreterToolArgs,
)


class TestPyodideCodeInterpreterToolArgs:
    """Test suite for PyodideCodeInterpreterToolArgs."""

    def test_valid_args(self) -> None:
        """Test creating valid tool arguments."""
        args = PyodideCodeInterpreterToolArgs(
            python_code="print('hello')",
            stateful=True,
        )
        assert args.python_code == "print('hello')"
        assert args.stateful is True

    def test_default_stateful(self) -> None:
        """Test default stateful value."""
        args = PyodideCodeInterpreterToolArgs(python_code="print('hello')")
        assert args.stateful is True

    def test_empty_code_valid(self) -> None:
        """Test that empty code is actually valid (no validation on empty strings)."""
        # Empty code is allowed by Pydantic - the tool should handle it
        args = PyodideCodeInterpreterToolArgs(python_code="")
        assert args.python_code == ""


class TestPyodideCodeInterpreterTool:
    """Test suite for PyodideCodeInterpreterTool."""

    @pytest.fixture
    def tool(self) -> PyodideCodeInterpreterTool:
        """Create a tool instance for testing."""
        return PyodideCodeInterpreterTool()

    @pytest.fixture
    def mock_config(self) -> RunnableConfig:
        """Create a mock config for testing."""
        return RunnableConfig(
            configurable={
                "thread_id": "test_thread_123",
                "user_id": "test_user_456",
            }
        )

    @pytest.fixture
    def mock_sandbox_result(self) -> MagicMock:
        """Create a mock sandbox execution result."""
        result = MagicMock()
        result.stdout = "Hello, World!"
        result.stderr = ""
        result.session_bytes = b"session_data"
        result.session_metadata = {"variables": {"x": 42, "y": "test"}}
        return result

    @pytest.mark.asyncio
    async def test_successful_execution(
        self, tool: PyodideCodeInterpreterTool, mock_config: RunnableConfig
    ) -> None:
        """Test successful code execution."""
        with (
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.PyodideSandbox"
            ) as mock_sandbox_class,
            patch("neuron_server.tools.pyodide_code_interpreter_tool.os.makedirs"),
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.aiofiles.open"
            ) as mock_aio_open,
        ):
            # Setup mocks
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox

            mock_result = MagicMock()
            mock_result.stdout = "42"
            mock_result.stderr = ""
            mock_result.session_bytes = b"session_data"
            mock_result.session_metadata = {}
            mock_sandbox.execute.return_value = mock_result

            # Mock file operations
            mock_file = AsyncMock()
            mock_file.write = AsyncMock()
            mock_aio_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
            mock_aio_open.return_value.__aexit__ = AsyncMock()

            # Execute
            result = await tool._arun(
                python_code="print(2 + 2)",
                config=mock_config,
                stateful=False,
            )

            # Verify result format
            assert isinstance(result, tuple)
            assert len(result) == 2
            content, artifacts = result

            # Check content
            assert "42" in content
            assert "Execution time:" in content
            assert "seconds" in content

            # Check artifacts
            assert isinstance(artifacts, list)
            assert len(artifacts) == 1  # Always creates execution artifact

            # Check artifact content
            artifact = artifacts[0]
            assert artifact["media_type"] == "code"
            assert len(artifact["items"]) >= 1  # At least code artifact

            # Check that we have the expected items
            captions = [item["name"] for item in artifact["items"]]
            assert "Source Code" in captions

            # Verify sandbox was called correctly
            mock_sandbox_class.assert_called_once_with(allow_net=True)
            mock_sandbox.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_stateful_execution(
        self,
        tool: PyodideCodeInterpreterTool,
        mock_config: RunnableConfig,
        mock_sandbox_result: MagicMock,
    ) -> None:
        """Test stateful code execution with session caching."""
        with patch(
            "neuron_server.tools.pyodide_code_interpreter_tool.PyodideSandbox"
        ) as mock_sandbox_class:
            # Setup mock
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox
            mock_sandbox.execute.return_value = mock_sandbox_result

            # First execution
            await tool._arun(
                python_code="x = 42",
                config=mock_config,
                stateful=True,
            )

            # Check that session was cached
            cache_key = f"stateful_{id(mock_config)}"
            assert cache_key in tool._sandbox_cache
            assert cache_key in tool._cleanup_tasks

            # Second execution should use cached sandbox
            await tool._arun(
                python_code="print(x)",
                config=mock_config,
                stateful=True,
            )

            # Sandbox should only be created once
            mock_sandbox_class.assert_called_once()

            # Execute should be called twice with correct session data
            assert mock_sandbox.execute.call_count == 2

            # Second call should have session data
            second_call_args = mock_sandbox.execute.call_args_list[1]
            assert second_call_args[1]["session_bytes"] == b"session_data"

    @pytest.mark.asyncio
    async def test_cleanup_task_scheduling(
        self, tool: PyodideCodeInterpreterTool, mock_config: RunnableConfig
    ) -> None:
        """Test that cleanup tasks are properly scheduled."""
        with patch(
            "neuron_server.tools.pyodide_code_interpreter_tool.PyodideSandbox"
        ) as mock_sandbox_class:
            # Setup mock
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox

            mock_result = MagicMock()
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_result.session_bytes = b"data"
            mock_result.session_metadata = {}
            mock_sandbox.execute.return_value = mock_result

            # Execute with stateful=True
            await tool._arun(
                python_code="x = 1",
                config=mock_config,
                stateful=True,
            )

            # Check cleanup task was created
            cache_key = f"stateful_{id(mock_config)}"
            assert cache_key in tool._cleanup_tasks
            cleanup_task = tool._cleanup_tasks[cache_key]
            assert isinstance(cleanup_task, asyncio.Task)
            assert not cleanup_task.done()

            # Cancel cleanup to prevent warnings
            cleanup_task.cancel()

    @pytest.mark.asyncio
    async def test_cleanup_task_execution(
        self, tool: PyodideCodeInterpreterTool, mock_config: RunnableConfig
    ) -> None:
        """Test that cleanup tasks actually remove cached sessions."""
        # Create a cleanup task with very short delay
        cache_key = "test_key"
        tool._sandbox_cache[cache_key] = (MagicMock(), b"data", {})

        # Schedule cleanup with 0.1 second delay
        cleanup_task = asyncio.create_task(tool._schedule_cleanup(cache_key, delay=0.1))
        tool._cleanup_tasks[cache_key] = cleanup_task

        # Wait for cleanup
        await asyncio.sleep(0.2)

        # Verify cleanup happened
        assert cache_key not in tool._sandbox_cache
        assert cache_key not in tool._cleanup_tasks

    @pytest.mark.asyncio
    async def test_artifact_generation(
        self, tool: PyodideCodeInterpreterTool, mock_config: RunnableConfig
    ) -> None:
        """Test artifact generation when variables are returned."""
        with (
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.PyodideSandbox"
            ) as mock_sandbox_class,
            patch("neuron_server.tools.pyodide_code_interpreter_tool.os.makedirs"),
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.aiofiles.open"
            ) as mock_aio_open,
        ):
            # Setup mock with variables
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox

            mock_result = MagicMock()
            mock_result.stdout = "Calculation complete"
            mock_result.stderr = ""
            mock_result.session_bytes = b"session"
            mock_result.session_metadata = {
                "variables": {
                    "result": 42,
                    "data": [1, 2, 3],
                    "name": "test",
                }
            }
            mock_sandbox.execute.return_value = mock_result

            # Mock file operations
            mock_file = AsyncMock()
            mock_file.write = AsyncMock()
            mock_aio_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
            mock_aio_open.return_value.__aexit__ = AsyncMock()

            # Execute
            result = await tool._arun(
                python_code="result = 42; data = [1,2,3]; name = 'test'",
                config=mock_config,
            )

            content, artifacts = result

            # Check artifacts were created
            assert len(artifacts) == 1
            artifact = artifacts[0]

            assert artifact["media_type"] == "code"
            assert len(artifact["items"]) >= 1  # At least code artifact

            # Check we have expected items
            captions = [item["name"] for item in artifact["items"]]
            assert "Source Code" in captions

    @pytest.mark.asyncio
    async def test_execution_error_handling(
        self, tool: PyodideCodeInterpreterTool, mock_config: RunnableConfig
    ) -> None:
        """Test handling of execution errors."""
        with patch(
            "neuron_server.tools.pyodide_code_interpreter_tool.PyodideSandbox"
        ) as mock_sandbox_class:
            # Setup mock to raise error
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox
            mock_sandbox.execute.side_effect = Exception(
                "Execution failed: syntax error"
            )

            # Execute should not raise but return error in content
            result = await tool._arun(
                python_code="invalid python code !!!",
                config=mock_config,
            )

            content, artifacts = result

            # Check error content
            assert "Error:" in content
            assert "Execution failed: syntax error" in content
            assert len(artifacts) == 0

    @pytest.mark.asyncio
    async def test_cleanup_method(self, tool: PyodideCodeInterpreterTool) -> None:
        """Test the cleanup method cancels all tasks."""
        # Create some mock tasks
        for i in range(3):
            task = AsyncMock()
            task.cancel = MagicMock()
            tool._cleanup_tasks[f"task_{i}"] = task
            tool._sandbox_cache[f"cache_{i}"] = (MagicMock(), b"data", {})

        # Run cleanup
        await tool.cleanup()

        # Verify all tasks were cancelled
        assert len(tool._cleanup_tasks) == 0
        assert len(tool._sandbox_cache) == 0

    def test_del_method(self, tool: PyodideCodeInterpreterTool) -> None:
        """Test the __del__ method performs cleanup."""
        # Create mock tasks
        task1 = MagicMock()
        task2 = MagicMock()
        tool._cleanup_tasks = {"task1": task1, "task2": task2}
        tool._sandbox_cache = {"cache1": (MagicMock(), b"data", {})}

        # Call __del__
        tool.__del__()

        # Verify cleanup
        task1.cancel.assert_called_once()
        task2.cancel.assert_called_once()
        assert len(tool._cleanup_tasks) == 0
        assert len(tool._sandbox_cache) == 0

    @pytest.mark.asyncio
    async def test_stderr_output(
        self, tool: PyodideCodeInterpreterTool, mock_config: RunnableConfig
    ) -> None:
        """Test handling of stderr output."""
        with (
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.PyodideSandbox"
            ) as mock_sandbox_class,
            patch("neuron_server.tools.pyodide_code_interpreter_tool.os.makedirs"),
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.aiofiles.open"
            ) as mock_aio_open,
        ):
            # Setup mock with stderr
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox

            mock_result = MagicMock()
            mock_result.stdout = "Success"
            mock_result.stderr = "Warning: deprecated function"
            mock_result.session_bytes = b""
            mock_result.session_metadata = {}
            mock_sandbox.execute.return_value = mock_result

            # Mock file operations
            mock_file = AsyncMock()
            mock_file.write = AsyncMock()
            mock_aio_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
            mock_aio_open.return_value.__aexit__ = AsyncMock()

            # Execute
            result = await tool._arun(
                python_code="import warnings; warnings.warn('deprecated')",
                config=mock_config,
            )

            content, _ = result

            # Check both stdout and stderr are included
            assert "Success" in content
            assert "deprecated function" in content
            assert "Execution time:" in content

    @pytest.mark.asyncio
    async def test_execution_timing(
        self, tool: PyodideCodeInterpreterTool, mock_config: RunnableConfig
    ) -> None:
        """Test that execution time is tracked."""
        with (
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.PyodideSandbox"
            ) as mock_sandbox_class,
            patch("neuron_server.tools.pyodide_code_interpreter_tool.os.makedirs"),
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.aiofiles.open"
            ) as mock_aio_open,
        ):
            # Setup mock
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox

            mock_result = MagicMock()
            mock_result.stdout = "Done"
            mock_result.stderr = ""
            mock_result.session_bytes = b""
            mock_result.session_metadata = {}

            # Mock file operations
            mock_file = AsyncMock()
            mock_file.write = AsyncMock()
            mock_aio_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
            mock_aio_open.return_value.__aexit__ = AsyncMock()

            # Add delay to simulate execution time
            async def delayed_execute(*args, **kwargs):
                await asyncio.sleep(0.1)
                return mock_result

            mock_sandbox.execute = delayed_execute

            # Execute
            start = time.time()
            result = await tool._arun(
                python_code="print('test')",
                config=mock_config,
            )
            duration = time.time() - start

            content, _ = result

            # Check execution time is reported
            assert "Execution time:" in content
            assert "seconds" in content
            # Should take at least 0.1 seconds
            assert duration >= 0.1

    @pytest.mark.asyncio
    async def test_execution_with_different_configs(
        self, tool: PyodideCodeInterpreterTool
    ) -> None:
        """Test that tool executes successfully with different config setups."""
        with (
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.PyodideSandbox"
            ) as mock_sandbox_class,
            patch("neuron_server.tools.pyodide_code_interpreter_tool.os.makedirs"),
            patch(
                "neuron_server.tools.pyodide_code_interpreter_tool.aiofiles.open"
            ) as mock_aio_open,
        ):
            # Setup minimal mock for sandbox execution
            mock_sandbox = AsyncMock()
            mock_sandbox_class.return_value = mock_sandbox

            mock_result = MagicMock()
            mock_result.stdout = "hello"
            mock_result.stderr = ""
            mock_result.session_bytes = b""
            mock_result.session_metadata = {}
            mock_sandbox.execute.return_value = mock_result

            # Mock file operations
            mock_file = AsyncMock()
            mock_file.write = AsyncMock()
            mock_aio_open.return_value.__aenter__ = AsyncMock(return_value=mock_file)
            mock_aio_open.return_value.__aexit__ = AsyncMock()

            # Test with missing user_id - tool should still work
            config_no_user = RunnableConfig(
                configurable={
                    "thread_id": "test_thread_123",
                    # user_id missing
                }
            )

            result = await tool._arun(
                python_code="print('hello')",
                config=config_no_user,
            )
            content, artifacts = result
            assert "hello" in content
            assert "Execution time:" in content
            assert len(artifacts) == 1  # Should still create artifact

            # Test with None user_id - tool should still work
            config_none_user = RunnableConfig(
                configurable={
                    "thread_id": "test_thread_123",
                    "user_id": None,
                }
            )

            result = await tool._arun(
                python_code="print('hello')",
                config=config_none_user,
            )
            content, artifacts = result
            assert "hello" in content
            assert len(artifacts) == 1

            # Test with empty string user_id - tool should still work
            config_empty_user = RunnableConfig(
                configurable={
                    "thread_id": "test_thread_123",
                    "user_id": "",
                }
            )

            result = await tool._arun(
                python_code="print('hello')",
                config=config_empty_user,
            )
            content, artifacts = result
            assert "hello" in content
            assert len(artifacts) == 1

    def test_tool_metadata(self, tool: PyodideCodeInterpreterTool) -> None:
        """Test tool metadata and properties."""
        assert tool.name == "pyodide_code_interpreter"
        assert "Pyodide WebAssembly sandbox" in tool.description
        assert "mathematical calculations" in tool.description
        assert tool.timeout == 120
        assert tool.response_format == "content_and_artifact"
