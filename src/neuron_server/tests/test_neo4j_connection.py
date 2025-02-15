"""Unit tests for Neo4j connection management."""

from unittest.mock import MagicMock, patch

import pytest

from neuron_server.config import Neo4jConfig
from neuron_server.graph.manager import Neo4jConnectionManager
from neuron_server.graph.neo4j_connection import Neo4jConnection


@pytest.fixture
def mock_config() -> Neo4jConfig:
    """Create a mock Neo4j config."""
    return Neo4jConfig(
        url="bolt://localhost:7687", username="neo4j", password="password"
    )


@pytest.fixture
def mock_graph() -> MagicMock:
    """Create a mock Neo4j graph."""
    return MagicMock()


class TestNeo4jConnection:
    """Test suite for Neo4jConnection class."""

    def test_init(self, mock_config: Neo4jConfig) -> None:
        """Test connection initialization."""
        connection = Neo4jConnection(mock_config)
        assert connection._config == mock_config
        assert connection._graph is None

    def test_graph_property_not_initialized(self, mock_config: Neo4jConfig) -> None:
        """Test graph property raises error when not initialized."""
        connection = Neo4jConnection(mock_config)
        with pytest.raises(ConnectionError, match="Neo4j connection not initialized"):
            _ = connection.graph

    def test_connect(self, mock_config: Neo4jConfig) -> None:
        """Test successful connection."""
        with patch("neuron_server.graph.neo4j_connection.Neo4jGraph") as mock_neo4j:
            mock_graph = MagicMock()
            mock_neo4j.return_value = mock_graph

            connection = Neo4jConnection(mock_config)
            connection.connect()

            mock_neo4j.assert_called_once_with(
                url=mock_config.url,
                username=mock_config.username,
                password=mock_config.password,
                enhanced_schema=True,
            )
            assert connection._graph == mock_graph

    def test_connect_index_error(self, mock_config: Neo4jConfig) -> None:
        """Test connection with index creation error."""
        with patch("neuron_server.graph.neo4j_connection.Neo4jGraph") as mock_neo4j:
            mock_graph = MagicMock()
            mock_graph.query.side_effect = Exception("Index error")
            mock_neo4j.return_value = mock_graph

            connection = Neo4jConnection(mock_config)
            with pytest.raises(ConnectionError, match="Failed to create index"):
                connection.connect()

    def test_disconnect(self, mock_config: Neo4jConfig, mock_graph: MagicMock) -> None:
        """Test disconnection."""
        mock_graph.close = MagicMock()

        connection = Neo4jConnection(mock_config)
        connection._graph = mock_graph

        connection.disconnect()
        mock_graph.close.assert_called_once()
        assert connection._graph is None


class TestNeo4jConnectionManager:
    """Test suite for Neo4jConnectionManager class."""

    def test_connection_property(self) -> None:
        """Test connection property creates connection if needed."""
        manager = Neo4jConnectionManager()
        assert manager._connection is None

        connection = manager.connection
        assert isinstance(connection, Neo4jConnection)
        assert manager._connection is connection

        # Second access should return same instance
        assert manager.connection is connection

    def test_initialize(self) -> None:
        """Test manager initialization."""
        manager = Neo4jConnectionManager()
        manager.connection.connect = MagicMock()

        manager.initialize()
        manager.connection.connect.assert_called_once()

    def test_cleanup(self) -> None:
        """Test manager cleanup."""
        manager = Neo4jConnectionManager()
        manager._connection = MagicMock()
        manager._connection.disconnect = MagicMock()

        manager.cleanup()
        manager._connection.disconnect.assert_called_once()

    def test_cleanup_no_connection(self) -> None:
        """Test cleanup with no active connection."""
        manager = Neo4jConnectionManager()
        manager.cleanup()  # Should not raise
