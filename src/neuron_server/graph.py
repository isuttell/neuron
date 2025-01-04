from langchain_neo4j import Neo4jGraph
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from neuron_server.config import config
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import List, Dict, Any, TypedDict, Annotated, Literal, Optional
import asyncio
from langchain_text_splitters import TokenTextSplitter
import hashlib
from neuron_server.logger import logger
from operator import add
from langgraph.graph import StateGraph, START, END
from langchain_community.vectorstores import Neo4jVector
import re
import ast
from langchain_core.runnables import RunnableConfig
import time
from datetime import datetime
import json
from langchain_core.prompts import PromptTemplate

graph = Neo4jGraph(
    url=config.neo4j.url,
    username=config.neo4j.username,
    password=config.neo4j.password,
    enhanced_schema=True,
)

# Add indexes if they don't exist
index_queries = [
    # Document indexes
    "CREATE INDEX document_name_idx IF NOT EXISTS FOR (d:Document) ON (d.name)",
    "CREATE INDEX document_source_idx IF NOT EXISTS FOR (d:Document) ON (d.source)",
    "CREATE INDEX document_personality_idx IF NOT EXISTS FOR (d:Document) ON (d.personality_id)",
    "CREATE INDEX document_user_idx IF NOT EXISTS FOR (d:Document) ON (d.user_id)",
    # Chunk indexes
    "CREATE INDEX chunk_personality_idx IF NOT EXISTS FOR (c:Chunk) ON (c.personality_id)",
    "CREATE INDEX chunk_document_idx IF NOT EXISTS FOR (c:Chunk) ON (c.document_id)",
    "CREATE INDEX chunk_user_idx IF NOT EXISTS FOR (c:Chunk) ON (c.user_id)",
    # AtomicFact indexes
    "CREATE INDEX atomic_fact_id_idx IF NOT EXISTS FOR (a:AtomicFact) ON (a.id)",
    "CREATE INDEX atomic_fact_text_idx IF NOT EXISTS FOR (a:AtomicFact) ON (a.text)",
    # KeyElement index
    "CREATE INDEX key_element_id_idx IF NOT EXISTS FOR (k:KeyElement) ON (k.id)",
]

for query in index_queries:
    try:
        graph.query(query)
    except Exception as e:
        logger.error(f"Error creating index: {str(e)}")

logger.debug(f"Connected to Neo4j at {config.neo4j.url}")

construction_system = """
You are now an intelligent assistant tasked with meticulously extracting both key elements and atomic facts from a long text.
1. Key Elements: The essential nouns (e.g., characters, times, events, places, numbers), verbs (e.g., actions), and adjectives (e.g., states, feelings) that are pivotal to the text's narrative.
2. Atomic Facts: The smallest, indivisible facts, presented as concise sentences. These include propositions, theories, existences, concepts, and implicit elements like logic, causality, event sequences, interpersonal relationships, timelines, etc.

Requirements:
1. Ensure that all identified key elements are reflected within the corresponding atomic facts.
2. You should extract key elements and atomic facts comprehensively, especially those that are important and potentially query-worthy and do not leave out details.
3. Whenever applicable, replace pronouns with their specific noun counterparts (e.g., change I, He, She to actual names).
4. Ensure that the key elements and atomic facts you extract are presented in the same language as the original text (e.g., English or Chinese).
""".strip()

construction_human = (
    "Use the given format to extract information from the following input: {input}"
)

construction_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            construction_system,
        ),
        ("human", construction_human),
    ]
)

import_query = """
MERGE (d:Document {id:$document_id})
SET d.name = $document_name,
    d.personality_id = $personality_id,
    d.user_id = $user_id,
    d.source = $source,
    d.updated_at = $updated_at
WITH d
UNWIND $data AS row
MERGE (c:Chunk {id: row.chunk_id})
SET c.text = row.chunk_text,
    c.index = row.index,
    c.description = row.description,
    c.document_id = $document_id,
    c.document_name = $document_name,
    c.personality_id = $personality_id,
    c.user_id = $user_id,
    c.source = $source,
    c.updated_at = $updated_at
MERGE (d)-[:HAS_CHUNK]->(c)
WITH c, row
UNWIND row.atomic_facts AS af
MERGE (a:AtomicFact {id: af.id})
SET a.text = af.atomic_fact, a.updated_at = $updated_at
MERGE (c)-[:HAS_ATOMIC_FACT]->(a)
WITH c, a, af
UNWIND af.key_elements AS ke
MERGE (k:KeyElement {id: ke})
MERGE (a)-[:HAS_KEY_ELEMENT]->(k)
""".strip()

