"""Question graph implementation and related functions."""

import ast
import json
import logging
import re
from datetime import datetime
from typing import Any, Literal, TypedDict

from langchain_community.vectorstores import Neo4jVector
from langchain_core.runnables import RunnableConfig
from langchain_openai import OpenAIEmbeddings
from langgraph.graph import END, START, StateGraph

from neuron_server.config import config

from .chains import (
    answer_reasoning_chain,
    atomic_fact_chain,
    chunk_read_chain,
    initial_nodes_chain,
    neighbor_select_chain,
    rational_chain,
)
from .connection import get_graph
from .models import (
    AtomicFactOutput,
    Chunk,
    ChunkOutput,
    InitialNodes,
    InputState,
    NeighborOutput,
    OutputState,
    OverallState,
    RationalPlanOutput,
)

logger = logging.getLogger(__name__)


class ParsedFunction(TypedDict):
    function_name: str
    arguments: list[Any]


def parse_function(input_str: str) -> ParsedFunction | None:
    """Parse function name and arguments from a string."""
    # Regular expression to capture the function name and arguments
    pattern = r"(\w+)(?:\((.*)\))?"

    match = re.match(pattern, input_str)
    if match:
        function_name = match.group(1)  # Extract the function name
        raw_arguments = match.group(2)  # Extract the arguments as a string
        # If there are arguments, attempt to parse them
        arguments = []
        if raw_arguments:
            try:
                # Use ast.literal_eval to safely evaluate and convert the arguments
                parsed_args = ast.literal_eval(
                    f"({raw_arguments})"
                )  # Wrap in tuple parentheses
                # Ensure it's always treated as a tuple even with a single argument
                arguments = (
                    list(parsed_args)
                    if isinstance(parsed_args, tuple)
                    else [parsed_args]
                )
            except (ValueError, SyntaxError):
                # In case of failure to parse, return the raw argument string
                arguments = [raw_arguments.strip()]

        return {"function_name": function_name, "arguments": arguments}
    return None


embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


async def get_potential_nodes(
    question: str, document_ids: list[str] | None = None
) -> list[str]:
    """Get potential nodes for a question using vector similarity."""
    # Load it on demand here to generate the embeddings on the fly
    # @TODO find a better way to get the embeddings created
    neo4j_vector = Neo4jVector.from_existing_graph(
        url=config.neo4j.url,
        username=config.neo4j.username,
        password=config.neo4j.password,
        embedding=embeddings,
        index_name="keyelements",
        node_label="KeyElement",
        text_node_properties=["id"],
        embedding_node_property="embedding",
        retrieval_query="""
MATCH (node:KeyElement)
    <-[:HAS_KEY_ELEMENT]-(fact)
    <-[:HAS_ATOMIC_FACT]-(chunk:Chunk)
    <-[:HAS_CHUNK]-(doc:Document)
RETURN node.id AS text, score, doc.id AS document_id, {
    document_id: doc.id,
    _embedding_: node.embedding
} AS metadata
""",
    )

    filter_query: dict[str, Any] = {}
    if document_ids:
        logger.debug(f"Filtering by document ids: {document_ids}")
        filter_query["document_id"] = {"$in": document_ids}

    # Use MMR to get the most relevant and diverse key elements
    retriver = neo4j_vector.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": 50,
            "fetch_k": 250,
            "filter": filter_query,
        },
    )
    key_elements = await retriver.ainvoke(question)
    return [el.page_content for el in key_elements]


def get_atomic_facts(
    key_elements: list[str], personality_id: str
) -> list[dict[str, Any]]:
    """Get the atomic facts for the given key elements and personality."""
    return get_graph().query(
        """
MATCH (k:KeyElement)<-[:HAS_KEY_ELEMENT]-(fact)<-[:HAS_ATOMIC_FACT]-(c:Chunk)
  <-[:HAS_CHUNK]-(doc:Document)
WHERE k.id IN $key_elements AND c.personality_id = $personality_id
RETURN DISTINCT
  doc.id AS document_id,
  doc.name AS document_name,
  doc.source AS source,
  c.id AS chunk_id,
  fact.text AS text,
  c.updated_at AS updated_at
    """.strip(),
        params={"key_elements": key_elements, "personality_id": personality_id},
    )


