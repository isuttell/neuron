"""Unit tests for TavilySearchTool."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError

from neuron_server.tools.tavily_search_tool import (
    TavilySearchTool,
    TavilySearchToolArgs,
)


class TestTavilySearchToolArgs:
    """Test suite for TavilySearchToolArgs parameter validation."""

    def test_valid_parameters(self) -> None:
        """Test valid parameter combinations."""
        # Test minimal valid parameters
        args = TavilySearchToolArgs(query="test query")
        assert args.query == "test query"
        assert args.topic == "general"  # default
        assert args.time_range is None  # default
        assert args.max_results == 5  # default
        assert args.search_depth == "basic"  # default
        assert args.include_answer is False  # default
        assert args.include_raw_content is False  # default

    def test_all_parameters(self) -> None:
        """Test all parameters with valid values."""
        args = TavilySearchToolArgs(
            query="Python programming",
            topic="news",
            time_range="week",
            include_domains=["stackoverflow.com", "github.com"],
            exclude_domains=["spam.com"],
            max_results=10,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=True,
        )
        assert args.query == "Python programming"
        assert args.topic == "news"
        assert args.time_range == "week"
        assert args.include_domains == ["stackoverflow.com", "github.com"]
        assert args.exclude_domains == ["spam.com"]
        assert args.max_results == 10
        assert args.search_depth == "advanced"
        assert args.include_answer is True
        assert args.include_raw_content is True

    def test_topic_validation(self) -> None:
        """Test topic parameter validation."""
        # Valid topics
        for topic in ["general", "news", "finance"]:
            args = TavilySearchToolArgs(query="test", topic=topic)
            assert args.topic == topic

        # Invalid topic
        with pytest.raises(ValidationError):
            TavilySearchToolArgs(query="test", topic="invalid")

    def test_time_range_validation(self) -> None:
        """Test time_range parameter validation."""
        # Valid time ranges
        for time_range in ["day", "week", "month", "year"]:
            args = TavilySearchToolArgs(query="test", time_range=time_range)
            assert args.time_range == time_range

        # None is valid
        args = TavilySearchToolArgs(query="test", time_range=None)
        assert args.time_range is None

        # Invalid time range
        with pytest.raises(ValidationError):
            TavilySearchToolArgs(query="test", time_range="invalid")

    def test_max_results_validation(self) -> None:
        """Test max_results parameter validation."""
        # Valid range (1-20)
        args = TavilySearchToolArgs(query="test", max_results=1)
        assert args.max_results == 1

        args = TavilySearchToolArgs(query="test", max_results=20)
        assert args.max_results == 20

        # Invalid: too low
        with pytest.raises(ValidationError):
            TavilySearchToolArgs(query="test", max_results=0)

        # Invalid: too high
        with pytest.raises(ValidationError):
            TavilySearchToolArgs(query="test", max_results=21)

    def test_search_depth_validation(self) -> None:
        """Test search_depth parameter validation."""
        # Valid depths
        for depth in ["basic", "advanced"]:
            args = TavilySearchToolArgs(query="test", search_depth=depth)
            assert args.search_depth == depth

        # Invalid depth
        with pytest.raises(ValidationError):
            TavilySearchToolArgs(query="test", search_depth="invalid")

    def test_domain_lists(self) -> None:
        """Test include_domains and exclude_domains parameters."""
        # Empty lists
        args = TavilySearchToolArgs(
            query="test", include_domains=[], exclude_domains=[]
        )
        assert args.include_domains == []
        assert args.exclude_domains == []

        # Multiple domains
        include_domains = ["example.com", "test.org", "domain.net"]
        exclude_domains = ["spam.com", "bad.site"]
        args = TavilySearchToolArgs(
            query="test",
            include_domains=include_domains,
            exclude_domains=exclude_domains,
        )
        assert args.include_domains == include_domains
        assert args.exclude_domains == exclude_domains


class TestTavilySearchTool:
    """Test suite for TavilySearchTool functionality."""

    @pytest.fixture
    def tool(self) -> TavilySearchTool:
        """Create a TavilySearchTool instance."""
        return TavilySearchTool()

    @pytest.fixture
    def sample_search_results(self) -> list[dict]:
        """Create sample search results."""
        return [
            {
                "title": "Python Programming Guide",
                "url": "https://example.com/python-guide",
                "content": "A comprehensive guide to Python programming...",
                "score": 0.95,
            },
            {
                "title": "Python Documentation",
                "url": "https://docs.python.org",
                "content": "Official Python documentation and tutorials...",
                "score": 0.87,
            },
        ]

    def test_tool_properties(self, tool: TavilySearchTool) -> None:
        """Test tool properties are correctly set."""
        assert tool.name == "tavily_search"
        assert "Advanced web search tool powered by Tavily" in tool.description
        assert tool.args_schema == TavilySearchToolArgs

    @pytest.mark.asyncio
    async def test_successful_search(
        self, tool: TavilySearchTool, sample_search_results: list[dict]
    ) -> None:
        """Test successful search execution."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults
            mock_instance = AsyncMock()
            mock_instance.ainvoke.return_value = sample_search_results
            mock_tavily.return_value = mock_instance

            # Execute search
            result = await tool._arun(query="Python programming")

            # Verify result is valid JSON
            parsed_result = json.loads(result)
            assert parsed_result == sample_search_results

            # Verify TavilySearchResults was called correctly
            mock_tavily.assert_called_once_with(
                max_results=5,
                search_depth="basic",
                topic="general",
                include_answer=False,
                include_raw_content=False,
            )
            mock_instance.ainvoke.assert_called_once_with(
                {"query": "Python programming"}
            )

    @pytest.mark.asyncio
    async def test_search_with_all_parameters(
        self, tool: TavilySearchTool, sample_search_results: list[dict]
    ) -> None:
        """Test search with all parameters specified."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults
            mock_instance = AsyncMock()
            mock_instance.ainvoke.return_value = sample_search_results
            mock_tavily.return_value = mock_instance

            # Execute search with all parameters
            result = await tool._arun(
                query="Python news",
                topic="news",
                time_range="week",
                include_domains=["python.org"],
                exclude_domains=["spam.com"],
                max_results=10,
                search_depth="advanced",
                include_answer=True,
                include_raw_content=True,
            )

            # Verify result is valid JSON
            parsed_result = json.loads(result)
            assert parsed_result == sample_search_results

            # Verify TavilySearchResults was called with all parameters
            mock_tavily.assert_called_once_with(
                max_results=10,
                search_depth="advanced",
                topic="news",
                time_range="week",
                include_answer=True,
                include_raw_content=True,
                include_domains=["python.org"],
                exclude_domains=["spam.com"],
            )

    @pytest.mark.asyncio
    async def test_search_with_none_domains(
        self, tool: TavilySearchTool, sample_search_results: list[dict]
    ) -> None:
        """Test search with None domain parameters."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults
            mock_instance = AsyncMock()
            mock_instance.ainvoke.return_value = sample_search_results
            mock_tavily.return_value = mock_instance

            # Execute search with None domains
            result = await tool._arun(
                query="test query", include_domains=None, exclude_domains=None
            )

            # Verify result is valid JSON
            parsed_result = json.loads(result)
            assert parsed_result == sample_search_results

            # Verify TavilySearchResults was called without domain parameters
            mock_tavily.assert_called_once_with(
                max_results=5,
                search_depth="basic",
                topic="general",
                include_answer=False,
                include_raw_content=False,
            )

    @pytest.mark.asyncio
    async def test_search_with_time_range_none(
        self, tool: TavilySearchTool, sample_search_results: list[dict]
    ) -> None:
        """Test search with time_range=None does not pass time_range parameter."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults
            mock_instance = AsyncMock()
            mock_instance.ainvoke.return_value = sample_search_results
            mock_tavily.return_value = mock_instance

            # Execute search with explicit time_range=None
            result = await tool._arun(
                query="test query", time_range=None
            )

            # Verify result is valid JSON
            parsed_result = json.loads(result)
            assert parsed_result == sample_search_results

            # Verify TavilySearchResults was called without time_range parameter
            mock_tavily.assert_called_once_with(
                max_results=5,
                search_depth="basic",
                topic="general",
                include_answer=False,
                include_raw_content=False,
            )

    @pytest.mark.asyncio
    async def test_empty_search_results(self, tool: TavilySearchTool) -> None:
        """Test handling of empty search results."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults to return empty results
            mock_instance = AsyncMock()
            mock_instance.ainvoke.return_value = []
            mock_tavily.return_value = mock_instance

            # Execute search
            result = await tool._arun(query="nonexistent query")

            # Verify result is valid JSON with empty array
            parsed_result = json.loads(result)
            assert parsed_result == []

    @pytest.mark.asyncio
    async def test_search_api_error(self, tool: TavilySearchTool) -> None:
        """Test handling of API errors."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults to raise an exception
            mock_instance = AsyncMock()
            mock_instance.ainvoke.side_effect = Exception("API Error")
            mock_tavily.return_value = mock_instance

            with patch("neuron_server.tools.tavily_search_tool.logger") as mock_logger:
                # Execute search
                result = await tool._arun(query="test query")

                # Verify error message is returned
                assert result.startswith("Search error:")
                assert "API Error" in result

                # Verify error was logged
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_tavily_initialization_error(self, tool: TavilySearchTool) -> None:
        """Test handling of TavilySearchResults initialization errors."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults constructor to raise an exception
            mock_tavily.side_effect = Exception("Initialization Error")

            with patch("neuron_server.tools.tavily_search_tool.logger") as mock_logger:
                # Execute search
                result = await tool._arun(query="test query")

                # Verify error message is returned
                assert result.startswith("Search error:")
                assert "Initialization Error" in result

                # Verify error was logged
                mock_logger.error.assert_called_once()

    def test_sync_run_method(self, tool: TavilySearchTool) -> None:
        """Test synchronous _run method delegates to async _arun."""
        with (
            patch.object(tool, "_arun", return_value="mocked result"),
            patch("asyncio.run") as mock_asyncio_run,
        ):
            mock_asyncio_run.return_value = "mocked result"

            # Execute sync method
            result = tool._run(query="test query")

            # Verify result
            assert result == "mocked result"

            # Verify asyncio.run was called
            mock_asyncio_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_parameter_defaults(
        self, tool: TavilySearchTool, sample_search_results: list[dict]
    ) -> None:
        """Test parameter defaults are applied correctly."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults
            mock_instance = AsyncMock()
            mock_instance.ainvoke.return_value = sample_search_results
            mock_tavily.return_value = mock_instance

            # Execute search with minimal parameters
            await tool._arun(query="test")

            # Verify defaults were used
            mock_tavily.assert_called_once_with(
                max_results=5,  # default
                search_depth="basic",  # default
                topic="general",  # default
                include_answer=False,  # default
                include_raw_content=False,  # default
            )

    @pytest.mark.asyncio
    async def test_logging_debug_message(
        self, tool: TavilySearchTool, sample_search_results: list[dict]
    ) -> None:
        """Test debug logging is called with correct parameters."""
        with patch(
            "neuron_server.tools.tavily_search_tool.TavilySearchResults"
        ) as mock_tavily:
            # Mock TavilySearchResults
            mock_instance = AsyncMock()
            mock_instance.ainvoke.return_value = sample_search_results
            mock_tavily.return_value = mock_instance

            with patch("neuron_server.tools.tavily_search_tool.logger") as mock_logger:
                # Execute search
                await tool._arun(
                    query="Python programming",
                    topic="news",
                    time_range="week",
                    max_results=10,
                    search_depth="advanced",
                )

                # Verify debug logging was called
                mock_logger.debug.assert_called_once()
                debug_call_args = mock_logger.debug.call_args[0][0]
                assert "query='Python programming'" in debug_call_args
                assert "topic='news'" in debug_call_args
                assert "time_range='week'" in debug_call_args
                assert "max_results=10" in debug_call_args
                assert "search_depth='advanced'" in debug_call_args