match_query = """MATCH (c:Chunk) WHERE c.document_id = $document_id
WITH c ORDER BY c.index WITH collect(c) AS nodes
UNWIND range(0, size(nodes) -2) AS index
WITH nodes[index] AS start, nodes[index + 1] AS end
MERGE (start)-[:NEXT]->(end)
""".strip()


class AtomicFact(BaseModel):
    key_elements: List[str] = Field(
        description="""The essential nouns (e.g., characters, times, events, places, numbers), verbs (e.g.,actions), and adjectives (e.g., states, feelings) that are pivotal to the atomic fact's narrative."""
    )
    atomic_fact: str = Field(
        description="""The smallest, indivisible facts, presented as concise sentences. These include propositions, theories, existences, concepts, and implicit elements like logic, causality, event sequences, interpersonal relationships, timelines, etc."""
    )


class Extraction(BaseModel):
    description: str = Field(
        description="A short description of the extracted information"
    )
    atomic_facts: List[AtomicFact] = Field(description="List of atomic facts")


model = ChatOpenAI(model="gpt-4o-2024-11-20", temperature=0.3, max_tokens=None)
# model = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0.3)
structured_llm = model.with_structured_output(Extraction)

construction_chain = construction_prompt | structured_llm


class SummaryResponse(BaseModel):
    summary: str = Field(description="A short summary of the extracted information")
    critical_analysis: str = Field(
        description="A detailed critical analysis of the extracted information. Identify inconsistencies and contradictions. Consider any biases or limitations. How trustworthy is the information? Is there evidence and supporting facts? What is the significance of the information? Provide future research recommendations if relevant."
    )
    keywords: List[str] = Field(
        description="A list of informative keywords or concepts that are important to the extracted information"
    )


summary_chain = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are an intelligent assistant for summarizing information. You will be given a series of summaries of extracted information from a previous step, and you need to combine them into a single summary giving a high level overview of all the information.",
        ),
        ("human", "{input}"),
    ]
) | model.with_structured_output(SummaryResponse)


