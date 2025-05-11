import sys
from unittest.mock import MagicMock, Mock, patch

import openai
import pytest
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pytest import MonkeyPatch

from neuron_server.config import Config

# Mock API clients and database connections before any imports
openai.OpenAI = MagicMock()
openai.AsyncOpenAI = MagicMock()

# Mock Neo4j
mock_neo4j = Mock()
mock_driver = Mock()
mock_driver.verify_connectivity = Mock()
mock_neo4j.GraphDatabase.driver.return_value = mock_driver

# Mock Tavily
mock_tavily = Mock()
mock_tavily.TavilySearchAPIWrapper = Mock
sys.modules["langchain_community.tools.tavily_search"] = mock_tavily

# Mock Neo4jGraph
mock_neo4j_graph = Mock()
mock_neo4j_graph.Neo4jGraph = Mock()
sys.modules["langchain_neo4j.graphs.neo4j_graph"] = mock_neo4j_graph

# Mock OpenAI embeddings
mock_embeddings = MagicMock()
mock_embeddings.create.return_value = {"data": [{"embedding": [0.1] * 1536}]}
openai.OpenAI.return_value.embeddings = mock_embeddings
openai.AsyncOpenAI.return_value.embeddings = mock_embeddings

# Mock OpenAI chat completions
mock_chat = MagicMock()
mock_chat.create.return_value = {
    "choices": [{"message": {"content": "Test response", "tool_calls": []}}]
}
openai.OpenAI.return_value.chat.completions = mock_chat
openai.AsyncOpenAI.return_value.chat.completions = mock_chat

# Mock LangChain classes
OpenAIEmbeddings.validate_environment = MagicMock()
ChatOpenAI.validate_environment = MagicMock()


def pytest_configure() -> None:
    """Configure test environment before running tests."""
    pass


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch: MonkeyPatch) -> None:
    """Mock environment variables for testing."""
    # API Keys
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-api-key")
    monkeypatch.setenv("HF_TOKEN", "test-token")
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-api-key")
    monkeypatch.setenv("ASTROSPHERIC_API_KEY", "test-api-key")
    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-api-key")
    monkeypatch.setenv("PUSHOVER_API_TOKEN", "test-token")
    monkeypatch.setenv("PUSHOVER_USER_KEY", "test-key")
    monkeypatch.setenv("TAVILY_API_KEY", "test-api-key")

    # Database Configs
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "test-user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
    monkeypatch.setenv("POSTGRES_DB", "test-db")

    # Redis Config
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")

    # Neo4j Config
    monkeypatch.setenv("NEO4J_URL", "bolt://localhost:7687")
    monkeypatch.setenv("NEO4J_USERNAME", "neo4j")
    monkeypatch.setenv("NEO4J_PASSWORD", "test-password")

    # Service Endpoints
    monkeypatch.setenv("HOMEASSISTANT_SERVER", "http://localhost:8123")
    monkeypatch.setenv("HOMEASSISTANT_TOKEN", "test-token")
    monkeypatch.setenv("AUTOMATIC1111_ENDPOINT", "http://localhost:7860")
    monkeypatch.setenv("GLADOS_ENDPOINT", "http://localhost:7612")

    # Auth Config
    monkeypatch.setenv("AUTH0_DOMAIN", "test.auth0.com")
    monkeypatch.setenv("AUTH0_API_AUDIENCE", "test-audience")
    monkeypatch.setenv("AUTH0_CLIENT_ID", "test-client-id")

    # Feature Flags
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("MEMORY_ENABLED", "True")
    monkeypatch.setenv("STATIC_REQUIRE_AUTH", "True")

    # Paths and URLs
    monkeypatch.setenv("STATIC_FOLDER", "./test/static")
    monkeypatch.setenv("OUTPUT_FOLDER", "./test/output")
    monkeypatch.setenv("TEMP_FOLDER", "./test/tmp")
    monkeypatch.setenv("PARENT_TEMP_FOLDER", "./test/tmp")
    monkeypatch.setenv("STATIC_CONTENT_URL", "http://localhost:5000/static")


@pytest.fixture
def mock_config() -> None:
    """Mock configuration for testing."""
    with patch("neuron_server.config.config", Config()):
        yield


@pytest.fixture
def mock_ai_message() -> AIMessage:
    """Create a mock AI message for testing."""
    return AIMessage(
        content="Test response",
        tool_calls=[],
        created_at="2024-02-16T13:00:00-08:00",
    )


@pytest.fixture
def mock_openai() -> None:
    """Mock OpenAI client for testing."""
    with patch("openai.OpenAI") as mock:
        mock.return_value.chat.completions.create.return_value = {
            "choices": [{"message": {"content": "Test response", "tool_calls": []}}]
        }
        yield mock
