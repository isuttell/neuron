"""Unit tests for graph_document_delete_tool.py."""

from unittest.mock import Mock, patch

import pytest
from langchain_core.runnables import RunnableConfig
from pydantic import ValidationError

from neuron_server.tools.graph_document_delete_tool import (
    GraphDocumentDeleteTool,
    GraphDocumentDeleteToolArgs,
)


class TestGraphDocumentDeleteToolArgs:
    """Test suite for GraphDocumentDeleteToolArgs."""

    def test_valid_args(self) -> None:
        """Test valid argument creation."""
        args = GraphDocumentDeleteToolArgs(document_id="doc123")
        assert args.document_id == "doc123"

    def test_empty_document_id(self) -> None:
        """Test validation with empty document_id."""
        with pytest.raises(ValidationError):
            GraphDocumentDeleteToolArgs(document_id="")

    def test_missing_document_id(self) -> None:
        """Test validation with missing document_id."""
        with pytest.raises(ValidationError):
            GraphDocumentDeleteToolArgs()


class TestGraphDocumentDeleteTool:
    """Test suite for GraphDocumentDeleteTool."""

    def test_tool_properties(self) -> None:
        """Test tool has correct properties."""
        tool = GraphDocumentDeleteTool()
        assert tool.name == "graph_document_delete_tool"
        assert "knowledge graph" in tool.description.lower()
        assert "irreversible" in tool.description.lower()
        assert tool.args_schema == GraphDocumentDeleteToolArgs

    @pytest.mark.asyncio
    async def test_successful_deletion(self) -> None:
        """Test successful document deletion."""
        # Mock check query result
        check_result = [
            {
                "d.id": "doc123",
                "d.name": "Test Document",
                "d.source": "test_source",
            }
        ]

        # Mock deletion query result
        delete_result = [
            {
                "chunk_count": 5,
                "fact_count": 15,
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = [check_result, delete_result]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify result format
            assert "<document_delete_result>" in result
            assert "<status>success</status>" in result
            assert "<message>Document successfully deleted</message>" in result
            assert "<deleted_document>" in result
            assert "<id>doc123</id>" in result
            assert "<name>Test Document</name>" in result
            assert "<source>test_source</source>" in result
            assert "<deletion_summary>" in result
            assert "<documents_deleted>1</documents_deleted>" in result
            assert "<chunks_deleted>5</chunks_deleted>" in result
            assert "<facts_deleted>15</facts_deleted>" in result
            assert "<total_nodes_deleted>21</total_nodes_deleted>" in result

            # Verify graph queries were called correctly
            assert mock_graph.query.call_count == 2

            # Check first query (check document exists)
            first_call = mock_graph.query.call_args_list[0]
            check_query = first_call[0][0]
            check_params = first_call[1]["params"]
            assert (
                "MATCH (d:Document {id: $document_id, personality_id: $personality_id})"
                in check_query
            )
            assert "RETURN d.id, d.name, d.source" in check_query
            assert check_params["document_id"] == "doc123"
            assert check_params["personality_id"] == "test_personality"

            # Check second query (delete document)
            second_call = mock_graph.query.call_args_list[1]
            delete_query = second_call[0][0]
            delete_params = second_call[1]["params"]
            assert (
                "MATCH (d:Document {id: $document_id, personality_id: $personality_id})"
                in delete_query
            )
            assert "DETACH DELETE d" in delete_query
            assert "RETURN chunk_count, fact_count" in delete_query
            assert delete_params["document_id"] == "doc123"
            assert delete_params["personality_id"] == "test_personality"

    @pytest.mark.asyncio
    async def test_document_not_found(self) -> None:
        """Test deletion when document doesn't exist."""
        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = []  # No document found
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="nonexistent", config=config)

            # Verify error response
            assert "<document_delete_result>" in result
            assert "<status>error</status>" in result
            assert (
                "<error_message>Document not found or access denied. "
                "Document ID: nonexistent</error_message>" in result
            )

            # Verify only check query was called
            assert mock_graph.query.call_count == 1

    @pytest.mark.asyncio
    async def test_permission_denied_different_personality(self) -> None:
        """Test deletion when document belongs to different personality."""
        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.return_value = []  # No document found for this personality
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(
                configurable={"personality_id": "wrong_personality"}
            )

            result = await tool._arun(document_id="doc123", config=config)

            # Verify error response
            assert "<document_delete_result>" in result
            assert "<status>error</status>" in result
            assert "Document not found or access denied" in result

    @pytest.mark.asyncio
    async def test_missing_personality_id(self) -> None:
        """Test error when personality_id is missing."""
        tool = GraphDocumentDeleteTool()
        config = RunnableConfig(configurable={})

        result = await tool._arun(document_id="doc123", config=config)

        # Verify error response
        assert "<document_delete_result>" in result
        assert "<status>error</status>" in result
        assert (
            "<error_message>Missing personality_id in configuration</error_message>"
            in result
        )

    @pytest.mark.asyncio
    async def test_graph_connection_error(self) -> None:
        """Test handling of graph connection errors."""
        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_get_graph.side_effect = Exception("Connection failed")

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify error response
            assert "<document_delete_result>" in result
            assert "<status>error</status>" in result
            assert "<error_message>Connection failed</error_message>" in result
            assert "<document_id>doc123</document_id>" in result

    @pytest.mark.asyncio
    async def test_check_query_error(self) -> None:
        """Test handling of check query errors."""
        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = Exception("Query failed")
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify error response
            assert "<document_delete_result>" in result
            assert "<status>error</status>" in result
            assert "<error_message>Query failed</error_message>" in result

    @pytest.mark.asyncio
    async def test_deletion_query_error(self) -> None:
        """Test handling of deletion query errors."""
        # Mock successful check query
        check_result = [
            {
                "d.id": "doc123",
                "d.name": "Test Document",
                "d.source": "test_source",
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            # First call succeeds, second call fails
            mock_graph.query.side_effect = [check_result, Exception("Delete failed")]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify error response
            assert "<document_delete_result>" in result
            assert "<status>error</status>" in result
            assert "<error_message>Delete failed</error_message>" in result

    @pytest.mark.asyncio
    async def test_deletion_failed_no_results(self) -> None:
        """Test handling when deletion query returns no results."""
        # Mock successful check query
        check_result = [
            {
                "d.id": "doc123",
                "d.name": "Test Document",
                "d.source": "test_source",
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            # First call succeeds, second call returns empty results
            mock_graph.query.side_effect = [check_result, []]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify error response
            assert "<document_delete_result>" in result
            assert "<status>error</status>" in result
            assert (
                "<error_message>Failed to delete document: doc123</error_message>"
                in result
            )

    @pytest.mark.asyncio
    async def test_document_with_null_fields(self) -> None:
        """Test deletion of document with null fields."""
        check_result = [
            {
                "d.id": "doc123",
                "d.name": None,
                "d.source": None,
            }
        ]

        delete_result = [
            {
                "chunk_count": 0,
                "fact_count": 0,
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = [check_result, delete_result]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify null fields are handled as N/A
            assert "<name>N/A</name>" in result
            assert "<source>N/A</source>" in result
            assert "<chunks_deleted>0</chunks_deleted>" in result
            assert "<facts_deleted>0</facts_deleted>" in result
            assert "<total_nodes_deleted>1</total_nodes_deleted>" in result

    @pytest.mark.asyncio
    async def test_document_with_many_chunks_and_facts(self) -> None:
        """Test deletion of document with many chunks and facts."""
        check_result = [
            {
                "d.id": "doc123",
                "d.name": "Large Document",
                "d.source": "large_source",
            }
        ]

        delete_result = [
            {
                "chunk_count": 100,
                "fact_count": 500,
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = [check_result, delete_result]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify large numbers are handled correctly
            assert "<chunks_deleted>100</chunks_deleted>" in result
            assert "<facts_deleted>500</facts_deleted>" in result
            assert (
                "<total_nodes_deleted>601</total_nodes_deleted>" in result
            )  # 1 + 100 + 500

    def test_sync_run_method(self) -> None:
        """Test synchronous _run method."""
        check_result = [
            {
                "d.id": "doc123",
                "d.name": "Test Document",
                "d.source": "test_source",
            }
        ]

        delete_result = [
            {
                "chunk_count": 2,
                "fact_count": 5,
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = [check_result, delete_result]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = tool._run(document_id="doc123", config=config)

            # Verify sync method works
            assert "<document_delete_result>" in result
            assert "<status>success</status>" in result
            assert "<total_nodes_deleted>8</total_nodes_deleted>" in result

    @pytest.mark.asyncio
    async def test_personality_id_isolation(self) -> None:
        """Test that deletion is properly isolated by personality_id."""
        check_result = [
            {
                "d.id": "doc123",
                "d.name": "Private Document",
                "d.source": "private_source",
            }
        ]

        delete_result = [
            {
                "chunk_count": 3,
                "fact_count": 8,
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = [check_result, delete_result]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(
                configurable={"personality_id": "specific_personality"}
            )

            result = await tool._arun(document_id="doc123", config=config)

            # Verify both queries used the specific personality_id
            assert mock_graph.query.call_count == 2

            for call in mock_graph.query.call_args_list:
                params = call[1]["params"]
                assert params["personality_id"] == "specific_personality"
                assert params["document_id"] == "doc123"

            # Verify successful deletion
            assert "<status>success</status>" in result

    @pytest.mark.asyncio
    async def test_missing_chunk_count_in_result(self) -> None:
        """Test handling when deletion result is missing chunk_count."""
        check_result = [
            {
                "d.id": "doc123",
                "d.name": "Test Document",
                "d.source": "test_source",
            }
        ]

        delete_result = [
            {
                "fact_count": 5,
                # chunk_count is missing
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = [check_result, delete_result]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify default value is used for missing chunk_count
            assert "<chunks_deleted>0</chunks_deleted>" in result
            assert "<facts_deleted>5</facts_deleted>" in result
            assert "<total_nodes_deleted>6</total_nodes_deleted>" in result

    @pytest.mark.asyncio
    async def test_missing_fact_count_in_result(self) -> None:
        """Test handling when deletion result is missing fact_count."""
        check_result = [
            {
                "d.id": "doc123",
                "d.name": "Test Document",
                "d.source": "test_source",
            }
        ]

        delete_result = [
            {
                "chunk_count": 3,
                # fact_count is missing
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = [check_result, delete_result]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id="doc123", config=config)

            # Verify default value is used for missing fact_count
            assert "<chunks_deleted>3</chunks_deleted>" in result
            assert "<facts_deleted>0</facts_deleted>" in result
            assert "<total_nodes_deleted>4</total_nodes_deleted>" in result

    @pytest.mark.asyncio
    async def test_special_characters_in_document_id(self) -> None:
        """Test deletion with special characters in document_id."""
        special_doc_id = "doc:123/test-document_v2.1"
        check_result = [
            {
                "d.id": special_doc_id,
                "d.name": "Special Document",
                "d.source": "special_source",
            }
        ]

        delete_result = [
            {
                "chunk_count": 1,
                "fact_count": 2,
            }
        ]

        with patch(
            "neuron_server.tools.graph_document_delete_tool.get_graph"
        ) as mock_get_graph:
            mock_graph = Mock()
            mock_graph.query.side_effect = [check_result, delete_result]
            mock_get_graph.return_value = mock_graph

            tool = GraphDocumentDeleteTool()
            config = RunnableConfig(configurable={"personality_id": "test_personality"})

            result = await tool._arun(document_id=special_doc_id, config=config)

            # Verify special characters are handled correctly
            assert f"<id>{special_doc_id}</id>" in result
            assert "<status>success</status>" in result

            # Verify queries received the correct document_id
            for call in mock_graph.query.call_args_list:
                params = call[1]["params"]
                assert params["document_id"] == special_doc_id