def encode_md5(text: str) -> str:
    """Convert a string to an MD5 hash."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def import_chunks(
    texts: List[str],
    extractions: List[Extraction],
    document_id: str,
    document_name: Optional[str] = None,
    personality_id: Optional[str] = None,
    user_id: Optional[str] = None,
    source: Optional[str] = None,
):
    docs: List[Dict[str, Any]] = [extraction.model_dump() for extraction in extractions]
    for index, doc in enumerate(docs):
        doc["chunk_id"] = encode_md5(texts[index])
        doc["chunk_text"] = texts[index]
        doc["index"] = index
        for af in doc["atomic_facts"]:
            af["id"] = encode_md5(af["atomic_fact"])

    graph.query(
        import_query,
        params={
            "data": docs,
            "document_id": document_id,
            "document_name": document_name,
            "personality_id": personality_id,
            "user_id": user_id,
            "source": source,
            "updated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        },
    )

    graph.query(match_query, params={"document_id": document_id})
    graph.refresh_schema()


async def process_chunk(
    input: str,
    index: int,
    config: Optional[RunnableConfig],
    semaphore: asyncio.Semaphore,
    attempts: int = 3,
    retry_delay_seconds: int = 1,
) -> Extraction:
    start_time = time.perf_counter()
    async with semaphore:
        # Retry so we don't break the entire import if one chunk fails
        for attempt in range(attempts):
            try:
                results: Extraction = await construction_chain.ainvoke(
                    input, config=config
                )
                logger.debug(
                    f"Found {len(results.atomic_facts)} atomic facts for chunk #{index} - {time.perf_counter() - start_time:.2f}s"
                )
                return results
            except Exception as e:
                if attempt < attempts - 1:
                    logger.warning(
                        f"Error while processing chunk {index}: {str(e)}. Retrying in {retry_delay_seconds} seconds..."
                    )
                    await asyncio.sleep(retry_delay_seconds)
                else:
                    raise e


class DocumentResult(BaseModel):
    document_id: str = Field(description="The ID of the document")
    document_name: Optional[str] = Field(description="The name of the document")
    source: Optional[str] = Field(description="The source of the document")
    keywords: List[str] = Field(description="The keywords of the document")
    summary: str = Field(description="The summary of the document")
    analysis: str = Field(description="The analysis of the document")


async def process_document(
    text: str,
    config: RunnableConfig,
    document_id: str,
    document_name: Optional[str] = None,
    source: Optional[str] = None,
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
):
    start_time = time.perf_counter()
    logger.debug(f"Started graph extraction...")
    personality_id: Optional[str] = config["configurable"].get("personality_id")
    assert personality_id is not None
    user_id: Optional[str] = config["configurable"].get("user_id")
    assert user_id is not None

    text_splitter = TokenTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap
    )
    texts = text_splitter.split_text(text)

    # Limit to 10 concurrent tasks
    semaphore = asyncio.Semaphore(10)
    logger.debug(f"Extracting atomic facts from {len(texts)} text chunks")
    extractions: List[Extraction] = await asyncio.gather(
        *[
            process_chunk(input=input, config=config, semaphore=semaphore, index=index)
            for index, input in enumerate(texts)
        ]
    )

    import_chunks(
        texts=texts,
        extractions=extractions,
        document_id=document_id,
        document_name=document_name,
        source=source,
        personality_id=personality_id,
        user_id=user_id,
    )

    summary_response: SummaryResponse = await summary_chain.ainvoke(
        {
            "input": "\n\n".join(
                [extraction.description for extraction in extractions]
            ),
        }
    )
    logger.debug(f"Finished graph extraction - {time.perf_counter() - start_time:.2f}s")
    return DocumentResult(
        document_id=document_id,
        document_name=document_name,
        source=source,
        keywords=summary_response.keywords,
        summary=summary_response.summary,
        analysis=summary_response.critical_analysis,
    )


class InputState(TypedDict):
    question: str
    history: str


class OutputState(TypedDict):
    answer: str
    analysis: str
    previous_actions: List[str]


class OverallState(TypedDict):
    history: str
    question: str
    rational_plan: str
    notebook: str
    previous_actions: Annotated[List[str], add]
    check_atomic_facts_queue: List[str]
    check_chunks_queue: List[str]
    neighbor_check_queue: List[str]
    chosen_action: str


def parse_function(input_str):
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
    else:
        return None


rational_plan_system = """As an intelligent assistant with access to a knowledge graph database, your primary objective is to answer the following question by gathering supporting facts from various articles using the notebook as a starting point. To facilitate this objective, the first step is to make a rational plan based on the question. This plan should outline the step-by-step process, in a few steps as possible, to resolve the question and specify the key information required to formulate a comprehensive answer. Use the message history if you need more context for the user's question. Do not answer the question, only make a plan to follow and determine the next action.

Now: {now}

Message History:
\"\"\"
{history}
\"\"\"

Basic Example:
#####
User: Who had a longer tennis career, Danny or Alice?
Assistant: In order to answer this question, we first need to find the length of Danny's and Alice's tennis careers, such as the start and retirement of their careers, and then compare the two.
#####

Notebook:
\"\"\"
{notebook}
\"\"\"
""".strip()

rational_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            rational_plan_system,
        ),
        (
            "human",
            ("{question}"),
        ),
    ]
)


class RationalPlanOutput(BaseModel):
    rational_plan: str = Field(
        description="The step by step rational plan to answer the question. It should be in second person and concise"
    )
    chosen_action: str = Field(
        description="""
