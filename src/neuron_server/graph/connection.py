"""Neo4j connection and index setup."""

from langchain_neo4j import Neo4jGraph

from neuron_server.config import config
from neuron_server.logger import logger

# Initialize Neo4j connection
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
    "CREATE INDEX document_personality_idx IF NOT EXISTS FOR (d:Document) ON (d.personality_id)",  # noqa: E501
    "CREATE INDEX document_user_idx IF NOT EXISTS FOR (d:Document) ON (d.user_id)",
    # Chunk indexes
    "CREATE INDEX chunk_personality_idx IF NOT EXISTS FOR (c:Chunk) ON (c.personality_id)",  # noqa: E501
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
