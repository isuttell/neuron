"""Neo4j connection manager.

This module provides a singleton manager for Neo4j database connections.
It handles connection lifecycle and ensures proper resource management.
"""

from typing import Optional

from neuron_server.config import config
from neuron_server.logger import logger

from .neo4j_connection import Neo4jConnection


class Neo4jConnectionManager:
    """Manages Neo4j connection lifecycle.

    This class provides a singleton manager for Neo4j database connections.
    It ensures that only one connection is active at a time and handles
    proper initialization and cleanup of database resources.

    Attributes:
        _connection: Active Neo4j connection instance
    """

    def __init__(self) -> None:
        """Initialize connection manager."""
        self._connection: Optional[Neo4jConnection] = None

    @property
    def connection(self) -> Neo4jConnection:
        """Get the Neo4j connection, creating it if needed.

        This property ensures that a Neo4j connection exists, creating one
        if necessary. It maintains a single connection instance throughout
        the application lifecycle.

        Returns:
            Neo4j connection instance.
        """
        if not self._connection:
            self._connection = Neo4jConnection(config.neo4j)
        return self._connection

    def initialize(self) -> None:
        """Initialize the connection on application startup.

        This method establishes the Neo4j connection when the application
        starts. It handles any connection errors and ensures proper logging.

        Raises:
            ConnectionError: If connection initialization fails.
        """
        try:
            self.connection.connect()
        except Exception as e:
            logger.error(f"Failed to initialize Neo4j connection: {str(e)}")
            raise

    def cleanup(self) -> None:
        """Clean up connection on application shutdown.

        This method ensures proper cleanup of the Neo4j connection when the
        application shuts down. It handles any disconnection errors and
        ensures proper logging.

        Raises:
            Exception: If cleanup fails.
        """
        if self._connection:
            try:
                self._connection.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting from Neo4j: {str(e)}")
                raise