1. search_more(): Choose this action if you think that the essential information necessary to answer the question is still lacking.
2. terminate(): Choose this action if you believe that the information you have currently obtained is enough to answer the question. This will allow you to summarize the gathered information and provide a final answer.
""".strip()
    )


rational_chain = rational_prompt | model.with_structured_output(RationalPlanOutput)


async def rational_plan_node(
    state: InputState, config: RunnableConfig = None
) -> OverallState:
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


embeddings = OpenAIEmbeddings(model="text-embedding-3-large")


async def get_potential_nodes(question: str) -> List[str]:
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
        retrieval_query="RETURN node.id AS text, score, {} AS metadata",
    )
    data = await neo4j_vector.asimilarity_search(question, k=50)
    return [el.page_content for el in data]


initial_node_system = """
As an intelligent assistant, your primary objective is to answer questions based on information contained within a text. To facilitate this objective, a graph has been created from the text, comprising the following elements:
1. Text Chunks: Chunks of the original text.
2. Atomic Facts: Smallest, indivisible truths extracted from text chunks.
3. Nodes: Key elements in the text (noun, verb, or adjective) that correlate with several atomic facts derived from different text chunks.

Your current task is to check a list of nodes, with the objective of selecting the most relevant initial nodes from the graph to efficiently answer the question. You are given the question, the rational plan, and a list of node key elements. These initial nodes are crucial because they are the starting point for searching for relevant information.

Requirements:

#####
1. Once you have selected a starting node, assess its relevance to the potential answer by assigning a score between 0 and 100. A score of 100 implies a high likelihood of relevance to the answer, whereas a score of 0 suggests minimal relevance.
2. Present each chosen starting node in a separate line, accompanied by its relevance score. Format each line as follows: Node: [Key Element of Node], Score: [Relevance Score].
3. Please select at least 10 starting nodes, ensuring they are non-repetitive and diverse.
4. In the user's input, each line constitutes a node. When selecting the starting node, please make your choice from those provided, and refrain from fabricating your own. The nodes you output must correspond exactly to the nodes given by the user, with identical wording.

Finally, I emphasize again that you need to select the starting node from the given Nodes, and it must be consistent with the words of the node you selected.
""".strip()

initial_node_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            initial_node_system,
        ),
        (
            "human",
            (
                """
Question:
\"\"\"
{question}
\"\"\"

Plan:
\"\"\"
{rational_plan}
\"\"\"

Nodes:
\"\"\"
{nodes}
\"\"\"
""".strip()
            ),
        ),
    ]
)


class Node(BaseModel):
    key_element: str = Field(description="""Key element or name of a relevant node""")
    score: int = Field(
        description="""Relevance to the potential answer by assigning a score between 0 and 100. A score of 100 implies a high likelihood of relevance to the answer, whereas a score of 0 suggests minimal relevance.""",
        ge=0,
        le=100,
    )


class InitialNodes(BaseModel):
    initial_nodes: List[Node] = Field(
        description="List of relevant nodes to the question and plan"
    )


initial_nodes_chain = initial_node_prompt | model.with_structured_output(InitialNodes)


async def initial_node_selection(
    state: OverallState, config: RunnableConfig = None
) -> OverallState:
    potential_nodes = await get_potential_nodes(state.get("question"))
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


atomic_fact_check_system = """As an intelligent assistant, your primary objective is to answer questions based on information contained within a text. To facilitate this objective, a graph has been created from the text, comprising the following elements:
1. Text Chunks: Chunks of the original text.
2. Atomic Facts: Smallest, indivisible truths extracted from text chunks.
3. Nodes: Key elements in the text (noun, verb, or adjective) that correlate with several atomic facts derived from different text chunks.

Your current task is to check a node and its associated atomic facts, with the objective of determining whether to proceed with reviewing the text chunk corresponding to these atomic facts. Given the question, the rational plan, previous actions, notebook content, and the current node's atomic facts and their corresponding chunk_ids, you have the following action options:

#####
1. read_chunk(List[ID]): Choose this action if you believe that a text chunk linked to an atomic fact may hold the necessary information to answer the question. This will allow you to access more complete and detailed information. Must include at least one ID in the list and not repeat chunks already read.
2. stop_and_read_neighbor(): Choose this action if you ascertain that all text chunks lack valuable information.
#####

Strategy:
#####
1. Reflect on previous actions and prevent redundant revisiting nodes or chunks.
2. You can choose to read multiple text chunks at the same time.
3. Atomic facts only cover part of the information in the text chunk, so even if you feel that the atomic facts are slightly relevant to the question, please try to read the text chunk to get more complete information.
4. Keep track of sources and references.
#####

