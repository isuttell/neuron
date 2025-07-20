"""Tests for HTTP decorators."""

import pytest
from quart import Quart, Response

from neuron_server.config import config
from neuron_server.decorators.http_decorators import (
    RateLimitExceededError,
    cache_control,
    cors,
    rate_limit,
)


@pytest.fixture
def app() -> Quart:
    """Create test Quart application."""
    return Quart(__name__)


@pytest.mark.asyncio
async def test_cors_default_headers(app: Quart) -> None:
    """Test CORS decorator with default headers."""

    @app.route("/test")
    @cors()
    async def test_route() -> Response:
        return Response("test")

    async with app.test_client() as client:
        # Test with allowed origin in debug mode
        if config.debug:
            response = await client.get(
                "/test", headers={"Origin": "http://localhost:5176"}
            )
            assert (
                response.headers["Access-Control-Allow-Origin"]
                == "http://localhost:5176"
            )
        else:
            response = await client.get(
                "/test", headers={"Origin": "https://neuron.zaks.io"}
            )
            assert (
                response.headers["Access-Control-Allow-Origin"]
                == "https://neuron.zaks.io"
            )
        assert (
            response.headers["Access-Control-Allow-Methods"]
            == "GET, POST, PUT, DELETE, OPTIONS"
        )
        assert (
            response.headers["Access-Control-Allow-Headers"]
            == "Content-Type, Authorization"
        )
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

        # Test with disallowed origin - no CORS headers should be added
        response = await client.get("/test", headers={"Origin": "http://evil.com"})
        assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.asyncio
async def test_cors_custom_headers(app: Quart) -> None:
    """Test CORS decorator with custom headers."""
    origins = ["http://localhost:3000"]
    methods = ["GET", "POST"]
    headers = ["X-Custom-Header"]

    @app.route("/test")
    @cors(
        allowed_origins=origins,
        allowed_methods=methods,
        allowed_headers=headers,
    )
    async def test_route() -> Response:
        return Response("test")

    async with app.test_client() as client:
        # Test with allowed origin
        response = await client.get(
            "/test", headers={"Origin": "http://localhost:3000"}
        )
        assert response.headers["Access-Control-Allow-Origin"] == origins[0]
        assert response.headers["Access-Control-Allow-Methods"] == "GET, POST"
        assert response.headers["Access-Control-Allow-Headers"] == "X-Custom-Header"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"

        # Test with disallowed origin - no CORS headers should be added
        response = await client.get("/test", headers={"Origin": "http://evil.com"})
        assert "Access-Control-Allow-Origin" not in response.headers


@pytest.mark.asyncio
async def test_cache_control_max_age(app: Quart) -> None:
    """Test cache control decorator with max age."""

    @app.route("/test")
    @cache_control(max_age=3600)
    async def test_route() -> Response:
        return Response("test")

    async with app.test_client() as client:
        response = await client.get("/test")
        assert response.headers["Cache-Control"] == "max-age=3600"


@pytest.mark.asyncio
async def test_cache_control_no_cache(app: Quart) -> None:
    """Test cache control decorator with no cache."""

    @app.route("/test")
    @cache_control(no_cache=True)
    async def test_route() -> Response:
        return Response("test")

    async with app.test_client() as client:
        response = await client.get("/test")
        assert response.headers["Cache-Control"] == "no-cache"


@pytest.mark.asyncio
async def test_cache_control_private(app: Quart) -> None:
    """Test cache control decorator with private directive."""

    @app.route("/test")
    @cache_control(private=True)
    async def test_route() -> Response:
        return Response("test")

    async with app.test_client() as client:
        response = await client.get("/test")
        assert response.headers["Cache-Control"] == "private"


@pytest.mark.asyncio
async def test_cache_control_public(app: Quart) -> None:
    """Test cache control decorator with public directive."""

    @app.route("/test")
    @cache_control(public=True)
    async def test_route() -> Response:
        return Response("test")

    async with app.test_client() as client:
        response = await client.get("/test")
        assert response.headers["Cache-Control"] == "public"


@pytest.mark.asyncio
async def test_cache_control_immutable(app: Quart) -> None:
    """Test cache control decorator with immutable directive."""

    @app.route("/test")
    @cache_control(immutable=True)
    async def test_route() -> Response:
        return Response("test")

    async with app.test_client() as client:
        response = await client.get("/test")
        assert response.headers["Cache-Control"] == "immutable"


@pytest.mark.asyncio
async def test_cache_control_multiple_directives(app: Quart) -> None:
    """Test cache control decorator with multiple directives."""

    @app.route("/test")
    @cache_control(max_age=3600, public=True, immutable=True)
    async def test_route() -> Response:
        return Response("test")

    async with app.test_client() as client:
        response = await client.get("/test")
        assert response.headers["Cache-Control"] == "max-age=3600, public, immutable"


@pytest.mark.asyncio
async def test_rate_limit_disabled(app: Quart) -> None:
    """Test rate limit decorator when disabled."""

    @app.route("/test")
    @rate_limit(enabled=False)
    async def test_route() -> Response:
        return Response("success")

    async with app.test_client() as client:
        response = await client.get("/test")
        assert response.status_code == 200
        assert await response.get_data() == b"success"


@pytest.mark.asyncio
async def test_rate_limit_decorator_types(app: Quart) -> None:
    """Test that different rate limit types can be configured."""

    @app.route("/api/test")
    @rate_limit(limit_type="api")
    async def api_route() -> Response:
        return Response("api")

    @app.route("/static/test")
    @rate_limit(limit_type="static")
    async def static_route() -> Response:
        return Response("static")

    # Test that decorators can be applied without error
    assert hasattr(api_route, "__wrapped__")
    assert hasattr(static_route, "__wrapped__")


def test_rate_limit_exceeded_error() -> None:
    """Test RateLimitExceededError has correct attributes."""
    error = RateLimitExceededError(
        retry_after=60, limit_type="requests per minute", limit_value=100
    )

    assert error.retry_after == 60
    assert error.limit_type == "requests per minute"
    assert error.limit_value == 100
    assert str(error) == "Rate limit exceeded: 100 requests per minute"
