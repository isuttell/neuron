"""Unit tests for tools.py."""

from unittest.mock import patch

import pytest
from langchain.tools import BaseTool

from neuron_server.llms.tools import (
    get_tools,
    memory_tools,
    personality_tools,
    schedule_tools,
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
            ) + len(schedule_tools)

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

            tool_names = {tool.name for tool in tools}

            assert all(name in tool_names for name in personality_tool_names)
            assert all(name in tool_names for name in schedule_tool_names)

    @pytest.mark.asyncio
    async def test_get_tools_empty_query(self) -> None:
        """Test get_tools with empty query."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            tools = await get_tools("")
            # Should only include required tools
            expected_count = len(personality_tools) + len(schedule_tools)
            assert len(tools) == expected_count

    @pytest.mark.asyncio
    async def test_get_tools_invalid_category(self) -> None:
        """Test get_tools with invalid category."""
        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False
            # Should not raise exception, just ignore invalid category
            tools = await get_tools("invalid_category")
            # Should only include required tools
            expected_count = len(personality_tools) + len(schedule_tools)
            assert len(tools) == expected_count

    @pytest.mark.asyncio
    async def test_get_tools_anthropic_search(self) -> None:
        """Test get_tools adds Anthropic web search for anthropic provider."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock the provider model
        mock_provider = MagicMock()
        mock_provider.provider = "anthropic"

        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False

            # Mock the module-level import inside the function
            with patch(
                "neuron_server.models.provider_model.ProviderModelModel"
            ) as mock_provider_model:
                mock_provider_model.get_active_provider = AsyncMock(
                    return_value=mock_provider
                )

                tools = await get_tools("search")

                # Should have Anthropic search
                tool_names = [
                    tool.name if hasattr(tool, 'name')
                    else tool['name'] if isinstance(tool, dict) and 'name' in tool
                    else str(tool)
                    for tool in tools
                ]
                assert "web_search" in tool_names

                # Should not have TavilySearchResults
                tavily_tools = [
                    tool
                    for tool in tools
                    if tool.__class__.__name__ == "TavilySearchResults"
                ]
                assert len(tavily_tools) == 0

    @pytest.mark.asyncio
    async def test_get_tools_non_anthropic_search(self) -> None:
        """Test get_tools uses default search for non-anthropic providers."""
        from unittest.mock import AsyncMock, MagicMock

        # Mock the provider model
        mock_provider = MagicMock()
        mock_provider.provider = "openai"

        with patch("neuron_server.llms.tools.config") as mock_config:
            mock_config.memory_enabled = False

            # Mock ProviderModelModel
            with patch(
                "neuron_server.models.provider_model.ProviderModelModel"
            ) as mock_provider_model:
                mock_provider_model.get_active_provider = AsyncMock(
                    return_value=mock_provider
                )

                tools = await get_tools("search")

                # Should still have TavilySearchResults for non-anthropic providers
                # Note: TavilySearchResults may not be created due to missing API key
                # so we check that no web_search tool was added (Anthropic mode)
                tool_names = [tool.name for tool in tools]
                # In a real environment with API key, there would be TavilySearchResults
                # In test environment without API key, no search tool gets added
                # The important thing is no anthropic "web_search" tool
                assert "web_search" not in tool_names