Finally, it is emphasized again that even if the atomic fact is only slightly relevant to the question, you should still look at the text chunk to avoid missing information. You should only choose stop_and_read_neighbor() when a given text chunk is irrelevant to the question.
"""


class AtomicFactOutput(BaseModel):
    updated_notebook: str = Field(
        description="""First, combine your current notebook with new insights and findings about the question from current atomic facts, creating a more complete version of the notebook that contains more valid information. Be detailed and accurate. Include sources and references where possible. Use clean markdown formatting with support for katex and math."""
    )
    rational_next_action: str = Field(
        description="""Based on the given question, the rational plan, previous actions, and notebook content, analyze how to choose the next action. Show your chain of thought."""
    )
    chosen_action: str = Field(
        description="""
1. read_chunk(List[ID]): Choose this action if you believe that a text chunk linked to an atomic fact may hold the necessary information to answer the question. This will allow you to access more complete and detailed information. Must include at least one ID in the list.
2. stop_and_read_neighbor(): Choose this action if you ascertain that all text chunks lack valuable information.""".strip()
    )


atomic_fact_check_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            atomic_fact_check_system,
        ),
        (
            "human",
            (
                """
Question:
\"\"\"
{question}
\"\"\"

Plan:
\"\"\"
{rational_plan}
\"\"\"

Previous actions:
\"\"\"
{previous_actions}
\"\"\"

Notebook:
\"\"\"
{notebook}
\"\"\"

Atomic facts:
\"\"\"
{atomic_facts}
\"\"\"
""".strip()
            ),
        ),
    ]
)


class AtomFactResult(TypedDict):
    document_id: str
    document_name: str
    source: str
    chunk_id: str
    text: str
    updated_at: str


def get_atomic_facts(
    key_elements: List[str], personality_id: str
) -> List[AtomFactResult]:
    """
    Get the atomic facts for the given key elements and personality
    """
    data = graph.query(
        """
MATCH (k:KeyElement)<-[:HAS_KEY_ELEMENT]-(fact)<-[:HAS_ATOMIC_FACT]-(c:Chunk)<-[:HAS_CHUNK]-(doc:Document)
WHERE k.id IN $key_elements AND c.personality_id = $personality_id
RETURN DISTINCT doc.id AS document_id, doc.name AS document_name, doc.source AS source, c.id AS chunk_id, fact.text AS text, c.updated_at AS updated_at
    """.strip(),
        params={"key_elements": key_elements, "personality_id": personality_id},
    )
    return data


def get_neighbors_by_key_element(key_elements: List[str], personality_id: str):
    logger.debug(f"Key elements: {key_elements}")
    data = graph.query(
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
    return data


atomic_fact_chain = atomic_fact_check_prompt | model.with_structured_output(
    AtomicFactOutput
)


def get_read_chunk_ids(previous_actions: List[str]) -> List[str]:
    """
    Get the list of chunks that have been read from the previous actions
    """
    read_chunks: List[str] = []
    for action in previous_actions:
        if action.startswith("read_chunk"):
            read_chunks.append(action.split("(")[1].split(")")[0].strip())
    return read_chunks


async def atomic_fact_check(
    state: OverallState, config: RunnableConfig
) -> OverallState:
    personality_id: Optional[str] = config["configurable"].get("personality_id")
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
        check_chunks_queue: List[str] = (
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


chunk_read_system_prompt = """As an intelligent assistant, your primary objective is to answer questions based on information within a text. To facilitate this objective, a knowledge graph of relevant information has been created from multiple documents, comprising the following elements:
1. Text Chunks: Segments of the original text.
2. Atomic Facts: Smallest, indivisible truths extracted from text chunks.
3. Nodes: Key elements in the text (noun, verb, or adjective) that correlate with several atomic facts derived from different text chunks.