def get_neighbors_by_key_element(
    key_elements: list[str], personality_id: str
) -> list[dict[str, list[str]]]:
    """Get neighboring nodes for the given key elements."""
    logger.debug(f"Key elements: {key_elements}")
    return get_graph().query(
        """
    MATCH (k:KeyElement)<-[:HAS_KEY_ELEMENT]-(c:Chunk)-[:HAS_KEY_ELEMENT]->(neighbor)
    WHERE k.id IN $key_elements AND NOT neighbor.id IN $key_elements
      AND c.personality_id = $personality_id
    WITH neighbor, count(*) AS count
    ORDER BY count DESC LIMIT 50
    RETURN collect(neighbor.id) AS possible_candidates
    """.strip(),
        params={"key_elements": key_elements, "personality_id": personality_id},
    )


def get_read_chunk_ids(previous_actions: list[str]) -> list[str]:
    """Get the list of chunks that have been read from the previous actions."""
    read_chunks: list[str] = []
    for action in previous_actions:
        if action.startswith("read_chunk"):
            read_chunks.append(action.split("(")[1].split(")")[0].strip())
    return read_chunks


def get_subsequent_chunk_id(chunk_id: str, personality_id: str) -> str | None:
    """Get the ID of the subsequent chunk."""
    data = get_graph().query(
        """
MATCH (c:Chunk)-[:NEXT]->(next)
WHERE c.id = $id AND c.personality_id = $personality_id
RETURN next.id AS next
        """.strip(),
        params={"id": chunk_id, "personality_id": personality_id},
    )
    return data[0]["next"] if data else None


def get_previous_chunk_id(chunk_id: str, personality_id: str) -> str | None:
    """Get the ID of the previous chunk."""
    data = get_graph().query(
        """
MATCH (c:Chunk)<-[:NEXT]-(previous)
WHERE c.id = $id AND c.personality_id = $personality_id
RETURN previous.id AS previous
    """.strip(),
        params={"id": chunk_id, "personality_id": personality_id},
    )
    return data[0]["previous"] if data else None


def get_chunk(chunk_id: str, personality_id: str) -> Chunk | None:
    """Get chunk information from Neo4j."""
    data = get_graph().query(
        """
MATCH (c:Chunk)
WHERE c.id = $chunk_id AND c.personality_id = $personality_id
RETURN c.id AS chunk_id, c.text AS text, c.document_id AS document_id
    """.strip(),
        params={"chunk_id": chunk_id, "personality_id": personality_id},
    )
    return data[0] if data else None


async def initial_notebook(state: OverallState) -> dict[str, str]:
    """Initialize the notebook with relevant chunks."""
    neo4j_vector = Neo4jVector.from_existing_graph(
        url=config.neo4j.url,
        username=config.neo4j.username,
        password=config.neo4j.password,
        embedding=embeddings,
        index_name="chunk_index",
        node_label="Chunk",
        text_node_properties=["text", "description", "document_name"],
        embedding_node_property="embedding",
        retrieval_query="""
MATCH (node:Chunk)
RETURN node.text AS text, score, node.document_id AS document_id, {
    document_name: node.document_name,
    description: node.description,
    document_id: node.document_id,
    chunk_id: node.id,
    source: COALESCE(node.source, 'Unknown'),
    _embedding_: node.embedding
} AS metadata
""",
    )
    filter_query: dict[str, Any] = {}
    if state.get("document_ids"):
        logger.debug(f"Filtering by document ids: {state.get('document_ids')}")
        filter_query["document_id"] = {"$in": state.get("document_ids")}
    retriver = neo4j_vector.as_retriever(
        search_kwargs={
            "k": 3,
            "filter": filter_query,
        },
    )
    data = await retriver.ainvoke(state.get("question"))
    logger.info(f"Retrieved {len(data)} chunks")
    docs = "".join(
        [
            f"""\
    <chunk>
        <document_name>{el.metadata.get("document_name")}</document_name>
        <chunk_id>{el.metadata.get("chunk_id")}</chunk_id>
        <chunk_description>{el.metadata.get("description")}</chunk_description>
        <chunk_text>{el.page_content}</chunk_text>
        <chunk_source>{el.metadata.get("source", "Unknown")}</chunk_source>
    </chunk>
"""
            for el in data
        ]
    )
    notebook = f"""\
<chunks>
{docs}
</chunks>
"""
    return {
        "notebook": notebook,
    }


