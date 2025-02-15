"""Neo4j connection management.

This module provides classes for managing Neo4j database connections and index creation.
It handles connection lifecycle, error handling, and index management.
"""

from typing import Optional

from langchain_neo4j import Neo4jGraph

from neuron_server.config import Neo4jConfig
from neuron_server.logger import logger


class Neo4jConnection:
    """Manages Neo4j database connection and index creation.

    This class handles the lifecycle of a Neo4j database connection, including
    initialization, index creation, and cleanup. It provides a centralized way
    to manage database connections and ensure proper resource management.

    Attributes:
        _config: Neo4j connection configuration
        _graph: Active Neo4j graph connection
        _index_queries: List of index creation queries
    """

    def __init__(self, config: Neo4jConfig) -> None:
        """Initialize connection with config.

        Args:
            config: Neo4j connection configuration containing URL, username,
                and password.
        """
        self._config = config
        self._graph: Optional[Neo4jGraph] = None
        self._index_queries = [
            # Document indexes
            (
                "CREATE INDEX document_name_idx IF NOT EXISTS "
                "FOR (d:Document) ON (d.name)"
            ),
            (
                "CREATE INDEX document_source_idx IF NOT EXISTS "
                "FOR (d:Document) ON (d.source)"
            ),
            (
                "CREATE INDEX document_personality_idx IF NOT EXISTS "
                "FOR (d:Document) ON (d.personality_id)"
            ),
            (
                "CREATE INDEX document_user_idx IF NOT EXISTS "
                "FOR (d:Document) ON (d.user_id)"
            ),
            # Chunk indexes
            (
                "CREATE INDEX chunk_personality_idx IF NOT EXISTS "
                "FOR (c:Chunk) ON (c.personality_id)"
            ),
            (
                "CREATE INDEX chunk_document_idx IF NOT EXISTS "
                "FOR (c:Chunk) ON (c.document_id)"
            ),
            ("CREATE INDEX chunk_user_idx IF NOT EXISTS FOR (c:Chunk) ON (c.user_id)"),
            # AtomicFact indexes
            (
                "CREATE INDEX atomic_fact_id_idx IF NOT EXISTS "
                "FOR (a:AtomicFact) ON (a.id)"
            ),
            (
                "CREATE INDEX atomic_fact_text_idx IF NOT EXISTS "
                "FOR (a:AtomicFact) ON (a.text)"
            ),
            # KeyElement index
            (
                "CREATE INDEX key_element_id_idx IF NOT EXISTS "
                "FOR (k:KeyElement) ON (k.id)"
            ),
        ]

    @property
    def graph(self) -> Neo4jGraph:
        """Get the Neo4j graph connection.

        Returns:
            Active Neo4j graph connection.

        Raises:
            ConnectionError: If connection not initialized.
        """
        if not self._graph:
            raise ConnectionError("Neo4j connection not initialized")
        return self._graph

    def connect(self) -> None:
        """Initialize the Neo4j connection and create indexes.

        This method establishes a connection to the Neo4j database and creates
        any required indexes. It handles connection errors and ensures proper
        cleanup on failure.

        Raises:
            ConnectionError: If connection or index creation fails.
        """
        if self._graph:
            return

        try:
            self._graph = Neo4jGraph(
                url=self._config.url,
                username=self._config.username,
                password=self._config.password,
                enhanced_schema=True,
            )
            self._create_indexes()
            logger.debug(f"Connected to Neo4j at {self._config.url}")
        except Exception as e:
            self._graph = None
            raise ConnectionError(
                f"Could not connect to Neo4j database: {str(e)}"
            ) from e

    def disconnect(self) -> None:
        """Close the Neo4j connection.

        This method safely closes the Neo4j connection and cleans up resources.
        It handles any errors that occur during disconnection and ensures the
        connection is marked as closed.
        """
        if self._graph:
            try:
                self._graph.close()
            except Exception as e:
                logger.error(f"Error closing Neo4j connection: {str(e)}")
            finally:
                self._graph = None
                logger.debug("Disconnected from Neo4j")

    def _create_indexes(self) -> None:
        """Create database indexes if they don't exist.

        This method creates any required indexes in the Neo4j database. It executes
        each index creation query and handles any errors that occur during the process.

        Raises:
            ConnectionError: If index creation fails.
        """
        for query in self._index_queries:
            try:
                self.graph.query(query)
            except Exception as e:
                raise ConnectionError(f"Failed to create index: {str(e)}") from e