Your current task is to assess a specific text chunk and determine whether the available information suffices to answer the question. Given the question, rational plan, previous actions, notebook content, and the current text chunk, you have the following action options:
#####
1. search_more(): Choose this action if you think that the essential information necessary to answer the question is still lacking.
2. read_previous_chunk(): Choose this action if you feel that the previous text chunk contains essential information for answering the question.
3. read_subsequent_chunk(): Choose this action if you feel that the subsequent text chunk contains essential information for answering the question.
4. termination(): Choose this action if you believe that the information you have currently obtained is enough to answer the question. This will allow you to summarize the gathered information and provide a final answer.
#####

Strategy:
#####
1. Reflect on previous actions and prevent redundant revisiting of nodes or chunks.
2. Show your chain of thought.
3. You can only choose one action.
#####
"""


class ChunkOutput(BaseModel):
    updated_notebook: str = Field(
        description="""First, combine your previous notes with new insights and findings about the question from current text chunks, creating a more complete version of the notebook that contains more valid information. Include sources."""
    )
    rational_next_move: str = Field(
        description="""Based on the given question, rational plan, previous actions, and notebook content, concisely analyze how to choose the next action. Show your chain of thought."""
    )
    chosen_action: str = Field(
        description="""
Choose one of the following actions:
1. search_more(): Choose this action if you think that the essential information necessary to answer the question is still lacking.
2. read_previous_chunk(): Choose this action if you feel that the previous text chunk contains essential information for answering the question.
3. read_subsequent_chunk(): Choose this action if you feel that the subsequent text chunk contains essential information for answering the question.
4. termination(): Choose this action if you believe that the information you have currently obtained is enough to answer the question. This will allow you to summarize the gathered information and provide a final answer.""".strip()
    )


chunk_read_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            chunk_read_system_prompt,
        ),
        (
            "human",
            (
                """
Question
\"\"\"
{question}
\"\"\"

Plan
\"\"\"
{rational_plan}
\"\"\"

Previous actions
\"\"\"
{previous_actions}
\"\"\"

Notebook
\"\"\"
{notebook}
\"\"\"

Chunk
\"\"\"
{chunk}
\"\"\"
""".strip()
            ),
        ),
    ]
)

chunk_read_chain = chunk_read_prompt | model.with_structured_output(ChunkOutput)


def get_subsequent_chunk_id(chunk_id: str, personality_id: str) -> Optional[str]:
    data = graph.query(
        """
MATCH (c:Chunk)-[:NEXT]->(next)
WHERE c.id = $id AND c.personality_id = $personality_id
RETURN next.id AS next
        """.strip(),
        params={"id": chunk_id, "personality_id": personality_id},
    )
    return data[0]["next"] if data else None


def get_previous_chunk_id(chunk_id: str, personality_id: str) -> Optional[str]:
    data = graph.query(
        """
MATCH (c:Chunk)<-[:NEXT]-(previous)
WHERE c.id = $id AND c.personality_id = $personality_id
RETURN previous.id AS previous
    """.strip(),
        params={"id": chunk_id, "personality_id": personality_id},
    )
    return data[0]["previous"] if data else None


class Chunk(TypedDict):
    chunk_id: str
    text: str
    document_id: str


def get_chunk(chunk_id: str, personality_id: str) -> Optional[Chunk]:
    data = graph.query(
        """
MATCH (c:Chunk)
WHERE c.id = $chunk_id AND c.personality_id = $personality_id
RETURN c.id AS chunk_id, c.text AS text, c.document_id AS document_id
    """.strip(),
        params={"chunk_id": chunk_id, "personality_id": personality_id},
    )
    return data[0] if data else None


async def chunk_check(state: OverallState, config: RunnableConfig) -> OverallState:
    personality_id: Optional[str] = config["configurable"].get("personality_id")
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
            neighbors = await get_potential_nodes(read_chunk_results.rational_next_move)
            response["neighbor_check_queue"] = neighbors

    response["check_chunks_queue"] = check_chunks_queue
    return response


neighbor_select_system_prompt = """
As an intelligent assistant, your primary objective is to answer questions based on information within a text. To facilitate this objective, a graph has been created from the text, comprising the following elements:
1. Text Chunks: Segments of the original text.
2. Atomic Facts: Smallest, indivisible truths extracted from text chunks.
3. Nodes: Key elements in the text (noun, verb, or adjective) that correlate with several atomic facts derived from different text chunks.

