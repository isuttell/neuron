import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import openai
import pytest
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession

from neuron_server.controllers.auth import TokenPayload

# Mock the cache module
mock_cache = Mock()
# Handle ttl parameter
mock_cache.cache_response = lambda func=None, ttl=None: lambda f: f
mock_cache.ClientCache = Mock()
sys.modules["neuron_server.cache"] = mock_cache

# Mock the pubsub module
mock_pubsub = Mock()
mock_pubsub.publish = AsyncMock()
mock_pubsub.subscribe = AsyncMock()
sys.modules["neuron_server.pubsub"] = mock_pubsub

# Mock Redis
redis_mock = Mock()
redis_mock.asyncio = Mock()
redis_mock.asyncio.from_url = Mock(return_value=Mock())
redis_mock.typing = Mock()
redis_mock.typing.ExpiryT = object
redis_mock.typing.ResponseT = object
redis_mock.exceptions = Mock()
redis_mock.exceptions.ConnectionError = type('ConnectionError', (Exception,), {})
sys.modules["redis"] = redis_mock

# Mock LangGraph and its modules
langgraph_mock = Mock()
langgraph_graph = Mock()
langgraph_graph_message = Mock() 
langgraph_graph_message.add_messages = Mock()
langgraph_checkpoint = Mock()
langgraph_checkpoint_postgres = Mock()
langgraph_checkpoint_postgres_aio = Mock()
langgraph_checkpoint_postgres_aio.AsyncPostgresSaver = Mock()
langgraph_prebuilt = Mock()
langgraph_prebuilt.ToolNode = Mock()

sys.modules["langgraph"] = langgraph_mock
sys.modules["langgraph.graph"] = langgraph_graph
sys.modules["langgraph.graph.message"] = langgraph_graph_message
sys.modules["langgraph.checkpoint"] = langgraph_checkpoint
sys.modules["langgraph.checkpoint.postgres"] = langgraph_checkpoint_postgres
sys.modules["langgraph.checkpoint.postgres.aio"] = langgraph_checkpoint_postgres_aio
sys.modules["langgraph.prebuilt"] = langgraph_prebuilt

# Mock Neo4j
mock_neo4j = Mock()
mock_driver = Mock()
mock_driver.verify_connectivity = Mock()
mock_neo4j.GraphDatabase = Mock()
mock_neo4j.GraphDatabase.driver = Mock(return_value=mock_driver)

# Mock Neo4j exceptions
mock_neo4j.exceptions = Mock()
mock_neo4j.exceptions.CypherSyntaxError = type('CypherSyntaxError', (Exception,), {})
mock_neo4j.exceptions.DriverError = type('DriverError', (Exception,), {})
mock_neo4j.exceptions.Neo4jError = type('Neo4jError', (Exception,), {})

# Mock neo4j Record
mock_neo4j.Record = Mock()
mock_neo4j.Driver = Mock()

sys.modules["neo4j"] = mock_neo4j

# Mock langchain-neo4j modules
sys.modules["langchain_neo4j"] = Mock()
sys.modules["langchain_neo4j.graphs"] = Mock()
sys.modules["langchain_neo4j.graphs.neo4j_graph"] = Mock()
sys.modules["langchain_neo4j.graphs.neo4j_graph"].Neo4jGraph = Mock()
sys.modules["langchain_neo4j.chains"] = Mock()
sys.modules["langchain_neo4j.chains.graph_qa"] = Mock()
sys.modules["langchain_neo4j.chains.graph_qa.cypher"] = Mock()
sys.modules["langchain_neo4j.chains.graph_qa.cypher"].GraphCypherQAChain = Mock()

# Mock neo4j-graphrag
sys.modules["neo4j_graphrag"] = Mock()
sys.modules["neo4j_graphrag.retrievers"] = Mock()
sys.modules["neo4j_graphrag.retrievers.text2cypher"] = Mock()
sys.modules["neo4j_graphrag.retrievers.text2cypher"].extract_cypher = Mock()
sys.modules["neo4j_graphrag.retrievers.text2cypher"].Text2CypherRetriever = Mock()

# Mock Tavily
mock_tavily = Mock()
mock_tavily.TavilySearchAPIWrapper = Mock
sys.modules["langchain_community.tools.tavily_search"] = mock_tavily

