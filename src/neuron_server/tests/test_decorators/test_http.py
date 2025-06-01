"""Tests for HTTP decorators."""

import pytest
from quart import Quart, Response

from neuron_server.config import config
from neuron_server.decorators.http_decorators import cache_control, cors


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
            response = await client.get("/test", headers={"Origin": "http://localhost:5173"})
            assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
        else:
            response = await client.get("/test", headers={"Origin": "https://neuron.zaks.io"})
            assert response.headers["Access-Control-Allow-Origin"] == "https://neuron.zaks.io"
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
        response = await client.get("/test", headers={"Origin": "http://localhost:3000"})
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