Your current task is to assess all neighboring nodes of the current node, with the objective of determining whether to proceed to the next neighboring node. Given the question, rational plan, previous actions, notebook content, and the neighbors of the current node, you have the following Action Options:
#####
1. read_neighbor_node(key element of node): Choose this action if you believe that any of the neighboring nodes may contain information important to the question. Note that you should focus on one neighbor node at a time.
2. termination(): Choose this action if you believe that none of the neighboring nodes possess information that could answer the question.
#####

Strategy:
#####
1. Reflect on previous actions and prevent redundant revisiting of nodes or chunks.
2. Show your chain of thought.
3. You can only choose one action. This means that you can choose to read only one neighbor node or choose to terminate.
#####
""".strip()


class NeighborOutput(BaseModel):
    rational_next_move: str = Field(
        description="""Based on the given question, rational plan, previous actions, and notebook content, concisely analyze how to choose the next action. Show your chain of thought."""
    )
    chosen_action: str = Field(
        description="""You have the following Action Options:
1. read_neighbor_node(key element of node): Choose this action if you believe that any of the neighboring nodes may contain information relevant to the question. Note that you should focus on one neighbor node at a time.
2. termination(): Choose this action if you believe that none of the neighboring nodes possess information that could answer the question."""
    )


neighbor_select_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            neighbor_select_system_prompt,
        ),
        (
            "human",
            (
                """
Question
\"\"\"
{question}
\"\"\"

Plan
\"\"\"
{rational_plan}
\"\"\"

Previous actions
\"\"\"
{previous_actions}
\"\"\"

Notebook
\"\"\"
{notebook}
\"\"\"

Neighbor nodes
\"\"\"
{nodes}
\"\"\"
""".strip()
            ),
        ),
    ]
)

neighbor_select_chain = neighbor_select_prompt | model.with_structured_output(
    NeighborOutput
)


async def neighbor_select(state: OverallState, config: RunnableConfig) -> OverallState:
    logger.debug(f"Step: neighbor select")
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
            f"neighbor_select({chosen_action.get('arguments', [''])[0] if chosen_action.get('arguments', ['']) else ''})"
        ],
    }
    if chosen_action.get("function_name") == "read_neighbor_node":
        response["check_atomic_facts_queue"] = [chosen_action.get("arguments")[0]]
    return response


def get_document(document_id: str, personality_id: str) -> Optional[Dict[str, str]]:
    data = graph.query(
        """
MATCH (c:Chunk)<-[:HAS_CHUNK]-(doc:Document)
WHERE doc.id = $id AND c.personality_id = $personality_id
RETURN doc.id AS document_id, doc.name AS document_name, c.id AS chunk_id, c.text AS text, c.updated_at AS updated_at
    """.strip(),
        params={"id": document_id, "personality_id": personality_id},
    )
    return data if data else None


class AnswerReasonOutput(BaseModel):
    analyze: str = Field(
        description="""Do a critical analysis of the research. Consider complementary information from other notes and employ a majority voting strategy to resolve any inconsistencies. Note any contradictions and inconsistencies if any. Show your thought process step by step. Follow the rational plan. The result should be cleanly formatted in markdown using latex and math if required. Last include a final section giving an overall assessment of the research and how well it answers the question. If the research is not sufficient to answer the question, explain why and what is missing. Include sources and references where possible."""
    )
    final_answer: str = Field(
        description="""When generating the final answer, ensure that you take into account all available information. Just present the facts and a concise answer. Use markdown formatting with support for katex and math. Include sources and references where possible."""
    )


answer_reasoning_system_prompt = """
As an intelligent assistant, your primary objective is to answer questions based on information within a text. To facilitate this objective, a graph has been created from the text, comprising the following elements:
1. Text Chunks: Segments of the original text.
2. Atomic Facts: Smallest, indivisible truths extracted from text chunks.
3. Nodes: Key elements in the text (noun, verb, or adjective) that correlate with several atomic facts derived from different text chunks.

You have now explored multiple paths from various starting nodes on this graph, recording key information for each path in the research. Your task now is to analyze these memories and reason to answer the question. Show your chain of thought step by step as part of your analysis.

