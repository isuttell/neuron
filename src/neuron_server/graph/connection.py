"""Neo4j connection and index setup."""

from typing import Any

from .manager import Neo4jConnectionManager

# Create singleton instance
connection_manager = Neo4jConnectionManager()

# For backward compatibility
graph: Any = None


def initialize_graph() -> None:
    """Initialize the graph instance."""
    global graph
    graph = connection_manager.connection.graph


def get_graph() -> Any:
    """Get the Neo4j graph instance.

    Returns:
        Neo4j graph instance

    Raises:
        ConnectionError: If connection not initialized
    """
    return connection_manager.connection.graph


__all__ = ["connection_manager", "get_graph", "graph", "initialize_graph"]
