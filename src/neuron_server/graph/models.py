"""Models and type definitions for graph operations."""

from operator import add
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field


class AtomicFact(BaseModel):
    key_elements: list[str] = Field(
        description="""
        The essential nouns (e.g., characters, times, events, places, numbers),
        verbs (e.g., actions), and adjectives (e.g., states, feelings) that are
        pivotal to the atomic fact's narrative."""
    )
    atomic_fact: str = Field(
        description="""
        The smallest, indivisible facts, presented as concise sentences. These include
        propositions, theories, existences, concepts, and implicit elements like logic,
        causality, event sequences, interpersonal relationships, timelines, etc."""
    )


class Extraction(BaseModel):
    description: str = Field(
        description="A short description of the extracted information"
    )
    atomic_facts: list[AtomicFact] = Field(description="List of atomic facts")


class SummaryResponse(BaseModel):
    summary: str = Field(description="A short summary of the extracted information")
    critical_analysis: str = Field(
        description="""
        A detailed critical analysis of the extracted information. Identify
        inconsistencies and contradictions. Consider any biases or limitations.
        How trustworthy is the information? Is there evidence and supporting
        facts? What is the significance of the information? Provide future
        research recommendations if relevant."""
    )
    keywords: list[str] = Field(
        description="""
        A list of informative keywords or concepts that are important to the
        extracted information"""
    )


class DocumentResult(BaseModel):
    document_id: str = Field(description="The ID of the document")
    document_name: str | None = Field(description="The name of the document")
    source: str | None = Field(description="The source of the document")
    keywords: list[str] = Field(description="The keywords of the document")
    summary: str = Field(description="The summary of the document")
    analysis: str = Field(description="The analysis of the document")


class InputState(TypedDict):
    question: str
    history: str
    document_ids: list[str] | None


class OutputState(TypedDict):
    answer: str
    analysis: str
    previous_actions: list[str]


class OverallState(TypedDict):
    history: str
    question: str
    rational_plan: str
    notebook: str
    document_ids: list[str] | None
    previous_actions: Annotated[list[str], add]
    check_atomic_facts_queue: list[str]
    check_chunks_queue: list[str]
    neighbor_check_queue: list[str]
    chosen_action: str


class RationalPlanOutput(BaseModel):
    rational_plan: str = Field(
        description="""
        The step by step rational plan to answer the question. It should be in
        second person and concise"""
    )
    chosen_action: str = Field(
        description="""
        1. search_more(): Choose this action if you think that the essential
           information necessary to answer the question is still lacking.
        2. terminate(): Choose this action if you believe that the information
           you have currently obtained is enough to answer the question. This
           will allow you to summarize the gathered information and provide a
           final answer.
        """.strip()
    )


class Node(BaseModel):
    key_element: str = Field(description="""Key element or name of a relevant node""")
    score: int = Field(
        description="""
        Relevance to the potential answer by assigning a score between 0 and 100.
        A score of 100 implies a high likelihood of relevance to the answer,
        whereas a score of 0 suggests minimal relevance. Values outside this range
        will be clamped."""
    )


class InitialNodes(BaseModel):
    initial_nodes: list[Node] = Field(
        description="List of relevant nodes to the question and plan"
    )


class AtomicFactOutput(BaseModel):
    updated_notebook: str = Field(
        description="""
        First, combine your current notebook with new insights and findings about
        the question from current atomic facts, creating a more complete version
        of the notebook that contains more valid information. Be detailed and
        accurate. Include sources and references where possible. Use clean
        markdown formatting with support for katex and math."""
    )
    rational_next_action: str = Field(
        description="""
        Based on the given question, the rational plan, previous actions, and
        notebook content, analyze how to choose the next action. Show your chain
        of thought."""
    )
    chosen_action: str = Field(
        description="""
        1. read_chunk(List[ID]): Choose this action if you believe that a text
           chunk linked to an atomic fact may hold the necessary information to
           answer the question. This will allow you to access more complete and
           detailed information. Must include at least one ID in the list.
        2. stop_and_read_neighbor(): Choose this action if you ascertain that all
           text chunks lack valuable information.""".strip()
    )


class ChunkOutput(BaseModel):
    updated_notebook: str = Field(
        description="""
        First, combine your previous notes with new insights and findings about
        the question from current text chunks, creating a more complete version
        of the notebook that contains more valid information. Include sources."""
    )
    rational_next_move: str = Field(
        description="""
        Based on the given question, rational plan, previous actions, and notebook
        content, concisely analyze how to choose the next action. Show your chain
        of thought."""
    )
    chosen_action: str = Field(
        description="""
        Choose one of the following actions:
        1. search_more(): Choose this action if you think that the essential
           information necessary to answer the question is still lacking.
        2. read_previous_chunk(): Choose this action if you feel that the previous
           text chunk contains essential information for answering the question.
        3. read_subsequent_chunk(): Choose this action if you feel that the
           subsequent text chunk contains essential information for answering
           the question.
        4. termination(): Choose this action if you believe that the information
           you have currently obtained is enough to answer the question. This will
           allow you to summarize the gathered information and provide a final
           answer.""".strip()
    )


class NeighborOutput(BaseModel):
    rational_next_move: str = Field(
        description="""
        Based on the given question, rational plan, previous actions, and notebook
        content, concisely analyze how to choose the next action. Show your chain
        of thought."""
    )
    chosen_action: str = Field(
        description="""
        You have the following Action Options:
        1. read_neighbor_node(key element of node): Choose this action if you
           believe that any of the neighboring nodes may contain information
           relevant to the question. Note that you should focus on one neighbor
           node at a time.
        2. termination(): Choose this action if you believe that none of the
           neighboring nodes possess information that could answer the question."""
    )


class AnswerReasonOutput(BaseModel):
    analyze: str = Field(
        description="""
        Do a critical analysis of the research. Consider complementary information
        from other notes and employ a majority voting strategy to resolve any
        inconsistencies. Note any contradictions and inconsistencies if any. Show
        your thought process step by step. Follow the rational plan. The result
        should be cleanly formatted in markdown using latex and math if required.
        Last include a final section giving an overall assessment of the research
        and how well it answers the question. If the research is not sufficient
        to answer the question, explain why and what is missing. Include sources
        and references where possible."""
    )
    final_answer: str = Field(
        description="""
        When generating the final answer, ensure that you take into account all
        available information. Just present the facts and a concise answer. Use
        markdown formatting with support for katex and math. Include sources and
        references where possible."""
    )


class AtomFactResult(TypedDict):
    document_id: str
    document_name: str
    source: str
    chunk_id: str
    text: str
    updated_at: str


class Chunk(TypedDict):
    chunk_id: str
    text: str
    document_id: str
