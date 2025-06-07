import pytest
from quart import Quart, request

from neuron_server.controllers.csrf import (
    create_session_cookie,
    requires_csrf,
    requires_csrf_or_api_key,
)


@pytest.mark.asyncio
async def test_csrf_with_actual_request():
    """Test CSRF protection with actual request object."""
    app = Quart(__name__)

    test_result = {"called": False, "user_id": None}

    @app.route("/test", methods=["POST"])
    @requires_csrf
    async def test_endpoint():
        test_result["called"] = True
        test_result["user_id"] = request.user_id
        return {"status": "ok"}

    # Create session with CSRF
    cookie_value, csrf_token = create_session_cookie("user123")

    async with app.test_client() as client:
        # Make request with proper cookie header
        response = await client.post(
            "/test",
            headers={
                "X-CSRF-Token": csrf_token,
                "Cookie": f"neuron_session={cookie_value}",
            },
        )

        assert response.status_code == 200
        data = await response.get_json()
        assert data["status"] == "ok"
        assert test_result["called"] is True
        assert test_result["user_id"] == "user123"


@pytest.mark.asyncio
async def test_csrf_with_api_key():
    """Test CSRF or API key protection."""
    app = Quart(__name__)

    # Mock config for API key
    import neuron_server.config

    original_api_key = getattr(neuron_server.config.config, "api_key", None)
    neuron_server.config.config.api_key = "test-api-key"

    try:

        @app.route("/test", methods=["POST"])
        @requires_csrf_or_api_key
        async def test_endpoint():
            return {"status": "ok"}

        async with app.test_client() as client:
            # Test with API key (no CSRF needed)
            response = await client.post("/test", headers={"X-API-Key": "test-api-key"})
            assert response.status_code == 200

            # Test with invalid API key
            response = await client.post("/test", headers={"X-API-Key": "wrong-key"})
            assert response.status_code == 403
    finally:
        # Restore original config
        if original_api_key is not None:
            neuron_server.config.config.api_key = original_api_key
        else:
            delattr(neuron_server.config.config, "api_key")
