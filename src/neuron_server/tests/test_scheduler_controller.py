from dataclasses import dataclass
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from quart import Quart
from werkzeug.exceptions import BadRequest, HTTPException, NotFound

from neuron_server.controllers.auth import TokenPayload
from neuron_server.controllers.scheduler_controller import blueprint

# HTTP status codes
HTTP_OK = 200
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404


@dataclass
class ScheduleTestContext:
    """Context for scheduler controller tests."""
    token: TokenPayload
    auth_mock: dict[str, AsyncMock | Mock]
    event_id: str
    event: dict


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


@pytest.fixture(autouse=True)
async def mock_db_session() -> None:
    """Mock the database session to prevent actual database connections."""
    session_mock = AsyncMock()
    cm_mock = AsyncMock()
    cm_mock.__aenter__.return_value = session_mock
    cm_mock.__aexit__.return_value = None
    
    with (
        patch("neuron_server.database.get_session", return_value=cm_mock),
        patch("neuron_server.database.engine", new=AsyncMock()),
        patch("neuron_server.database.create_async_engine", return_value=AsyncMock()),
        patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=AsyncMock()),
    ):
        yield


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


@pytest.fixture
def mock_jwks() -> dict[str, list[dict[str, str]]]:
    """Create a mock JWKS response."""
    return {
        "keys": [
            {
                "kid": "test-kid",
                "kty": "RSA",
                "use": "sig",
                "n": "test",
                "e": "AQAB",
            }
        ]
    }


@pytest.fixture
def test_context(mock_token: TokenPayload) -> ScheduleTestContext:
    """Create a test context with common objects needed for tests."""
    event_id = str(uuid4())
    event = {
        "id": event_id,
        "user_id": mock_token.user_id,
        "cron": "0 0 * * *",
        "event_data": {"message": "test", "personality_id": "test-personality-id"},
    }
    
    # Mock the auth functions
    async def mock_decode_token(*_: object, **__: object) -> TokenPayload:
        return mock_token
    
    auth_mock = {
        "decode_token": AsyncMock(side_effect=mock_decode_token),
        "get_token_auth_header": Mock(return_value="test-token"),
        "get_jwks": AsyncMock(return_value={"keys": [{"kid": "test-kid"}]}),
    }
    
    return ScheduleTestContext(
        token=mock_token,
        auth_mock=auth_mock,
        event_id=event_id,
        event=event,
    )


@pytest.fixture
def mock_auth_decorators(test_context: ScheduleTestContext) -> None:
    """Mock the auth decorators to bypass Redis for JWKS caching."""
    with (
        patch(
            "neuron_server.controllers.auth.decode_token",
            side_effect=test_context.auth_mock["decode_token"],
        ),
        patch(
            "neuron_server.controllers.auth.get_token_auth_header",
            side_effect=test_context.auth_mock["get_token_auth_header"],
        ),
        patch(
            "neuron_server.controllers.auth.get_jwks",
            side_effect=test_context.auth_mock["get_jwks"],
        ),
    ):
        yield


