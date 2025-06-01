import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import openai
import pytest
from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pytest import MonkeyPatch
from sqlalchemy.ext.asyncio import AsyncSession

from neuron_server.controllers.auth import TokenPayload

# Mock tiktoken to prevent network requests during tests
mock_tiktoken = Mock()

class MockEncoding:
    """Mock tiktoken encoding class."""
    def encode(
        self,
        text: str,
        allowed_special: set[str] | str | None = None,
        disallowed_special: str = "all"
    ) -> list[int]:
        """Return mock tokens proportional to text length."""
        if not text:
            return []
        # Return approximately 1 token per 4 characters (rough approximation)
        return list(range(len(text) // 4 + 1))

    def decode(self, tokens: list[int]) -> str:
        """Return mock decoded text."""
        return "decoded_text"

mock_tiktoken.encoding_for_model = Mock(return_value=MockEncoding())
mock_tiktoken.get_encoding = Mock(return_value=MockEncoding())
sys.modules["tiktoken"] = mock_tiktoken

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
class AsyncContextManagerMock(AsyncMock):
    """Mock that supports async context manager protocol."""
    async def __aenter__(self) -> "AsyncContextManagerMock":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        return None

redis_mock = Mock()

# Create a proper mock Redis client that supports async context manager
redis_client_mock = AsyncContextManagerMock()
redis_client_mock.close = AsyncMock()
redis_client_mock.config_set = AsyncMock()
redis_client_mock.set = AsyncMock(return_value=True)
redis_client_mock.setex = AsyncMock()
redis_client_mock.get = AsyncMock(return_value=None)
redis_client_mock.exists = AsyncMock(return_value=False)
redis_client_mock.sadd = AsyncMock()
redis_client_mock.smembers = AsyncMock(return_value=set())
redis_client_mock.srem = AsyncMock()
redis_client_mock.delete = AsyncMock()
redis_client_mock.execute = AsyncMock()
redis_client_mock.ping = AsyncMock()
redis_client_mock.psubscribe = AsyncMock()
redis_client_mock.get_message = AsyncMock(return_value=None)

# Create pubsub mock
pubsub_mock = AsyncContextManagerMock()
pubsub_mock.ping = AsyncMock()
pubsub_mock.subscribe = AsyncMock()
pubsub_mock.get_message = AsyncMock(return_value=None)
pubsub_mock.listen = AsyncMock()
pubsub_mock.__aiter__ = AsyncMock(return_value=pubsub_mock)
pubsub_mock.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
pubsub_mock.unsubscribe = AsyncMock()
pubsub_mock.psubscribe = AsyncMock()
pubsub_mock.punsubscribe = AsyncMock()

# Add pubsub method to client
redis_client_mock.pubsub = AsyncMock(return_value=pubsub_mock)

# Create pipeline mock that supports async context manager
pipeline_mock = AsyncContextManagerMock()
pipeline_mock.set = AsyncMock(return_value=pipeline_mock)
pipeline_mock.setex = AsyncMock(return_value=pipeline_mock)
pipeline_mock.sadd = AsyncMock(return_value=pipeline_mock)
pipeline_mock.srem = AsyncMock(return_value=pipeline_mock)
pipeline_mock.delete = AsyncMock(return_value=pipeline_mock)
pipeline_mock.execute = AsyncMock(return_value=[True] * 5)

# Add pipeline method to client
redis_client_mock.pipeline = AsyncMock(return_value=pipeline_mock)

# Setup Redis mock
redis_mock.Redis = Mock(return_value=redis_client_mock)
redis_mock.asyncio = Mock()
redis_mock.asyncio.Redis = Mock(return_value=redis_client_mock)
redis_mock.asyncio.from_url = Mock(return_value=redis_client_mock)
redis_mock.typing = Mock()
redis_mock.typing.ExpiryT = object
redis_mock.typing.ResponseT = object
redis_mock.exceptions = Mock()
redis_mock.exceptions.ConnectionError = type('ConnectionError', (BaseException,), {})
redis_mock.exceptions.RedisError = type('RedisError', (BaseException,), {})
redis_mock.RedisError = type('RedisError', (BaseException,), {})
# Add more specific Redis exceptions
redis_error = redis_mock.exceptions.RedisError
redis_mock.exceptions.LockError = type('LockError', (redis_error,), {})
redis_mock.exceptions.WatchError = type('WatchError', (redis_error,), {})

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

# Mock PGVector
mock_pgvector = Mock()
mock_pgvector.PGVector = Mock()
sys.modules["langchain_postgres"] = mock_pgvector
sys.modules["langchain_postgres.vectorstores"] = mock_pgvector

# Mock the vectorstores module
mock_vectorstores = Mock()
mock_vectorstores.memories_store = Mock()
sys.modules["neuron_server.vectorstores"] = mock_vectorstores

# Mock neo4j-graphrag
sys.modules["neo4j_graphrag"] = Mock()
sys.modules["neo4j_graphrag.retrievers"] = Mock()
sys.modules["neo4j_graphrag.retrievers.text2cypher"] = Mock()
sys.modules["neo4j_graphrag.retrievers.text2cypher"].extract_cypher = Mock()
sys.modules["neo4j_graphrag.retrievers.text2cypher"].Text2CypherRetriever = Mock()

# Mock Tavily
mock_tavily = Mock()

# Create a mock TavilySearchResults that inherits from BaseTool
class MockTavilySearchResults(Mock):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__()
        self.name = "tavily_search_results"
        self.description = "Search Tavily for recent results"

mock_tavily.TavilySearchResults = MockTavilySearchResults
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

# Don't mock the entire API module, just patch the scheduler inside the tests
# We need to maintain the actual Quart app for the API tests

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

    # CSRF Configuration
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing")
    monkeypatch.setenv("CSRF_COOKIE_MAX_AGE", "86400")
    monkeypatch.setenv("CSRF_TOKEN_ROTATION", "False")
    monkeypatch.setenv("ENVIRONMENT", "development")

    # Feature Flags
    monkeypatch.setenv("DEBUG", "True")  # Enable debug for tests
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

@pytest.fixture(autouse=True)
def mock_quart_app() -> None:
    """Make Quart app mocks work with async context manager protocol."""
    from quart import Quart

    # Add async context manager support to Quart app test client and request context
    original_test_client = Quart.test_client
    original_test_request_context = Quart.test_request_context

    def patched_test_client(self: Quart) -> object:
        client = original_test_client(self)
        if not hasattr(client, "__aenter__"):
            client.__aenter__ = AsyncMock(return_value=client)
            client.__aexit__ = AsyncMock(return_value=None)
        return client

    def patched_test_request_context(
        self: Quart,
        *args: object,
        **kwargs: object
    ) -> object:
        ctx = original_test_request_context(self, *args, **kwargs)
        if not hasattr(ctx, "__aenter__"):
            ctx.__aenter__ = AsyncMock(return_value=ctx)
            ctx.__aexit__ = AsyncMock(return_value=None)
        return ctx

    # Patch the methods
    Quart.test_client = patched_test_client
    Quart.test_request_context = patched_test_request_context

    yield

    # Restore original methods after tests
    Quart.test_client = original_test_client
    Quart.test_request_context = original_test_request_context


@pytest.fixture
def csrf_headers() -> dict[str, str]:
    """Create CSRF headers for testing."""
    from neuron_server.controllers.csrf import create_session_cookie

    cookie_value, csrf_token = create_session_cookie("test_user_id", include_csrf=True)

    return {
        "X-CSRF-Token": csrf_token,
        "Cookie": f"neuron_session={cookie_value}"
    }


@pytest.fixture(autouse=True)
def bypass_csrf_in_tests(request) -> None:
    """Bypass CSRF checks in all tests except CSRF-specific tests."""
    # Skip bypass for CSRF-specific tests
    test_file = request.node.fspath.basename if hasattr(request.node, 'fspath') else ''
    if 'test_csrf' in test_file:
        yield
        return

    # Patch Quart's test request context to add CSRF cookies automatically
    from quart import Quart

    from neuron_server.controllers.csrf import create_session_cookie

    # Save original test_request_context
    original_test_request_context = Quart.test_request_context

    def patched_test_request_context(self, *args, **kwargs):
        """Create test request context with CSRF headers automatically added."""
        ctx = original_test_request_context(self, *args, **kwargs)

        # Save original push method
        original_push = ctx.push

        async def patched_push():
            # Call original push
            await original_push()

            # Add CSRF data to the request
            from quart import request as quart_request

            # Only modify for non-GET requests
            if quart_request.method not in ["GET", "HEAD", "OPTIONS"]:
                # Create valid session cookie with CSRF token
                cookie_value, csrf_token = create_session_cookie(
                    "test_user_id", include_csrf=True
                )

                # Mock the cookies
                class MockCookies(dict):
                    def get(self, key, default=None):
                        if key == "neuron_session":
                            return cookie_value
                        return super().get(key, default)

                # Set mock cookies
                quart_request.cookies = MockCookies()

                # Mock headers to include CSRF token
                original_get = quart_request.headers.get

                def mock_get(key, default=None):
                    if key.lower() == "x-csrf-token":
                        return csrf_token
                    return original_get(key, default)

                quart_request.headers.get = mock_get

                # Set session data attributes
                quart_request.user_id = "test_user_id"
                quart_request.session_data = {
                    "user_id": "test_user_id", "csrf_token": csrf_token
                }

        ctx.push = patched_push
        return ctx

    # Save original test_client
    original_test_client = Quart.test_client

    def patched_test_client(self):
        """Create test client with automatic CSRF headers."""
        client = original_test_client(self)

        # Save original methods
        original_post = client.post
        original_put = client.put
        original_patch = client.patch
        original_delete = client.delete

        # Create wrapper functions that add CSRF headers
        async def wrapped_post(path, **kwargs):
            headers = kwargs.get('headers', {})
            # Add CSRF headers if not present
            if 'X-CSRF-Token' not in headers and 'Cookie' not in headers:
                cookie_value, csrf_token = create_session_cookie(
                    "test_user_id", include_csrf=True
                )
                headers['X-CSRF-Token'] = csrf_token
                headers['Cookie'] = f"neuron_session={cookie_value}"
                kwargs['headers'] = headers
            return await original_post(path, **kwargs)

        async def wrapped_put(path, **kwargs):
            headers = kwargs.get('headers', {})
            if 'X-CSRF-Token' not in headers and 'Cookie' not in headers:
                cookie_value, csrf_token = create_session_cookie(
                    "test_user_id", include_csrf=True
                )
                headers['X-CSRF-Token'] = csrf_token
                headers['Cookie'] = f"neuron_session={cookie_value}"
                kwargs['headers'] = headers
            return await original_put(path, **kwargs)

        async def wrapped_patch(path, **kwargs):
            headers = kwargs.get('headers', {})
            if 'X-CSRF-Token' not in headers and 'Cookie' not in headers:
                cookie_value, csrf_token = create_session_cookie(
                    "test_user_id", include_csrf=True
                )
                headers['X-CSRF-Token'] = csrf_token
                headers['Cookie'] = f"neuron_session={cookie_value}"
                kwargs['headers'] = headers
            return await original_patch(path, **kwargs)

        async def wrapped_delete(path, **kwargs):
            headers = kwargs.get('headers', {})
            if 'X-CSRF-Token' not in headers and 'Cookie' not in headers:
                cookie_value, csrf_token = create_session_cookie(
                    "test_user_id", include_csrf=True
                )
                headers['X-CSRF-Token'] = csrf_token
                headers['Cookie'] = f"neuron_session={cookie_value}"
                kwargs['headers'] = headers
            return await original_delete(path, **kwargs)

        # Replace methods
        client.post = wrapped_post
        client.put = wrapped_put
        client.patch = wrapped_patch
        client.delete = wrapped_delete

        return client

    # Apply patches
    Quart.test_request_context = patched_test_request_context
    Quart.test_client = patched_test_client

    # Also patch extract_csrf_token to return the correct token and verify_cookie_data
    with (
        patch("neuron_server.controllers.csrf.extract_csrf_token") as mock_extract,
        patch("neuron_server.controllers.csrf.verify_cookie_data") as mock_verify,
    ):
        # Make extract_csrf_token return the same token that's in the cookie
        async def mock_extract_csrf(req):
            # Get the cookie from the request to extract the CSRF token
            cookie = req.cookies.get("neuron_session")
            if cookie:
                from neuron_server.controllers.csrf import (
                    verify_cookie_data as original_verify,
                )
                try:
                    # Try to use the real verify function
                    cookie_data = original_verify(cookie)
                    if cookie_data:
                        return cookie_data.get("csrf_token", "test_csrf_token")
                except Exception:
                    pass
            return "test_csrf_token"

        mock_extract.side_effect = mock_extract_csrf

        # Make verify_cookie_data handle test cookies
        def mock_verify_func(cookie):
            if cookie == "test_user_id":
                # Old style test cookie for backward compatibility
                return {"user_id": "test_user_id"}
            # For any other cookie, return valid test data
            return {"user_id": "test_user_id", "csrf_token": "test_csrf_token"}

        mock_verify.side_effect = mock_verify_func

        yield

    # Restore originals
    Quart.test_request_context = original_test_request_context
    Quart.test_client = original_test_client
