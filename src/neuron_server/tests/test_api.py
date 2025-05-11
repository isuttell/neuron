import asyncio
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from quart import Quart
from quart.testing.connections import WebsocketDisconnectError
from werkzeug.exceptions import NotFound

from neuron_server.api import app as neuron_app
from neuron_server.config import config
from neuron_server.controllers.auth import TokenPayload


@pytest.fixture
def app() -> Quart:
    return neuron_app


@pytest.fixture
def mock_pool() -> MagicMock:
    with patch("neuron_server.api.pool") as mock:
        mock.check = AsyncMock()
        yield mock


@pytest.fixture
def mock_redis() -> MagicMock:
    with patch("neuron_server.api.client") as mock:
        mock.ping = AsyncMock()
        mock.pubsub = MagicMock()
        yield mock


@pytest.fixture
def mock_scheduler() -> MagicMock:
    with patch("neuron_server.api.scheduler") as mock:
        mock.start = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_health_check(
    app: Quart, mock_pool: MagicMock, mock_redis: MagicMock
) -> None:
    async with app.test_client() as client:
        response = await client.get("/status")
        assert response.status_code == HTTPStatus.OK
        data = await response.get_json()
        assert data["server"] == "neuron"
        assert data["status"] == "healthy"
        mock_pool.check.assert_called_once()
        mock_redis.ping.assert_called_once()


@pytest.mark.asyncio
async def test_startup(app: Quart, mock_scheduler: MagicMock) -> None:
    await app.startup()
    mock_scheduler.start.assert_called_once()


@pytest.mark.asyncio
async def test_index_routes(app: Quart) -> None:
    with patch("neuron_server.api.blueprint.send_static_file") as mock_send:
        mock_send.return_value = "test"
        test_routes = [
            "/",
            "/thread/123",
            "/personalities",
            "/personality/456",
            "/personality/456/embeddings",
            "/gallery",
            "/code-viewer",
            "/stats",
            "/prompts",
            "/scheduled",
            "/providers",
            "/share/789",
        ]

        async with app.test_client() as client:
            for route in test_routes:
                response = await client.get(route)
                assert response.status_code == HTTPStatus.OK


@pytest.mark.asyncio
async def test_static_file_not_found(app: Quart) -> None:
    async with app.test_client() as client:
        # Include a session cookie to pass the requires_cookie check
        response = await client.get(
            "/static/nonexistent.jpg",
            headers={"Cookie": "neuron_session=test_user_id"}
        )
        assert response.status_code == HTTPStatus.NOT_FOUND
        data = await response.get_data()
        assert b"File not found" in data


@pytest.mark.asyncio
async def test_static_file_unauthorized(app: Quart) -> None:
    """Test that accessing static files without a cookie returns 401 Unauthorized."""
    # Save original value and temporarily set to True for this test
    original_value = config.static_require_auth
    config.static_require_auth = True

    try:
        async with app.test_client() as client:
            # Request without a session cookie
            response = await client.get("/static/some-image.jpg")
            assert response.status_code == HTTPStatus.UNAUTHORIZED
            data = await response.get_data()
            assert b"Authentication required" in data
    finally:
        # Restore original value
        config.static_require_auth = original_value