@pytest.mark.asyncio
async def test_create_event(
    app: Quart, 
    mock_scheduler: AsyncMock,
    mock_auth_decorators: None,
) -> None:
    """Test creating a new scheduled event."""
    with patch("neuron_server.api.scheduler", mock_scheduler):
        test_client = app.test_client()
        payload = {
            "cron": "0 0 * * *",
            "event_data": {"message": "test", "personality_id": "test-personality-id"},
        }
        
        response = await test_client.post(
            "/api/scheduler/events",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        
        response_data = await response.get_json()
        assert response.status_code == HTTP_OK
        assert response_data == {"event_id": "test-event-id"}
        
        mock_scheduler.create_event.assert_awaited_once_with(
            cron="0 0 * * *",
            event_data={"message": "test", "personality_id": "test-personality-id"},
            user_id="test-user-id",
        )


@pytest.mark.asyncio
async def test_create_event_missing_body(
    app: Quart,
    mock_auth_decorators: None,
) -> None:
    """Test creating a new scheduled event with missing request body."""
    # Add handler for BadRequest exceptions
    @app.errorhandler(BadRequest)
    async def handle_bad_request(error: BadRequest) -> tuple[dict[str, str], int]:
        return (
            {"error": "Bad Request", "message": error.description},
            HTTP_BAD_REQUEST,
        )
        
    test_client = app.test_client()
    
    response = await test_client.post(
        "/api/scheduler/events",
        data="",  # Empty body
        headers={"Authorization": "Bearer test-token"},
    )
    
    assert response.status_code == HTTP_BAD_REQUEST
    response_data = await response.get_json()
    assert response_data["message"] == "Request body is required"


@pytest.mark.asyncio
async def test_update_event(
    app: Quart, 
    mock_scheduler: AsyncMock, 
    test_context: ScheduleTestContext,
    mock_auth_decorators: None,
) -> None:
    """Test updating an existing scheduled event."""
    event_id = test_context.event_id
    event = test_context.event
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = event
        
        test_client = app.test_client()
        payload = {
            "cron": "0 12 * * *",
            "event_data": {"message": "updated test"},
        }
        
        response = await test_client.put(
            f"/api/scheduler/events/{event_id}",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_OK
        response_data = await response.get_json()
        assert response_data == {"event_id": event_id}
        
        mock_scheduler.get_event.assert_awaited_once_with(event_id)
        mock_scheduler.update_event.assert_awaited_once_with(
            event_id=event_id,
            cron="0 12 * * *",
            event_data={"message": "updated test"},
        )


@pytest.mark.asyncio
async def test_update_event_not_found(
    app: Quart, 
    mock_scheduler: AsyncMock,
    mock_auth_decorators: None,
) -> None:
    """Test updating a non-existent scheduled event."""
    event_id = "non-existent-event-id"
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = None
        
        # Add handler for NotFound exceptions
        @app.errorhandler(NotFound)
        async def handle_not_found(error: NotFound) -> tuple[dict[str, str], int]:
            return {"error": "Not Found", "message": error.description}, HTTP_NOT_FOUND
            
        test_client = app.test_client()
        payload = {
            "cron": "0 12 * * *",
            "event_data": {"message": "updated test"},
        }
        
        response = await test_client.put(
            f"/api/scheduler/events/{event_id}",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_NOT_FOUND
        response_data = await response.get_json()
        assert response_data["message"] == "Event not found"


@pytest.mark.asyncio
async def test_update_event_different_user(
    app: Quart, 
    mock_scheduler: AsyncMock,
    test_context: ScheduleTestContext,
    mock_auth_decorators: None,
) -> None:
    """Test updating an event belonging to a different user."""
    event_id = test_context.event_id
    
    # Create event with different user_id
    event = test_context.event.copy()
    event["user_id"] = "different-user-id"  # Different from the token user_id
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = event
        
        # Add handler for NotFound exceptions
        @app.errorhandler(NotFound)
        async def handle_not_found(error: NotFound) -> tuple[dict[str, str], int]:
            return {"error": "Not Found", "message": error.description}, HTTP_NOT_FOUND
            
        test_client = app.test_client()
        payload = {
            "cron": "0 12 * * *",
            "event_data": {"message": "updated test"},
        }
        
        response = await test_client.put(
            f"/api/scheduler/events/{event_id}",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_NOT_FOUND
        response_data = await response.get_json()
        assert response_data["message"] == "Event not found"


@pytest.mark.asyncio
async def test_get_event(
    app: Quart, 
    mock_scheduler: AsyncMock,
    test_context: ScheduleTestContext,
    mock_auth_decorators: None,
) -> None:
    """Test getting details of a specific scheduled event."""
    event_id = test_context.event_id
    event = test_context.event
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = event
        
        test_client = app.test_client()
        response = await test_client.get(
            f"/api/scheduler/events/{event_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_OK
        response_data = await response.get_json()
        assert response_data == {"event": event}
        
        mock_scheduler.get_event.assert_awaited_once_with(event_id)


@pytest.mark.asyncio
async def test_get_event_not_found(
    app: Quart, 
    mock_scheduler: AsyncMock,
    mock_auth_decorators: None,
) -> None:
    """Test getting details of a non-existent scheduled event."""
    event_id = "non-existent-event-id"
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = None
        
        # Add handler for NotFound exceptions
        @app.errorhandler(NotFound)
        async def handle_not_found(error: NotFound) -> tuple[dict[str, str], int]:
            return {"error": "Not Found", "message": error.description}, HTTP_NOT_FOUND
            
        test_client = app.test_client()
        response = await test_client.get(
            f"/api/scheduler/events/{event_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_NOT_FOUND
        response_data = await response.get_json()
        assert response_data["message"] == "Event not found"


@pytest.mark.asyncio
async def test_get_event_different_user(
    app: Quart, 
    mock_scheduler: AsyncMock,
    test_context: ScheduleTestContext,
    mock_auth_decorators: None,
) -> None:
    """Test getting details of an event belonging to a different user."""
    event_id = test_context.event_id
    
    # Create event with different user_id
    event = test_context.event.copy()
    event["user_id"] = "different-user-id"  # Different from the token user_id
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = event
        
        # Add handler for NotFound exceptions
        @app.errorhandler(NotFound)
        async def handle_not_found(error: NotFound) -> tuple[dict[str, str], int]:
            return {"error": "Not Found", "message": error.description}, HTTP_NOT_FOUND
            
        test_client = app.test_client()
        response = await test_client.get(
            f"/api/scheduler/events/{event_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_NOT_FOUND
        response_data = await response.get_json()
        assert response_data["message"] == "Event not found"


class MockPersonality:
    """Mock personality for testing."""
    
    def __init__(self, personality_id: str, name: str) -> None:
        """Initialize mock personality."""
        self.id = personality_id
        self.name = name
        
    def model_dump(self) -> dict:
        """Return the model as a dictionary."""
        return {
            "id": self.id,
            "name": self.name,
        }


@pytest.mark.asyncio
async def test_list_events(
    app: Quart, 
    mock_scheduler: AsyncMock, 
    test_context: ScheduleTestContext,
    mock_auth_decorators: None,
) -> None:
    """Test listing all scheduled events for the authenticated user."""
    event_data = {"message": "test", "personality_id": "test-personality-id"}
    event_data2 = {"message": "another test", "personality_id": "test-personality-id"}
    
    mock_events = [
        {
            "id": "event-1",
            "user_id": "test-user-id",
            "cron": "0 0 * * *",
            "event_data": event_data,
        },
        {
            "id": "event-2",
            "user_id": "test-user-id",
            "cron": "0 12 * * *",
            "event_data": event_data2,
        },
    ]
    
    # Set the list_events return value
    mock_scheduler.list_events.return_value = mock_events
    
    mock_personality = MockPersonality("test-personality-id", "Test Personality")
    
    # Mock PersonalityModel.get_many to return a list of mock personalities
    async def mock_get_many(personality_ids: set) -> list[MockPersonality]:
        return [mock_personality]
    
    # Create shorter path names for better readability
    model_path = "neuron_server.models.personality_model.PersonalityModel"
    controller_path = "neuron_server.controllers.scheduler_controller.PersonalityModel"
    db_path = "neuron_server.database"
    
    with (
        patch("neuron_server.api.scheduler", mock_scheduler),
        patch(f"{model_path}.get_many", side_effect=mock_get_many),
        patch(f"{controller_path}.get_many", side_effect=mock_get_many),
        # Prevent database connections
        patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=AsyncMock()),
        patch(f"{db_path}.get_session", return_value=AsyncMock()),
    ):
        test_client = app.test_client()
        response = await test_client.get(
            "/api/scheduler/events",
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_OK
        response_data = await response.get_json()
        
        expected_data = {
            "events": mock_events,
            "personalities": [
                {"id": "test-personality-id", "name": "Test Personality"}
            ],
        }
        assert response_data == expected_data
        
        # Verify filter was applied correctly
        mock_scheduler.list_events.assert_awaited_once_with(
            filters={"user_id": "test-user-id"}
        )


@pytest.mark.asyncio
async def test_delete_event(
    app: Quart, 
    mock_scheduler: AsyncMock,
    test_context: ScheduleTestContext,
    mock_auth_decorators: None,
) -> None:
    """Test deleting a scheduled event."""
    event_id = test_context.event_id
    event = test_context.event
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = event
        
        test_client = app.test_client()
        response = await test_client.delete(
            f"/api/scheduler/events/{event_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_NO_CONTENT
        
        mock_scheduler.get_event.assert_awaited_once_with(event_id)
        mock_scheduler.delete_event.assert_awaited_once_with(event_id)


@pytest.mark.asyncio
async def test_delete_event_not_found(
    app: Quart, 
    mock_scheduler: AsyncMock,
    mock_auth_decorators: None,
) -> None:
    """Test deleting a non-existent scheduled event."""
    event_id = "non-existent-event-id"
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = None
        
        # Add handler for NotFound exceptions
        @app.errorhandler(NotFound)
        async def handle_not_found(error: NotFound) -> tuple[dict[str, str], int]:
            return {"error": "Not Found", "message": error.description}, HTTP_NOT_FOUND
            
        test_client = app.test_client()
        response = await test_client.delete(
            f"/api/scheduler/events/{event_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_NOT_FOUND
        response_data = await response.get_json()
        assert response_data["message"] == "Event not found"


@pytest.mark.asyncio
async def test_delete_event_different_user(
    app: Quart, 
    mock_scheduler: AsyncMock, 
    test_context: ScheduleTestContext,
    mock_auth_decorators: None,
) -> None:
    """Test deleting an event belonging to a different user."""
    event_id = test_context.event_id
    
    # Create event with different user_id
    event = test_context.event.copy()
    event["user_id"] = "different-user-id"  # Different from the token user_id
    
    with patch("neuron_server.api.scheduler", mock_scheduler):
        mock_scheduler.get_event.return_value = event
        
        # Add handler for NotFound exceptions
        @app.errorhandler(NotFound)
        async def handle_not_found(error: NotFound) -> tuple[dict[str, str], int]:
            return {"error": "Not Found", "message": error.description}, HTTP_NOT_FOUND
            
        test_client = app.test_client()
        response = await test_client.delete(
            f"/api/scheduler/events/{event_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        
        assert response.status_code == HTTP_NOT_FOUND
        response_data = await response.get_json()
        assert response_data["message"] == "Event not found"