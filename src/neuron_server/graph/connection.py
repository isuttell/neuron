"""Neo4j connection and index setup."""

from typing import TYPE_CHECKING

from .manager import Neo4jConnectionManager

if TYPE_CHECKING:
    from neo4j import Graph

# Create singleton instance
connection_manager = Neo4jConnectionManager()


def get_graph() -> "Graph":
    """Get the Neo4j graph instance.

    Returns:
        Neo4j Graph instance

    Raises:
        ConnectionError: If connection not initialized
    """
    return connection_manager.connection.graph


__all__ = ["connection_manager", "get_graph"]
