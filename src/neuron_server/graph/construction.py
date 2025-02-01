"""Construction system for extracting key elements and atomic facts."""

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from .models import Extraction

construction_system = """
You are now an intelligent assistant tasked with meticulously extracting both key
elements and atomic facts from a long text.
1. Key Elements: The essential nouns (e.g., characters, times, events, places, numbers),
   verbs (e.g., actions), and adjectives (e.g., states, feelings) that are pivotal to
   the text's narrative.
2. Atomic Facts: The smallest, indivisible facts, presented as concise sentences. These
   include propositions, theories, existences, concepts, and implicit elements like
   logic, causality, event sequences, interpersonal relationships, timelines, etc.

Requirements:
1. Ensure that all identified key elements are reflected within the corresponding atomic
   facts.
2. You should extract key elements and atomic facts comprehensively, especially those
   that are important and potentially query-worthy and do not leave out details.
3. Whenever applicable, replace pronouns with their specific noun counterparts (e.g.,
   change I, He, She to actual names).
4. Ensure that the key elements and atomic facts you extract are presented in the same
   language as the original text (e.g., English or Chinese).
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

model = ChatOpenAI(model="gpt-4o-2024-11-20", temperature=0.3, max_tokens=None)
structured_llm = model.with_structured_output(Extraction)

construction_chain = construction_prompt | structured_llm

# Query templates
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
