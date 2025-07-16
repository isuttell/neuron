"""Unit tests for graph_document_list_tool.py."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.runnables import RunnableConfig
from pydantic import ValidationError

from neuron_server.tools.graph_document_list_tool import (
    GraphDocumentListTool,
    GraphDocumentListToolArgs,
)


class TestGraphDocumentListToolArgs:
    """Test suite for GraphDocumentListToolArgs."""

    def test_valid_args(self) -> None:
        """Test valid argument creation."""
        args = GraphDocumentListToolArgs(search="test", limit=5)
        assert args.search == "test"
        assert args.limit == 5

    def test_default_args(self) -> None:
        """Test default argument values."""
        args = GraphDocumentListToolArgs()
        assert args.search is None
        assert args.limit == 10

    def test_limit_validation(self) -> None:
        """Test limit parameter validation."""
        # Valid limits
        args = GraphDocumentListToolArgs(limit=1)
        assert args.limit == 1

        args = GraphDocumentListToolArgs(limit=100)
        assert args.limit == 100

        # Invalid limits
        with pytest.raises(ValidationError):
            GraphDocumentListToolArgs(limit=0)

        with pytest.raises(ValidationError):
            GraphDocumentListToolArgs(limit=101)

        with pytest.raises(ValidationError):
            GraphDocumentListToolArgs(limit=-1)


class TestGraphDocumentListTool:
    """Test suite for GraphDocumentListTool."""

    def test_tool_properties(self) -> None:
        """Test tool has correct properties."""
        tool = GraphDocumentListTool()
        assert tool.name == "graph_document_list_tool"
        assert "knowledge graph" in tool.description.lower()
        assert tool.args_schema == GraphDocumentListToolArgs

    @pytest.mark.asyncio
    async def test_successful_listing_with_results(self) -> None:
        """Test successful document listing with results."""
        # Mock graph response
        mock_results = [
            {
                "d.id": "doc1",
                "d.name": "Document 1",
                "d.source": "source1",
                "d.updated_at": "2024-01-01T00:00:00Z",
            },
            {
                "d.id": "doc2",
                "d.name": "Document 2",
                "d.source": "source2",
                "d.updated_at": "2024-01-02T00:00:00Z",
            },
        ]

        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = mock_results
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(config=config, search=None, limit=10)

            # Verify result format
            assert "<document_list_result>" in result
            assert "<status>success</status>" in result
            assert "<count>2</count>" in result
            assert "<document>" in result
            assert "<id>doc1</id>" in result
            assert "<name>Document 1</name>" in result
            assert "<source>source1</source>" in result
            assert "<updated_at>2024-01-01T00:00:00Z</updated_at>" in result
            assert "<id>doc2</id>" in result

            # Verify graph query was called correctly
            mock_graph.query.assert_called_once()
            call_args = mock_graph.query.call_args
            query = call_args[0][0]
            params = call_args[1]["params"]

            assert "MATCH (d:Document)" in query
            assert "WHERE d.personality_id = $personality_id" in query
            assert "ORDER BY d.updated_at DESC" in query
            assert "LIMIT $limit" in query
            assert params["personality_id"] == "test_personality"
            assert params["limit"] == 10

    @pytest.mark.asyncio
    async def test_successful_listing_with_search(self) -> None:
        """Test successful document listing with search filter."""
        mock_results = [
            {
                "d.id": "doc1",
                "d.name": "Test Document",
                "d.source": "test_source",
                "d.updated_at": "2024-01-01T00:00:00Z",
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = mock_results
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(config=config, search="test", limit=10)

            # Verify result includes search filter
            assert "<search_filter>test</search_filter>" in result
            assert "<count>1</count>" in result

            # Verify graph query includes search filter
            call_args = mock_graph.query.call_args
            query = call_args[0][0]
            params = call_args[1]["params"]

            assert "AND (d.name CONTAINS $search OR d.source CONTAINS $search)" in query
            assert params["search"] == "test"

    @pytest.mark.asyncio
    async def test_successful_listing_empty_results(self) -> None:
        """Test successful listing with no documents found."""
        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = []
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(config=config, search=None, limit=10)

            # Verify empty result format
            assert "<document_list_result>" in result
            assert "<status>success</status>" in result
            assert "<message>No documents found</message>" in result
            assert "<count>0</count>" in result
            assert "<document>" not in result

    @pytest.mark.asyncio
    async def test_missing_personality_id(self) -> None:
        """Test error when personality_id is missing."""
        tool = GraphDocumentListTool()
        config = RunnableConfig(configurable={})

        result = await tool._arun(config=config, search=None, limit=10)

        # Verify error response
        assert "<document_list_result>" in result
        assert "<status>error</status>" in result
        assert (
            "<error_message>Missing personality_id in configuration</error_message>"
            in result
        )

    @pytest.mark.asyncio
    async def test_empty_configurable(self) -> None:
        """Test error when configurable is empty."""
        tool = GraphDocumentListTool()
        config = RunnableConfig(configurable={})

        result = await tool._arun(config=config, search=None, limit=10)

        # Verify error response
        assert "<status>error</status>" in result
        assert "personality_id" in result

    @pytest.mark.asyncio
    async def test_graph_connection_error(self) -> None:
        """Test handling of graph connection errors."""
        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_get_graph.side_effect = Exception("Connection failed")

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(config=config, search=None, limit=10)

            # Verify error response
            assert "<document_list_result>" in result
            assert "<status>error</status>" in result
            assert "<error_message>Connection failed</error_message>" in result

    @pytest.mark.asyncio
    async def test_graph_query_error(self) -> None:
        """Test handling of graph query errors."""
        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = Exception("Query failed")
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(config=config, search=None, limit=10)

            # Verify error response
            assert "<document_list_result>" in result
            assert "<status>error</status>" in result
            assert "<error_message>Query failed</error_message>" in result

    @pytest.mark.asyncio
    async def test_custom_limit(self) -> None:
        """Test listing with custom limit."""
        mock_results = [
            {
                "d.id": "doc1",
                "d.name": "Document 1",
                "d.source": "source1",
                "d.updated_at": "2024-01-01T00:00:00Z",
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = mock_results
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            await tool._arun(config=config, search=None, limit=5)

            # Verify limit parameter was passed correctly
            call_args = mock_graph.query.call_args
            params = call_args[1]["params"]
            assert params["limit"] == 5

    @pytest.mark.asyncio
    async def test_document_with_null_fields(self) -> None:
        """Test handling of documents with null/missing fields."""
        mock_results = [
            {
                "d.id": "doc1",
                "d.name": None,
                "d.source": None,
                "d.updated_at": None,
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = mock_results
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(config=config, search=None, limit=10)

            # Verify null fields are handled as N/A
            assert "<name>N/A</name>" in result
            assert "<source>N/A</source>" in result
            assert "<updated_at>N/A</updated_at>" in result

    def test_sync_run_method(self) -> None:
        """Test synchronous _run method."""
        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = []
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = tool._run(config=config, search=None, limit=10)

            # Verify sync method works
            assert "<document_list_result>" in result
            assert "<status>success</status>" in result
            assert "<count>0</count>" in result

    @pytest.mark.asyncio
    async def test_personality_id_isolation(self) -> None:
        """Test that documents are properly filtered by personality_id."""
        mock_results = [
            {
                "d.id": "doc1",
                "d.name": "Document 1",
                "d.source": "source1",
                "d.updated_at": "2024-01-01T00:00:00Z",
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = mock_results
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(
                configurable={"personality_id": "specific_personality"}
            )

            result = await tool._arun(config=config, search=None, limit=10)

            # Verify specific personality_id was used in query
            call_args = mock_graph.query.call_args
            params = call_args[1]["params"]
            assert params["personality_id"] == "specific_personality"

            # Verify result is successful
            assert "<status>success</status>" in result
            assert "<count>1</count>" in result

    @pytest.mark.asyncio
    async def test_complex_search_scenario(self) -> None:
        """Test complex search scenario with multiple matching documents."""
        mock_results = [
            {
                "d.id": "doc1",
                "d.name": "Research Paper",
                "d.source": "arxiv",
                "d.updated_at": "2024-01-03T00:00:00Z",
            },
            {
                "d.id": "doc2",
                "d.name": "User Manual",
                "d.source": "research_docs",
                "d.updated_at": "2024-01-02T00:00:00Z",
            },
            {
                "d.id": "doc3",
                "d.name": "Technical Report",
                "d.source": "research_group",
                "d.updated_at": "2024-01-01T00:00:00Z",
            },
        ]

        with patch(
            "neuron_server.tools.graph_document_list_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = mock_results
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentListTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(config=config, search="research", limit=50)

            # Verify all documents are returned
            assert "<count>3</count>" in result
            assert "<search_filter>research</search_filter>" in result
            assert "Research Paper" in result
            assert "User Manual" in result
            assert "Technical Report" in result

            # Verify query parameters
            call_args = mock_graph.query.call_args
            params = call_args[1]["params"]
            assert params["search"] == "research"
            assert params["limit"] == 50
