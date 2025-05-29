"""Unit tests for graph/question.py."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.graph.models import (
    AtomicFactOutput,
    ChunkOutput,
    InitialNodes,
    NeighborOutput,
    Node,
    RationalPlanOutput,
)
from neuron_server.graph.question import (
    answer_reasoning,
    atomic_fact_check,
    atomic_fact_condition,
    chunk_check,
    chunk_condition,
    get_atomic_facts,
    get_chunk,
    get_neighbors_by_key_element,
    get_potential_nodes,
    get_previous_chunk_id,
    get_read_chunk_ids,
    get_subsequent_chunk_id,
    initial_node_selection,
    initial_notebook,
    neighbor_condition,
    neighbor_select,
    parse_function,
    rational_plan_node,
    rational_plan_node_condition,
)


class TestParseFunctionHelpers:
    """Test cases for parse_function and related helpers."""

    def test_parse_function_with_no_arguments(self) -> None:
        """Test parsing function with no arguments."""
        result = parse_function("test_function")
        assert result is not None
        assert result["function_name"] == "test_function"
        assert result["arguments"] == []

    def test_parse_function_with_single_argument(self) -> None:
        """Test parsing function with single argument."""
        result = parse_function("test_function('arg1')")
        assert result is not None
        assert result["function_name"] == "test_function"
        assert result["arguments"] == ["arg1"]

    def test_parse_function_with_multiple_arguments(self) -> None:
        """Test parsing function with multiple arguments."""
        result = parse_function("test_function('arg1', 'arg2', 123)")
        assert result is not None
        assert result["function_name"] == "test_function"
        assert result["arguments"] == ["arg1", "arg2", 123]

    def test_parse_function_with_list_argument(self) -> None:
        """Test parsing function with list argument."""
        result = parse_function("test_function(['item1', 'item2'])")
        assert result is not None
        assert result["function_name"] == "test_function"
        assert result["arguments"] == [["item1", "item2"]]

    def test_parse_function_with_invalid_syntax(self) -> None:
        """Test parsing function with invalid syntax."""
        result = parse_function("test_function(invalid syntax)")
        assert result is not None
        assert result["function_name"] == "test_function"
        assert result["arguments"] == ["invalid syntax"]

    def test_parse_function_with_empty_string(self) -> None:
        """Test parsing function with empty string."""
        result = parse_function("")
        assert result is None

    def test_get_read_chunk_ids(self) -> None:
        """Test extracting read chunk IDs from previous actions."""
        previous_actions = [
            "rational_plan",
            "read_chunk(chunk_123)",
            "atomic_fact_check(['fact1'])",
            "read_chunk(chunk_456)",
        ]
        result = get_read_chunk_ids(previous_actions)
        assert result == ["chunk_123", "chunk_456"]

    def test_get_read_chunk_ids_empty_list(self) -> None:
        """Test extracting read chunk IDs from empty list."""
        result = get_read_chunk_ids([])
        assert result == []


class TestGraphQueries:
    """Test cases for Neo4j graph query functions."""

    @patch("neuron_server.graph.question.get_graph")
    def test_get_atomic_facts(self, mock_get_graph: Mock) -> None:
        """Test getting atomic facts from graph."""
        mock_graph = Mock()
        mock_graph.query.return_value = [
            {
                "document_id": "doc1",
                "document_name": "Test Doc",
                "source": "test_source",
                "chunk_id": "chunk1",
                "text": "Test fact",
                "updated_at": "2024-01-01",
            }
        ]
        mock_get_graph.return_value = mock_graph

        result = get_atomic_facts(["key1", "key2"], "personality_id")

        mock_graph.query.assert_called_once()
        assert len(result) == 1
        assert result[0]["document_id"] == "doc1"

    @patch("neuron_server.graph.question.get_graph")
    def test_get_neighbors_by_key_element(self, mock_get_graph: Mock) -> None:
        """Test getting neighbors by key element."""
        mock_graph = Mock()
        mock_graph.query.return_value = [
            {"possible_candidates": ["neighbor1", "neighbor2"]}
        ]
        mock_get_graph.return_value = mock_graph

        result = get_neighbors_by_key_element(["key1"], "personality_id")

        assert len(result) == 1
        assert result[0]["possible_candidates"] == ["neighbor1", "neighbor2"]

    @patch("neuron_server.graph.question.get_graph")
    def test_get_subsequent_chunk_id(self, mock_get_graph: Mock) -> None:
        """Test getting subsequent chunk ID."""
        mock_graph = Mock()
        mock_graph.query.return_value = [{"next": "chunk_next"}]
        mock_get_graph.return_value = mock_graph

        result = get_subsequent_chunk_id("chunk_current", "personality_id")
        assert result == "chunk_next"

    @patch("neuron_server.graph.question.get_graph")
    def test_get_subsequent_chunk_id_not_found(self, mock_get_graph: Mock) -> None:
        """Test getting subsequent chunk ID when not found."""
        mock_graph = Mock()
        mock_graph.query.return_value = []
        mock_get_graph.return_value = mock_graph

        result = get_subsequent_chunk_id("chunk_current", "personality_id")
        assert result is None

    @patch("neuron_server.graph.question.get_graph")
    def test_get_previous_chunk_id(self, mock_get_graph: Mock) -> None:
        """Test getting previous chunk ID."""
        mock_graph = Mock()
        mock_graph.query.return_value = [{"previous": "chunk_prev"}]
        mock_get_graph.return_value = mock_graph

        result = get_previous_chunk_id("chunk_current", "personality_id")
        assert result == "chunk_prev"

    @patch("neuron_server.graph.question.get_graph")
    def test_get_chunk(self, mock_get_graph: Mock) -> None:
        """Test getting chunk information."""
        mock_graph = Mock()
        mock_graph.query.return_value = [
            {
                "chunk_id": "chunk1",
                "text": "Chunk text",
                "document_id": "doc1",
            }
        ]
        mock_get_graph.return_value = mock_graph

        result = get_chunk("chunk1", "personality_id")
        assert result is not None
        assert result["chunk_id"] == "chunk1"
        assert result["text"] == "Chunk text"

    @patch("neuron_server.graph.question.get_graph")
    def test_get_chunk_not_found(self, mock_get_graph: Mock) -> None:
        """Test getting chunk when not found."""
        mock_graph = Mock()
        mock_graph.query.return_value = []
        mock_get_graph.return_value = mock_graph

        result = get_chunk("chunk_not_exists", "personality_id")
        assert result is None


class TestVectorSearch:
    """Test cases for vector search functionality."""

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.Neo4jVector")
    async def test_get_potential_nodes(self, mock_neo4j_vector: Mock) -> None:
        """Test getting potential nodes with vector search."""
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke.return_value = [
            Mock(page_content="node1"),
            Mock(page_content="node2"),
        ]

        mock_vector_instance = Mock()
        mock_vector_instance.as_retriever.return_value = mock_retriever
        mock_neo4j_vector.from_existing_graph.return_value = mock_vector_instance

        result = await get_potential_nodes("test question")

        assert result == ["node1", "node2"]
        mock_retriever.ainvoke.assert_called_once_with("test question")

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.Neo4jVector")
    async def test_get_potential_nodes_with_document_filter(
        self, mock_neo4j_vector: Mock
    ) -> None:
        """Test getting potential nodes with document filter."""
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke.return_value = [
            Mock(page_content="node1"),
        ]

        mock_vector_instance = Mock()
        mock_vector_instance.as_retriever.return_value = mock_retriever
        mock_neo4j_vector.from_existing_graph.return_value = mock_vector_instance

        result = await get_potential_nodes("test question", ["doc1", "doc2"])

        assert result == ["node1"]
        # Verify filter was applied
        retriever_kwargs = mock_vector_instance.as_retriever.call_args[1][
            "search_kwargs"
        ]
        assert retriever_kwargs["filter"]["document_id"]["$in"] == ["doc1", "doc2"]


class TestGraphNodes:
    """Test cases for graph node functions."""

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.Neo4jVector")
    async def test_initial_notebook(self, mock_neo4j_vector: Mock) -> None:
        """Test initial notebook creation."""
        mock_retriever = AsyncMock()
        mock_retriever.ainvoke.return_value = [
            Mock(
                page_content="Test content",
                metadata={
                    "document_name": "Test Doc",
                    "chunk_id": "chunk1",
                    "description": "Test description",
                    "source": "test_source",
                },
            )
        ]

        mock_vector_instance = Mock()
        mock_vector_instance.as_retriever.return_value = mock_retriever
        mock_neo4j_vector.from_existing_graph.return_value = mock_vector_instance

        state = {"question": "test question"}
        result = await initial_notebook(state)

        assert "notebook" in result
        assert "Test Doc" in result["notebook"]
        assert "chunk1" in result["notebook"]
        assert "Test content" in result["notebook"]

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.rational_chain")
    async def test_rational_plan_node(self, mock_rational_chain: Mock) -> None:
        """Test rational plan node execution."""
        mock_response = RationalPlanOutput(
            rational_plan="Test plan",
            chosen_action="search_more"
        )
        mock_rational_chain.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "question": "test question",
            "history": [],
            "notebook": "test notebook",
        }
        config = RunnableConfig(configurable={})

        result = await rational_plan_node(state, config)

        assert result["rational_plan"] == "Test plan"
        assert result["chosen_action"] == "search_more"
        assert result["previous_actions"] == ["rational_plan"]

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.get_potential_nodes")
    @patch("neuron_server.graph.question.initial_nodes_chain")
    async def test_initial_node_selection(
        self, mock_initial_nodes_chain: Mock, mock_get_potential_nodes: Mock
    ) -> None:
        """Test initial node selection."""
        mock_get_potential_nodes.return_value = ["node1", "node2", "node3"]

        mock_nodes = InitialNodes(
            initial_nodes=[
                Node(key_element="node1", score=90),
                Node(key_element="node2", score=80),
                Node(key_element="node3", score=70),
                Node(key_element="node4", score=60),
            ]
        )
        mock_initial_nodes_chain.ainvoke = AsyncMock(return_value=mock_nodes)

        state = {
            "question": "test question",
            "rational_plan": "test plan",
        }
        config = RunnableConfig(configurable={})

        result = await initial_node_selection(state, config)

        # Should select top 3 nodes
        assert len(result["check_atomic_facts_queue"]) == 3  # noqa: PLR2004
        assert result["check_atomic_facts_queue"] == ["node1", "node2", "node3"]
        assert result["previous_actions"] == ["initial_node_selection"]

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.get_atomic_facts")
    @patch("neuron_server.graph.question.atomic_fact_chain")
    @patch("neuron_server.graph.question.get_neighbors_by_key_element")
    async def test_atomic_fact_check_with_neighbor_action(
        self,
        mock_get_neighbors: Mock,
        mock_atomic_fact_chain: Mock,
        mock_get_atomic_facts: Mock,
    ) -> None:
        """Test atomic fact check with stop_and_read_neighbor action."""
        mock_get_atomic_facts.return_value = [{"text": "test fact"}]
        mock_get_neighbors.return_value = [{"possible_candidates": ["neighbor1"]}]

        mock_response = AtomicFactOutput(
            updated_notebook="Updated notebook",
            rational_next_action="Read neighbor",
            chosen_action="stop_and_read_neighbor"
        )
        mock_atomic_fact_chain.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "question": "test question",
            "rational_plan": "test plan",
            "notebook": "test notebook",
            "check_atomic_facts_queue": ["key1"],
            "previous_actions": [],
        }
        config = RunnableConfig(configurable={"personality_id": "test_personality"})

        result = await atomic_fact_check(state, config)

        assert result["notebook"] == "Updated notebook"
        assert result["chosen_action"] == "stop_and_read_neighbor"
        assert result["neighbor_check_queue"] == [
            {"possible_candidates": ["neighbor1"]}
        ]

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.get_chunk")
    @patch("neuron_server.graph.question.chunk_read_chain")
    @patch("neuron_server.graph.question.get_subsequent_chunk_id")
    async def test_chunk_check_with_subsequent(
        self,
        mock_get_subsequent: Mock,
        mock_chunk_read_chain: Mock,
        mock_get_chunk: Mock,
    ) -> None:
        """Test chunk check with read_subsequent_chunk action."""
        mock_get_chunk.return_value = {"chunk_id": "chunk1", "text": "Test chunk"}
        mock_get_subsequent.return_value = "chunk2"

        mock_response = ChunkOutput(
            updated_notebook="Updated notebook",
            rational_next_move="Read next chunk",
            chosen_action="read_subsequent_chunk"
        )
        mock_chunk_read_chain.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "question": "test question",
            "rational_plan": "test plan",
            "notebook": "test notebook",
            "check_chunks_queue": ["chunk1"],
            "previous_actions": [],
        }
        config = RunnableConfig(configurable={"personality_id": "test_personality"})

        result = await chunk_check(state, config)

        assert result["notebook"] == "Updated notebook"
        assert result["chosen_action"] == "read_subsequent_chunk"
        assert result["check_chunks_queue"] == ["chunk2"]

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.neighbor_select_chain")
    async def test_neighbor_select(self, mock_neighbor_select_chain: Mock) -> None:
        """Test neighbor selection."""
        mock_response = NeighborOutput(
            rational_next_move="Select neighbor node",
            chosen_action="read_neighbor_node('neighbor1')"
        )
        mock_neighbor_select_chain.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "question": "test question",
            "rational_plan": "test plan",
            "notebook": "test notebook",
            "neighbor_check_queue": ["neighbor1", "neighbor2"],
            "previous_actions": [],
        }
        config = RunnableConfig(configurable={})

        result = await neighbor_select(state, config)

        assert result["chosen_action"] == "read_neighbor_node"
        assert result["check_atomic_facts_queue"] == ["neighbor1"]
        assert "neighbor_select(neighbor1)" in result["previous_actions"][0]

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.answer_reasoning_chain")
    async def test_answer_reasoning(self, mock_answer_reasoning_chain: Mock) -> None:
        """Test answer reasoning node."""
        mock_response = Mock(
            final_answer="Final answer text",
            analyze="Analysis text"
        )
        mock_answer_reasoning_chain.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "question": "test question",
            "notebook": "test notebook",
        }
        config = RunnableConfig(configurable={})

        result = await answer_reasoning(state, config)

        assert result["answer"] == "Final answer text"
        assert result["analysis"] == "Analysis text"
        assert result["previous_actions"] == ["answer_reasoning"]


class TestConditionFunctions:
    """Test cases for condition functions."""

    def test_atomic_fact_condition_neighbor(self) -> None:
        """Test atomic fact condition returns neighbor_select."""
        state = {"chosen_action": "stop_and_read_neighbor"}
        assert atomic_fact_condition(state) == "neighbor_select"

    def test_atomic_fact_condition_chunk(self) -> None:
        """Test atomic fact condition returns chunk_check."""
        state = {
            "chosen_action": "read_chunk",
            "check_chunks_queue": ["chunk1"],
        }
        assert atomic_fact_condition(state) == "chunk_check"

    def test_atomic_fact_condition_default(self) -> None:
        """Test atomic fact condition default case."""
        state = {"chosen_action": "unknown"}
        assert atomic_fact_condition(state) == "neighbor_select"

    def test_chunk_condition_termination(self) -> None:
        """Test chunk condition returns answer_reasoning."""
        state = {"chosen_action": "termination"}
        assert chunk_condition(state) == "answer_reasoning"

    def test_chunk_condition_continue_chunk(self) -> None:
        """Test chunk condition returns chunk_check."""
        for action in ["read_subsequent_chunk", "read_previous_chunk", "search_more"]:
            state = {"chosen_action": action}
            assert chunk_condition(state) == "chunk_check"

    def test_chunk_condition_neighbor(self) -> None:
        """Test chunk condition returns neighbor_select."""
        state = {"chosen_action": "search_neighbor"}
        assert chunk_condition(state) == "neighbor_select"

    def test_neighbor_condition_termination(self) -> None:
        """Test neighbor condition returns answer_reasoning."""
        state = {"chosen_action": "termination"}
        assert neighbor_condition(state) == "answer_reasoning"

    def test_neighbor_condition_read_neighbor(self) -> None:
        """Test neighbor condition returns atomic_fact_check."""
        state = {"chosen_action": "read_neighbor_node"}
        assert neighbor_condition(state) == "atomic_fact_check"

    def test_rational_plan_condition_search_more(self) -> None:
        """Test rational plan condition returns initial_node_selection."""
        state = {"chosen_action": "search_more"}
        assert rational_plan_node_condition(state) == "initial_node_selection"

    def test_rational_plan_condition_default(self) -> None:
        """Test rational plan condition default case."""
        state = {"chosen_action": "termination"}
        assert rational_plan_node_condition(state) == "answer_reasoning"


class TestEdgeCases:
    """Test cases for edge cases and error handling."""

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.get_chunk")
    async def test_chunk_check_empty_queue(self, mock_get_chunk: Mock) -> None:
        """Test chunk check with empty queue."""
        state = {
            "check_chunks_queue": [],
            "previous_actions": [],
        }
        config = RunnableConfig(configurable={"personality_id": "test_personality"})

        result = await chunk_check(state, config)

        assert result["chosen_action"] == "stop_and_read_neighbor"
        assert "error: no chunks to check" in result["previous_actions"][0]

    @pytest.mark.asyncio
    @patch("neuron_server.graph.question.get_chunk")
    @patch("neuron_server.graph.question.chunk_read_chain")
    @patch("neuron_server.graph.question.get_potential_nodes")
    async def test_chunk_check_search_more_empty_queue(
        self,
        mock_get_potential_nodes: Mock,
        mock_chunk_read_chain: Mock,
        mock_get_chunk: Mock,
    ) -> None:
        """Test chunk check with search_more action and empty queue."""
        mock_get_chunk.return_value = {"chunk_id": "chunk1", "text": "Test chunk"}
        mock_get_potential_nodes.return_value = ["node1", "node2"]

        mock_response = ChunkOutput(
            updated_notebook="Updated notebook",
            rational_next_move="Search for more",
            chosen_action="search_more"
        )
        mock_chunk_read_chain.ainvoke = AsyncMock(return_value=mock_response)

        state = {
            "question": "test question",
            "rational_plan": "test plan",
            "notebook": "test notebook",
            "check_chunks_queue": ["chunk1"],
            "previous_actions": [],
            "document_ids": None,
        }
        config = RunnableConfig(configurable={"personality_id": "test_personality"})

        result = await chunk_check(state, config)

        # When search_more and queue is empty, should switch to search_neighbor
        assert result["chosen_action"] == "search_neighbor"
        assert result["neighbor_check_queue"] == ["node1", "node2"]
