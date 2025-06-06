from http import HTTPStatus
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError
from quart import Quart
from werkzeug.exceptions import BadRequest

from neuron_server.api import app as neuron_app
from neuron_server.controllers.webhook_controller import PromptRequest


@pytest.fixture
def app() -> Quart:
    """Return the Quart app with patched test client and request context.

    The patching is done in conftest.py mock_quart_app fixture.
    """
    return neuron_app


@pytest.fixture
def valid_api_key() -> str:
    """Return a valid API key for testing."""
    return "test-api-key-123"


@pytest.fixture
def mock_config() -> AsyncMock:
    """Mock the config to set API key."""
    with patch("neuron_server.controllers.auth.config") as mock:
        mock.api_key = "test-api-key-123"
        yield mock


@pytest.fixture
def mock_execute_agent() -> AsyncMock:
    """Mock the execute_agent function."""
    with patch(
        "neuron_server.controllers.webhook_controller.execute_agent",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = "Test response from agent"
        yield mock


@pytest.fixture
def mock_rate_limiter() -> AsyncMock:
    """Mock the rate limiter to allow all requests."""
    with patch(
        "neuron_server.decorators.http_decorators._rate_limiter"
    ) as mock:
        mock._get_client_ip.return_value = "127.0.0.1"
        mock.check_limits = AsyncMock()
        yield mock


@pytest.mark.asyncio
async def test_prompt_success(
    app: Quart,
    valid_api_key: str,
    mock_config: AsyncMock,
    mock_execute_agent: AsyncMock,
    mock_rate_limiter: AsyncMock,
) -> None:
    """Test successful prompt execution."""
    personality_id = uuid4()
    prompt_text = "Test prompt"

    async with app.test_request_context(
        "/api/webhook/prompt",
        method="POST",
        json={
            "prompt": prompt_text,
            "personality_id": str(personality_id),
            "run_name": "test_run",
        },
        headers={"X-API-Key": valid_api_key},
    ):
        from neuron_server.controllers.webhook_controller import prompt

        result = await prompt()

        assert result["status"] == "success"
        assert result["content"] == "Test response from agent"

    # Verify execute_agent was called with correct parameters
    mock_execute_agent.assert_called_once()
    call_args = mock_execute_agent.call_args
    assert personality_id in call_args.kwargs.values()
    assert "Do not ask for confirmation" in call_args.kwargs["prompt"]
    assert prompt_text in call_args.kwargs["prompt"]


@pytest.mark.asyncio
async def test_prompt_missing_body(
    app: Quart,
    valid_api_key: str,
    mock_config: AsyncMock,
    mock_rate_limiter: AsyncMock,
) -> None:
    """Test prompt endpoint with missing request body."""
    async with app.test_request_context(
        "/api/webhook/prompt",
        method="POST",
        headers={"X-API-Key": valid_api_key},
    ):
        from neuron_server.controllers.webhook_controller import prompt

        with pytest.raises(BadRequest) as exc_info:
            await prompt()

        assert "Request body is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_prompt_invalid_body(
    app: Quart,
    valid_api_key: str,
    mock_config: AsyncMock,
    mock_rate_limiter: AsyncMock,
) -> None:
    """Test prompt endpoint with invalid request body."""
    async with app.test_request_context(
        "/api/webhook/prompt",
        method="POST",
        json={
            "prompt": "Test prompt",
            # Missing personality_id
        },
        headers={"X-API-Key": valid_api_key},
    ):
        from neuron_server.controllers.webhook_controller import prompt

        with pytest.raises(ValidationError):
            await prompt()


@pytest.mark.asyncio
async def test_prompt_missing_api_key(
    app: Quart,
    mock_config: AsyncMock,
    mock_rate_limiter: AsyncMock,
) -> None:
    """Test prompt endpoint without API key."""
    from werkzeug.exceptions import Unauthorized

    personality_id = uuid4()

    async with app.test_request_context(
        "/api/webhook/prompt",
        method="POST",
        json={
            "prompt": "Test prompt",
            "personality_id": str(personality_id),
        },
        # No X-API-Key header
    ):
        from neuron_server.controllers.webhook_controller import prompt

        with pytest.raises(Unauthorized) as exc_info:
            await prompt()

        assert "API key is required" in str(exc_info.value)


@pytest.mark.asyncio
async def test_prompt_invalid_api_key(
    app: Quart,
    mock_config: AsyncMock,
    mock_rate_limiter: AsyncMock,
) -> None:
    """Test prompt endpoint with invalid API key."""
    from werkzeug.exceptions import Unauthorized

    personality_id = uuid4()

    async with app.test_request_context(
        "/api/webhook/prompt",
        method="POST",
        json={
            "prompt": "Test prompt",
            "personality_id": str(personality_id),
        },
        headers={"X-API-Key": "invalid-key"},
    ):
        from neuron_server.controllers.webhook_controller import prompt

        with pytest.raises(Unauthorized) as exc_info:
            await prompt()

        assert "Invalid API key" in str(exc_info.value)