@pytest.mark.asyncio
async def test_openai_error_handler(app: Quart) -> None:
    from openai import APIError

    with patch("neuron_server.api.logger") as mock_logger:
        error = APIError(
            "Test OpenAI error",
            request=MagicMock(),
            body={"error": {"message": "Test OpenAI error"}},
        )
        response = await app.handle_user_exception(error)
        assert response[1] == HTTPStatus.BAD_REQUEST
        data = response[0]
        assert data["error"] == "API Error"
        assert data["message"] == "Test OpenAI error"
        mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_http_error_handler(app: Quart) -> None:
    with patch("neuron_server.api.logger") as mock_logger:
        error = NotFound()
        response = await app.handle_user_exception(error)
        assert response[1] == HTTPStatus.NOT_FOUND
        data = response[0]
        assert data["error"] == "Not Found"
        mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_internal_error_handler(app: Quart) -> None:
    with patch("neuron_server.api.logger") as mock_logger:
        error = ValueError("Test error")
        response = await app.handle_user_exception(error)
        assert response[1] == HTTPStatus.INTERNAL_SERVER_ERROR
        data = response[0]
        assert data["error"] == "Internal Server Error"
        assert data["message"] == "Test error"
        mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_webhook_prompt_api_key_auth(app: Quart) -> None:
    """Test that the webhook prompt endpoint requires a valid API key."""
    # Save the original API key and set a test key
    original_api_key = config.api_key
    test_api_key = "test_api_key_12345"
    config.api_key = test_api_key

    # Mock the execute_agent function to avoid actually executing the agent
    with patch(
        "neuron_server.controllers.webhook_controller.execute_agent"
    ) as mock_execute:
        mock_execute.return_value = "Test response"

        # Test data
        test_data = {
            "prompt": "Test prompt",
            "personality_id": str(uuid4())
        }

        async with app.test_client() as client:
            # Test with no API key
            response = await client.post("/api/webhooks/prompt", json=test_data)
            assert response.status_code == HTTPStatus.UNAUTHORIZED

            # Test with invalid API key
            response = await client.post(
                "/api/webhooks/prompt",
                json=test_data,
                headers={"X-API-Key": "invalid_key"}
            )
            assert response.status_code == HTTPStatus.UNAUTHORIZED

            # Test with valid API key
            response = await client.post(
                "/api/webhooks/prompt",
                json=test_data,
                headers={"X-API-Key": test_api_key}
            )
            assert response.status_code == HTTPStatus.OK
            data = await response.get_json()
            assert data["status"] == "success"
            assert data["content"] == "Test response"

            # Verify the same for the home_prompt endpoint
            response = await client.post(
                "/api/webhooks/home_prompt",
                json=test_data,
                headers={"X-API-Key": test_api_key}
            )
            assert response.status_code == HTTPStatus.OK

    # Restore the original API key
    config.api_key = original_api_key


@pytest.mark.skip(reason="Websocket tests are unstable")
@pytest.mark.asyncio
async def test_websocket_invalid_token(app: Quart) -> None:
    with patch(
        "neuron_server.api.decode_token", side_effect=ValueError("Invalid token")
    ):
        test_client = app.test_client()
        try:
            async with test_client.websocket("/ws") as test_websocket:
                await test_websocket.send("Bearer=invalid_token")
                await test_websocket.receive()
        except WebsocketDisconnectError as error:
            assert error.status_code == HTTPStatus.UNAUTHORIZED


@pytest.mark.skip(reason="Websocket tests are unstable")
@pytest.mark.asyncio
async def test_websocket_valid_connection(app: Quart) -> None:
    mock_token = TokenPayload(
        user_id="test_user",
        roles=[],
        email="test@example.com",
        nickname="test",
        permissions=[],
    )

    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    mock_pubsub.get_message = AsyncMock(return_value=None)

    with (
        patch("neuron_server.api.decode_token", new_callable=AsyncMock) as mock_decode,
        patch("neuron_server.api.logger") as mock_logger,
        patch("neuron_server.api.client") as mock_client,
    ):
        mock_decode.return_value = mock_token
        mock_client.pubsub.return_value.__aenter__.return_value = mock_pubsub

        test_client = app.test_client()
        async with test_client.websocket("/ws") as test_websocket:
            await test_websocket.send("Bearer=valid_token")
            # Wait for connection to be established
            await asyncio.sleep(0.1)
            # Verify connection logged
            mock_logger.info.assert_called_with("Connected (test_user)")
            # Close websocket to trigger disconnect
            await test_websocket.close()
            # Wait for disconnect to be logged
            await asyncio.sleep(0.1)
            # Verify disconnect logged
            mock_logger.info.assert_called_with("Disconnected (test_user)")
