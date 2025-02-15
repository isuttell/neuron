"""Neo4j connection manager."""

from typing import Optional

from neuron_server.config import config
from neuron_server.logger import logger

from .neo4j_connection import Neo4jConnection


class Neo4jConnectionManager:
    """Manages Neo4j connection lifecycle."""

    def __init__(self) -> None:
        """Initialize connection manager."""
        self._connection: Optional[Neo4jConnection] = None

    @property
    def connection(self) -> Neo4jConnection:
        """Get the Neo4j connection, creating it if needed.

        Returns:
            Neo4j connection instance
        """
        if not self._connection:
            self._connection = Neo4jConnection(config.neo4j)
        return self._connection

    def initialize(self) -> None:
        """Initialize the connection on application startup.

        Raises:
            ConnectionError: If connection fails
        """
        try:
            self.connection.connect()
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j connection: {str(e)}")
            raise

    def cleanup(self) -> None:
        """Clean up connection on application shutdown."""
        if self._connection:
            try:
                self._connection.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from Neo4j: {str(e)}")
                raise