@pytest.mark.asyncio
async def test_prompt_no_server_api_key(
    app: Quart,
    mock_rate_limiter: AsyncMock,
) -> None:
    """Test prompt endpoint when server has no API key configured."""
    from werkzeug.exceptions import Unauthorized

    personality_id = uuid4()

    with patch("neuron_server.controllers.auth.config") as mock_config:
        mock_config.api_key = None

        async with app.test_request_context(
            "/api/webhook/prompt",
            method="POST",
            json={
                "prompt": "Test prompt",
                "personality_id": str(personality_id),
            },
            headers={"X-API-Key": "some-key"},
        ):
            from neuron_server.controllers.webhook_controller import prompt

            with pytest.raises(Unauthorized) as exc_info:
                await prompt()

            assert "API key is not configured on the server" in str(exc_info.value)


@pytest.mark.asyncio
async def test_prompt_rate_limit_exceeded(
    app: Quart,
    valid_api_key: str,
    mock_config: AsyncMock,
) -> None:
    """Test prompt endpoint when rate limit is exceeded."""
    from neuron_server.decorators.http_decorators import RateLimitExceededError

    personality_id = uuid4()

    with patch(
        "neuron_server.decorators.http_decorators._rate_limiter"
    ) as mock_limiter:
        mock_limiter._get_client_ip.return_value = "127.0.0.1"
        mock_limiter.check_limits = AsyncMock(
            side_effect=RateLimitExceededError(
                retry_after=60,
                limit_type="requests per minute",
                limit_value=60
            )
        )

        async with app.test_request_context(
            "/api/webhook/prompt",
            method="POST",
            json={
                "prompt": "Test prompt",
                "personality_id": str(personality_id),
            },
            headers={"X-API-Key": valid_api_key},
        ):
            from neuron_server.controllers.webhook_controller import prompt

            result = await prompt()

            # Rate limit decorator returns a response object
            assert result.status_code == HTTPStatus.TOO_MANY_REQUESTS
            json_data = await result.get_json()
            assert json_data["error"] == "rate_limit_exceeded"
            assert "Rate limit exceeded" in json_data["message"]


@pytest.mark.asyncio
async def test_prompt_with_optional_run_name(
    app: Quart,
    valid_api_key: str,
    mock_config: AsyncMock,
    mock_execute_agent: AsyncMock,
    mock_rate_limiter: AsyncMock,
) -> None:
    """Test prompt endpoint with optional run_name parameter."""
    personality_id = uuid4()

    async with app.test_request_context(
        "/api/webhook/prompt",
        method="POST",
        json={
            "prompt": "Test prompt",
            "personality_id": str(personality_id),
            # run_name is optional, not provided here
        },
        headers={"X-API-Key": valid_api_key},
    ):
        from neuron_server.controllers.webhook_controller import prompt

        result = await prompt()

        assert result["status"] == "success"
        assert result["content"] == "Test response from agent"


@pytest.mark.asyncio
async def test_home_prompt_endpoint(
    app: Quart,
    valid_api_key: str,
    mock_config: AsyncMock,
    mock_execute_agent: AsyncMock,
    mock_rate_limiter: AsyncMock,
) -> None:
    """Test that /home_prompt endpoint works the same as /prompt."""
    personality_id = uuid4()

    async with app.test_request_context(
        "/api/webhook/home_prompt",
        method="POST",
        json={
            "prompt": "Test prompt",
            "personality_id": str(personality_id),
        },
        headers={"X-API-Key": valid_api_key},
    ):
        from neuron_server.controllers.webhook_controller import prompt

        result = await prompt()

        assert result["status"] == "success"
        assert result["content"] == "Test response from agent"


@pytest.mark.asyncio
async def test_prompt_request_model_validation() -> None:
    """Test PromptRequest model validation."""
    personality_id = uuid4()

    # Valid request
    valid_request = PromptRequest(
        prompt="Test prompt",
        personality_id=personality_id,
        run_name="test_run",
    )
    assert valid_request.prompt == "Test prompt"
    assert valid_request.personality_id == personality_id
    assert valid_request.run_name == "test_run"

    # Valid request without run_name
    request_no_run = PromptRequest(
        prompt="Test prompt",
        personality_id=personality_id,
    )
    assert request_no_run.run_name is None

    # Invalid request - missing required fields
    with pytest.raises(ValidationError):
        PromptRequest(prompt="Test prompt")  # Missing personality_id

    with pytest.raises(ValidationError):
        PromptRequest(personality_id=personality_id)  # Missing prompt
