import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from neuron_server.controllers.auth import TokenPayload

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
    with patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=mock_engine):
        with patch("neuron_server.database.get_session", return_value=mock_session):
            with patch("neuron_server.database.engine", mock_engine):
                with patch("neuron_server.database.start", AsyncMock()):
                    yield


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch) -> None:
    """Mock environment variables for testing."""
    # API Keys
    monkeypatch.setenv("OPENAI_API_KEY", "test-api-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-api-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-api-key")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test-api-key")
    monkeypatch.setenv("HF_TOKEN", "test-token")

    # Database Configs
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_USER", "test-user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "test-password")
    monkeypatch.setenv("POSTGRES_DB", "test-db")

    # Auth Config
    monkeypatch.setenv("AUTH0_DOMAIN", "test.auth0.com")
    monkeypatch.setenv("AUTH0_API_AUDIENCE", "test-audience")
    monkeypatch.setenv("AUTH0_CLIENT_ID", "test-client-id")


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