async def rational_plan_node(
    state: InputState, config: RunnableConfig | None = None
) -> OverallState:
    """Create a rational plan for answering the question."""
    response: RationalPlanOutput = await rational_chain.ainvoke(
        {
            "question": state.get("question"),
            "history": state.get("history"),
            "notebook": state.get("notebook"),
            "now": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
        config=config,
    )
    rational_plan = response.rational_plan
    logger.debug(f"Rational plan: {rational_plan}")
    return {
        "rational_plan": rational_plan,
        "previous_actions": ["rational_plan"],
        "chosen_action": response.chosen_action,
    }


async def initial_node_selection(
    state: OverallState, config: RunnableConfig | None = None
) -> OverallState:
    """Select initial nodes for exploration."""
    potential_nodes = await get_potential_nodes(
        state.get("question"), state.get("document_ids")
    )
    initial_nodes: InitialNodes = await initial_nodes_chain.ainvoke(
        {
            "question": state.get("question"),
            "rational_plan": state.get("rational_plan"),
            "nodes": json.dumps(potential_nodes),
        },
        config=config,
    )
    # paper uses 5 initial nodes
    check_atomic_facts_queue = [
        el.key_element
        for el in sorted(
            initial_nodes.initial_nodes,
            key=lambda node: node.score,
            reverse=True,
        )
    ][:3]
    return {
        "check_atomic_facts_queue": check_atomic_facts_queue,
        "previous_actions": ["initial_node_selection"],
    }


async def atomic_fact_check(
    state: OverallState, config: RunnableConfig
) -> OverallState:
    """Check atomic facts for relevance."""
    personality_id: str | None = config["configurable"].get("personality_id")
    assert personality_id is not None
    atomic_facts = get_atomic_facts(
        key_elements=state.get("check_atomic_facts_queue"),
        personality_id=personality_id,
    )
    logger.debug(f"Step: Atomic Fact Check ({state.get('check_atomic_facts_queue')})")
    atomic_facts_results: AtomicFactOutput = await atomic_fact_chain.ainvoke(
        {
            "question": state.get("question"),
            "rational_plan": state.get("rational_plan"),
            "notebook": state.get("notebook"),
            "previous_actions": json.dumps(state.get("previous_actions"), indent=2),
            "atomic_facts": json.dumps(atomic_facts, indent=2),
        },
        config=config,
    )

    notebook = atomic_facts_results.updated_notebook
    logger.debug(f"Next Action: {atomic_facts_results.rational_next_action}")
    chosen_action = parse_function(atomic_facts_results.chosen_action)
    if chosen_action is None:
        raise ValueError("Failed to parse chosen action")
    logger.debug(f"Chosen action: {chosen_action.get('function_name')}")
    response = {
        "notebook": notebook,
        "chosen_action": chosen_action.get("function_name"),
        "check_atomic_facts_queue": [],
        "previous_actions": [
            f"atomic_fact_check({state.get('check_atomic_facts_queue')})"
        ],
    }
    if chosen_action.get("function_name") == "stop_and_read_neighbor":
        neighbors = get_neighbors_by_key_element(
            state.get("check_atomic_facts_queue"), personality_id=personality_id
        )
        response["neighbor_check_queue"] = neighbors
    elif chosen_action.get("function_name") == "read_chunk":
        args = chosen_action.get("arguments")
        check_chunks_queue: list[str] = (
            args[0]
            if isinstance(args, list) and len(args) > 0 and isinstance(args[0], list)
            else []
        )
        read_chunks = get_read_chunk_ids(state.get("previous_actions"))
        # Filter out chunks that have already been read
        response["check_chunks_queue"] = [
            cid for cid in check_chunks_queue if cid not in read_chunks
        ]
    return response


async def chunk_check(state: OverallState, config: RunnableConfig) -> OverallState:
    """Check a chunk for relevant information."""
    personality_id: str | None = config["configurable"].get("personality_id")
    assert personality_id is not None
    check_chunks_queue = state.get("check_chunks_queue")
    if len(check_chunks_queue) == 0:
        logger.error("No chunks to check")
        return {
            "chosen_action": "stop_and_read_neighbor",
            "previous_actions": ["read_chunk(error: no chunks to check)"],
        }
    chunk_id = check_chunks_queue.pop()
    logger.debug(f"Step: read_chunk({chunk_id})")
    read_chunks = get_read_chunk_ids(state.get("previous_actions"))
    if chunk_id in read_chunks:
        logger.warning(f"Chunk {chunk_id} has already been read")
    chunk = get_chunk(chunk_id, personality_id)
    read_chunk_results: ChunkOutput = await chunk_read_chain.ainvoke(
        {
            "question": state.get("question"),
            "rational_plan": state.get("rational_plan"),
            "notebook": state.get("notebook"),
            "previous_actions": json.dumps(state.get("previous_actions"), indent=2),
            "chunk": json.dumps(chunk, indent=2) if chunk else "Unable to find a chunk",
        },
        config=config,
    )

    notebook = read_chunk_results.updated_notebook
    logger.debug(f"Next Move: {read_chunk_results.rational_next_move}")
    chosen_action = parse_function(read_chunk_results.chosen_action)
    logger.debug(f"Chosen action: {chosen_action.get('function_name')}")
    response = {
        "notebook": notebook,
        "chosen_action": chosen_action.get("function_name"),
        "previous_actions": [f"read_chunk({chunk_id})"],
    }
    if chosen_action.get("function_name") == "read_subsequent_chunk":
        subsequent_id = get_subsequent_chunk_id(chunk_id, personality_id)
        if subsequent_id:
            check_chunks_queue.append(subsequent_id)
    elif chosen_action.get("function_name") == "read_previous_chunk":
        previous_id = get_previous_chunk_id(chunk_id, personality_id)
        if previous_id:
            check_chunks_queue.append(previous_id)
    elif chosen_action.get("function_name") == "search_more":
        # Go over to next chunk
        # Else explore neighbors
        if not check_chunks_queue:
            response["chosen_action"] = "search_neighbor"
            # Get neighbors/use vector similarity
            logger.debug(f"Neighbor rational: {read_chunk_results.rational_next_move}")
            neighbors = await get_potential_nodes(
                read_chunk_results.rational_next_move, state.get("document_ids")
            )
            response["neighbor_check_queue"] = neighbors

    response["check_chunks_queue"] = check_chunks_queue
    return response


async def neighbor_select(state: OverallState, config: RunnableConfig) -> OverallState:
    """Select a neighboring node to explore."""
    logger.debug("Step: neighbor select")
    logger.debug(f"Possible candidates: {state.get('neighbor_check_queue')}")
    neighbor_select_results: NeighborOutput = await neighbor_select_chain.ainvoke(
        {
            "question": state.get("question"),
            "rational_plan": state.get("rational_plan"),
            "notebook": state.get("notebook"),
            "nodes": json.dumps(state.get("neighbor_check_queue"), indent=2),
            "previous_actions": json.dumps(state.get("previous_actions"), indent=2),
        },
        config=config,
    )
    logger.debug(f"Rational next action: {neighbor_select_results.rational_next_move}")
    chosen_action = parse_function(neighbor_select_results.chosen_action)
    logger.debug(f"Chosen action: {chosen_action}")
    # Empty neighbor select queue
    response = {
        "chosen_action": chosen_action.get("function_name"),
        "neighbor_check_queue": [],
        "previous_actions": [
            "neighbor_select("
            + (
                chosen_action.get("arguments", [""])[0]
                if chosen_action.get("arguments")
                else ""
            )
            + ")"
        ],
    }
    if chosen_action.get("function_name") == "read_neighbor_node":
        response["check_atomic_facts_queue"] = [chosen_action.get("arguments")[0]]
    return response


async def answer_reasoning(state: OverallState, config: RunnableConfig) -> OutputState:
    """Generate the final answer based on collected information."""
    logger.debug("Step: Answer")
    final_answer = await answer_reasoning_chain.ainvoke(
        {
            "now": datetime.now().astimezone().isoformat(timespec="seconds"),
            "question": state.get("question"),
            "notebook": state.get("notebook"),
        },
        config=config,
    )
    return {
        "answer": final_answer.final_answer,
        "analysis": final_answer.analyze,
        "previous_actions": ["answer_reasoning"],
    }


def atomic_fact_condition(
    state: OverallState,
) -> Literal["neighbor_select", "chunk_check"]:
    """Determine next action after atomic fact check."""
    if state.get("chosen_action") == "stop_and_read_neighbor":
        return "neighbor_select"
    if (
        state.get("chosen_action") == "read_chunk"
        and len(state.get("check_chunks_queue", [])) > 0
    ):
        return "chunk_check"
    return "neighbor_select"


def chunk_condition(
    state: OverallState,
) -> Literal["answer_reasoning", "chunk_check", "neighbor_select"]:
    """Determine next action after chunk check."""
    if state.get("chosen_action") == "termination":
        return "answer_reasoning"
    if state.get("chosen_action") in [
        "read_subsequent_chunk",
        "read_previous_chunk",
        "search_more",
    ]:
        return "chunk_check"
    if state.get("chosen_action") == "search_neighbor":
        return "neighbor_select"
    logger.error(f"Unknown action: {state.get('chosen_action')}")
    return "neighbor_select"


def neighbor_condition(
    state: OverallState,
) -> Literal["answer_reasoning", "atomic_fact_check"]:
    """Determine next action after neighbor selection."""
    if state.get("chosen_action") == "termination":
        return "answer_reasoning"
    if state.get("chosen_action") == "read_neighbor_node":
        return "atomic_fact_check"
    return "answer_reasoning"  # Default case


def rational_plan_node_condition(
    state: OverallState,
) -> Literal["initial_node_selection", "answer_reasoning"]:
    """Determine next action after rational plan creation."""
    if state.get("chosen_action") == "search_more":
        return "initial_node_selection"
    return "answer_reasoning"


# Initialize the question graph
question_graph = StateGraph(OverallState, input=InputState, output=OutputState)
question_graph.add_node(initial_notebook)
question_graph.add_node(rational_plan_node)
question_graph.add_node(initial_node_selection)
question_graph.add_node(atomic_fact_check)
question_graph.add_node(chunk_check)
question_graph.add_node(answer_reasoning)
question_graph.add_node(neighbor_select)

question_graph.add_edge(START, "initial_notebook")
question_graph.add_edge("initial_notebook", "rational_plan_node")
question_graph.add_edge("initial_node_selection", "atomic_fact_check")

question_graph.add_conditional_edges(
    "rational_plan_node",
    rational_plan_node_condition,
)

question_graph.add_conditional_edges(
    "atomic_fact_check",
    atomic_fact_condition,
)
question_graph.add_conditional_edges(
    "chunk_check",
    chunk_condition,
)
question_graph.add_conditional_edges(
    "neighbor_select",
    neighbor_condition,
)
question_graph.add_edge("answer_reasoning", END)

question_graph = question_graph.compile()