# Mock OpenAI API
# Mock embeddings response
mock_embeddings = MagicMock()
mock_embeddings.create.return_value = {"data": [{"embedding": [0.1] * 1536}]}

# Mock chat completions response
mock_chat = MagicMock()
mock_chat.create.return_value = {
    "choices": [{"message": {"content": "Test response", "tool_calls": []}}]
}

# Define a custom client class that doesn't check for API key
class MockOpenAI:
    def __init__(self, api_key: str = None, **kwargs: dict) -> None:
        self.embeddings = mock_embeddings
        self.chat = MagicMock()
        self.chat.completions = mock_chat

class MockAsyncOpenAI:
    def __init__(self, api_key: str = None, **kwargs: dict) -> None:
        self.embeddings = mock_embeddings
        self.chat = MagicMock()
        self.chat.completions = mock_chat

# Patch OpenAI
openai.OpenAI = MockOpenAI
openai.AsyncOpenAI = MockAsyncOpenAI
openai.OpenAIError = type('OpenAIError', (Exception,), {})

# Mock langchain OpenAI classes
OpenAIEmbeddings.validate_environment = MagicMock()
ChatOpenAI.validate_environment = MagicMock()

# Mock scheduler
mock_scheduler = AsyncMock()
mock_scheduler.create_event = AsyncMock(return_value="test-event-id")
mock_scheduler.update_event = AsyncMock()
mock_scheduler.delete_event = AsyncMock()
mock_scheduler.list_events = AsyncMock(return_value=[])
mock_scheduler.get_event = AsyncMock()

# Mock API module
sys.modules["neuron_server.api"] = Mock()
sys.modules["neuron_server.api"].scheduler = mock_scheduler

# Create mock SQLAlchemy session
mock_session = AsyncMock(spec=AsyncSession)
mock_session.__aenter__.return_value = mock_session
mock_session.__aexit__.return_value = None
mock_session.commit = AsyncMock()
mock_session.rollback = AsyncMock()
mock_session.close = AsyncMock()
mock_session.execute = AsyncMock()
mock_session.flush = AsyncMock()
mock_session.refresh = AsyncMock()
mock_session.scalar = AsyncMock()

# Create mock engine
mock_engine = Mock()
mock_engine.begin = AsyncMock()
mock_engine.dispose = AsyncMock()


@pytest.fixture(autouse=True)
def mock_database() -> None:
    """Mock database connections for all tests."""
    # Apply patches
    with (
        patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine),
        patch("neuron_server.database.get_session", return_value=mock_session),
        patch("neuron_server.database.engine", mock_engine),
        patch("neuron_server.database.start", AsyncMock()),
    ):
        yield


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
def mock_token() -> TokenPayload:
    """Create a mock token for testing."""
    return TokenPayload(
        sub="test_user",
        user_id="test-user-id",
        nickname="Test User",
        email="test@example.com",
        picture=None,
        roles=["user"],
        permissions=["read:events", "write:events"]
    )


@pytest.fixture
def mock_ai_message() -> AIMessage:
    """Create a mock AI message for testing."""
    return AIMessage(
        content="Test response",
        tool_calls=[],
        created_at="2024-02-16T13:00:00-08:00",
    )


# Create modules mock for OpenAI
mock_openai = Mock(OpenAI=MockOpenAI, AsyncOpenAI=MockAsyncOpenAI)
mock_openai_simple = Mock(OpenAI=MockOpenAI)
mock_openai_full = Mock(OpenAI=MockOpenAI, AsyncOpenAI=MockAsyncOpenAI)

sys.modules["neuron_server.llms.openai"] = mock_openai
sys.modules["neuron_server.llms.openai.openai"] = mock_openai
sys.modules["neuron_server.tools.inspect_image_tool.openai"] = mock_openai_simple
sys.modules["neuron_server.tools.openai_tts_tool.openai"] = mock_openai_simple
sys.modules["neuron_server.tools.whisper_stt_tool.openai"] = mock_openai_simple
sys.modules["neuron_server.llms.agent.openai"] = mock_openai_simple
sys.modules["neuron_server.llms.embeddings.openai"] = mock_openai_full

@pytest.fixture(autouse=True)
def mock_openai_modules() -> None:
    """Mock OpenAI modules in various places they might be imported."""
    yield