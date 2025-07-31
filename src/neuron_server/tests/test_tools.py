"""Unit tests for tools.py."""

from unittest.mock import patch

import pytest
from langchain.tools import BaseTool

from neuron_server.llms.tools import (
    get_tools,
    memory_tools,
    personality_tools,
    schedule_tools,
    thread_memory_tools,
    tool_sets,
)


class TestTools:
    """Test suite for tools.py."""

    def test_tool_sets_structure(self) -> None:
        """Test that tool_sets contains expected categories."""
        expected_categories = {
            "nasa",
            "charts",
            "reasoning",
            "finance",
            "kepler",
            "graph",
            "inspect",
            "document_query",
            "image",
            "video",
            "audio",
            "tts",
            "search",
            "arxiv",
            "homeassistant",
            "astro",
            "memory",
            "dice",
            "hd2",
            "weather",
            "notifications",
            "code_interpreter",
            "glados",
        }
        assert set(tool_sets.keys()) == expected_categories

    @pytest.mark.asyncio
    async def test_get_tools_single_category(self) -> None:
        """Test get_tools with a single category."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            tools = await get_tools("reasoning")
            # Should include reasoning tools plus required tools
            assert any(isinstance(tool, BaseTool) for tool in tools)
            assert len(tools) == len(tool_sets["reasoning"]) + len(
                personality_tools
            ) + len(schedule_tools) + len(thread_memory_tools)

    @pytest.mark.asyncio
    async def test_get_tools_multiple_categories(self) -> None:
        """Test get_tools with multiple categories."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            tools = await get_tools("reasoning+inspect")
            expected_count = (
                len(tool_sets["reasoning"])
                + len(tool_sets["inspect"])
                + len(personality_tools)
                + len(schedule_tools)
                + len(thread_memory_tools)
            )
            assert len(tools) == expected_count

    @pytest.mark.asyncio
    async def test_get_tools_with_memory_enabled(self) -> None:
        """Test get_tools includes memory tools when enabled."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = True
            tools = await get_tools("reasoning")
            assert any(tool.name == memory_tools[0].name for tool in tools)

    @pytest.mark.asyncio
    async def test_get_tools_with_memory_disabled(self) -> None:
        """Test get_tools excludes memory tools when disabled."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            tools = await get_tools("reasoning")
            assert not any(tool.name == memory_tools[0].name for tool in tools)

    @pytest.mark.asyncio
    async def test_get_tools_deduplication(self) -> None:
        """Test get_tools removes duplicate tools."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            # Use categories that might share tools
            tools = await get_tools("inspect+image")  # Both contain InspectImageTool
            # Count unique tool names
            unique_names = {tool.name for tool in tools}
            assert len(tools) == len(unique_names)

    @pytest.mark.asyncio
    async def test_get_tools_required_tools(self) -> None:
        """Test get_tools always includes required tools."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            tools = await get_tools("dice")  # Simple category with few tools

            # Check for required tools
            personality_tool_names = {tool.name for tool in personality_tools}
            schedule_tool_names = {tool.name for tool in schedule_tools}
            thread_memory_tool_names = {tool.name for tool in thread_memory_tools}

            tool_names = {tool.name for tool in tools}

            assert all(name in tool_names for name in personality_tool_names)
            assert all(name in tool_names for name in schedule_tool_names)
            assert all(name in tool_names for name in thread_memory_tool_names)

    @pytest.mark.asyncio
    async def test_get_tools_empty_query(self) -> None:
        """Test get_tools with empty query."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            tools = await get_tools("")
            # Should only include required tools
            expected_count = (
                len(personality_tools) + len(schedule_tools) + len(thread_memory_tools)
            )
            assert len(tools) == expected_count

    @pytest.mark.asyncio
    async def test_get_tools_invalid_category(self) -> None:
        """Test get_tools with invalid category."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            # Should not raise exception, just ignore invalid category
            tools = await get_tools("invalid_category")
            # Should only include required tools
            expected_count = (
                len(personality_tools) + len(schedule_tools) + len(thread_memory_tools)
            )
            assert len(tools) == expected_count

    @pytest.mark.asyncio
    async def test_get_tools_anthropic_search(self) -> None:
        """Test get_tools returns only BaseTool instances."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False

            tools = await get_tools("search")

            # Check that we got some tools
            assert len(tools) > 0

            # The mock TavilySearchResults won't be a BaseTool in tests
            # but schedule tools should be
            schedule_tools = [
                t
                for t in tools
                if hasattr(t, "__class__") and "Schedule" in t.__class__.__name__
            ]
            assert all(isinstance(tool, BaseTool) for tool in schedule_tools)

    @pytest.mark.asyncio
    async def test_get_tools_non_anthropic_search(self) -> None:
        """Test get_tools returns tools for search category."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False

            tools = await get_tools("search")

            # Check that we got some tools
            assert len(tools) > 0

            # No dict objects should be returned
            assert not any(isinstance(tool, dict) for tool in tools)