Strategy:
#####
1. You should first analyze the research facts in detail before providing a final answer.
2. During the analysis, consider complementary information from other notes and employ a majority voting strategy to resolve any inconsistencies.
3. When generating the final answer, ensure that you take into account all available information. Include sources such as article ids and urls whenver possible.
#####

Example:
#####
User:
Question: Who had a longer tennis career, Danny or Alice?
Research results of different exploration paths:
1. We only know that Danny's tennis career started in 1972 and ended in 1990, but we don't know the length of Alice's career.
2. ......
Assistant:
Analyze:
The summary of search path 1 points out that Danny's tennis career is 1990-1972=18 years. Although it does not indicate the length of Alice's career, the summary of search path 2 finds this information, that is, the length of Alice's tennis career is 15 years. Then we can get the final answer, that is, Danny's tennis career is longer than Alice's.
Final answer:
Danny's tennis career is longer than Alice's.
#####
"""

answer_reasoning_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            answer_reasoning_system_prompt,
        ),
        (
            "human",
            (
                """
Question
\"\"\"
{question}
\"\"\"

Research
\"\"\"
{notebook}
\"\"\"

Now: {now}
""".strip()
            ),
        ),
    ]
)


answer_reasoning_chain = answer_reasoning_prompt | model.with_structured_output(
    AnswerReasonOutput
)


async def answer_reasoning(state: OverallState, config: RunnableConfig) -> OutputState:
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
    if state.get("chosen_action") == "stop_and_read_neighbor":
        return "neighbor_select"
    elif (
        state.get("chosen_action") == "read_chunk"
        and len(state.get("check_chunks_queue", [])) > 0
    ):
        return "chunk_check"
    return "neighbor_select"


def chunk_condition(
    state: OverallState,
) -> Literal["answer_reasoning", "chunk_check", "neighbor_select"]:
    if state.get("chosen_action") == "termination":
        return "answer_reasoning"
    elif state.get("chosen_action") in [
        "read_subsequent_chunk",
        "read_previous_chunk",
        "search_more",
    ]:
        return "chunk_check"
    elif state.get("chosen_action") == "search_neighbor":
        return "neighbor_select"
    logger.error(f"Unknown action: {state.get('chosen_action')}")
    return "neighbor_select"


def neighbor_condition(
    state: OverallState,
) -> Literal["answer_reasoning", "atomic_fact_check"]:
    if state.get("chosen_action") == "termination":
        return "answer_reasoning"
    elif state.get("chosen_action") == "read_neighbor_node":
        return "atomic_fact_check"


def rational_plan_node_condition(
    state: OverallState,
) -> Literal["initial_node_selection", "answer_reasoning"]:
    if state.get("chosen_action") == "search_more":
        return "initial_node_selection"
    return "answer_reasoning"


async def initial_notebook(state: OverallState) -> List[str]:
    neo4j_vector = Neo4jVector.from_existing_graph(
        url=config.neo4j.url,
        username=config.neo4j.username,
        password=config.neo4j.password,
        embedding=embeddings,
        index_name="chunk_index",
        node_label="Chunk",
        text_node_properties=["text", "description", "document_name"],
        embedding_node_property="embedding",
        retrieval_query="""RETURN node.text AS text, score, {document_name: node.document_name, description: node.description, document_id: node.document_id, chunk_id: node.id, source: node.source} AS metadata""",
    )
    data = await neo4j_vector.asimilarity_search(state.get("question"), k=3)
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


async def main(question: str, personality_id: str):
    response = await question_graph.ainvoke(
        {"question": question},
        {
            "configurable": {
                "personality_id": personality_id,
            }
        },
    )

    print(f"Analysis:\n{response['analysis']}\n")
    print(f"Answer:\n{response['answer']}\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Process a question using the question graph."
    )
    parser.add_argument(
        "--question",
        type=str,
        help="The question to be processed",
        default="What do you know about llms?",
        # default="What information do we have about Large Language Models in our knowledge graph? Include details about architectures, training methods, and recent developments.",
    )
    parser.add_argument(
        "--personality_id",
        type=str,
        help="The personality id to use",
        default="b6c663ef-691a-4c4a-a3f0-5f68094c4d1d",
    )
    args = parser.parse_args()

    asyncio.run(main(args.question, args.personality_id))
