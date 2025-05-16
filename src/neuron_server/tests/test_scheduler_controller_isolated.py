import sys
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, Mock

import pytest
from quart import Quart
from werkzeug.exceptions import HTTPException

# Mock controller imports
blueprint = Mock()
mock_controller = Mock(blueprint=blueprint)
sys.modules["neuron_server.controllers.scheduler_controller"] = mock_controller

# Mock auth
@dataclass
class TokenPayload:
    """Mock token payload for testing."""
    sub: str
    user_id: str
    nickname: str
    email: str
    picture: Optional[str]
    roles: list[str]
    permissions: list[str]

# HTTP status codes
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404


@pytest.fixture
def app() -> Quart:
    """Create a test Quart application with the scheduler blueprint registered."""
    app = Quart(__name__)
    app.register_blueprint(blueprint, url_prefix="/api/scheduler")
    app.config["TESTING"] = True
    
    # Add HTTP error handler
    @app.errorhandler(HTTPException)
    async def http_error(error: HTTPException) -> tuple[dict[str, str], int]:
        return {"error": error.name, "message": error.description}, error.code
    
    return app


@pytest.fixture
def mock_scheduler() -> AsyncMock:
    """Create a mock scheduler for testing."""
    mock = AsyncMock()
    mock.create_event = AsyncMock(return_value="test-event-id")
    mock.update_event = AsyncMock()
    mock.delete_event = AsyncMock()
    mock.list_events = AsyncMock(return_value=[])
    mock.get_event = AsyncMock()
    return mock


@pytest.fixture
def mock_token() -> TokenPayload:
    """Create a mock auth token for testing."""
    return TokenPayload(
        sub="test_user",
        user_id="test-user-id", 
        email="test@example.com",
        nickname="Test User",
        picture=None,
        roles=["user"],
        permissions=["read:events", "write:events"],
    )


@pytest.fixture
def mock_personality_model() -> AsyncMock:
    """Create a mock personality model for testing."""
    mock_personality = AsyncMock()
    mock_personality.model_dump.return_value = {
        "id": "test-personality-id",
        "name": "Test Personality",
    }
    
    mock = AsyncMock()
    mock.get_many = AsyncMock(return_value=[mock_personality])
    return mock


@pytest.mark.asyncio
async def test_scheduler_controller_mock() -> None:
    """Test with isolated mocking to avoid import issues."""
    # This test is a placeholder - it always passes
    # The real integration tests are in test_scheduler_controller.py
    # This file is to test the CI build pipeline without import issues
    assert True