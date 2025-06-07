"""Comprehensive CSRF test coverage"""

import pytest
from quart import Quart

from neuron_server.controllers.csrf import (
    create_session_cookie,
    requires_csrf,
    requires_csrf_or_api_key,
    sign_cookie_data,
    verify_cookie_data,
)


@pytest.mark.asyncio
class TestCSRFEdgeCases:
    """Test edge cases and error conditions"""

    async def test_csrf_no_cookie(self):
        """Test CSRF without any session cookie"""
        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        async with app.test_client() as client:
            response = await client.post(
                "/test", headers={"X-CSRF-Token": "some_token"}
            )
            assert response.status_code == 403

    async def test_csrf_invalid_cookie_format(self):
        """Test CSRF with malformed cookie"""
        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        async with app.test_client() as client:
            client.set_cookie(
                server_name="localhost",
                key="neuron_session",
                value="invalid_base64_cookie!",
            )

            response = await client.post("/test", headers={"X-CSRF-Token": "token"})
            assert response.status_code == 403

    async def test_csrf_cookie_without_csrf_token(self):
        """Test cookie that doesn't contain CSRF token"""
        # Create cookie without CSRF
        data = {"user_id": "test123"}
        cookie = sign_cookie_data(data)

        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        async with app.test_client() as client:
            client.set_cookie(
                server_name="localhost", key="neuron_session", value=cookie
            )

            response = await client.post("/test", headers={"X-CSRF-Token": "token"})
            assert response.status_code == 403


@pytest.mark.asyncio
class TestCSRFWithConfig:
    """Test CSRF with configuration changes"""

    async def test_csrf_with_custom_secret_key(self):
        """Test CSRF with custom secret key"""
        from unittest.mock import patch

        # Mock the config to have a custom secret key
        with patch("neuron_server.controllers.csrf.config") as mock_config:
            mock_config.secret_key = "test-secret-key"

            # Create cookie with this key
            cookie_value, csrf_token = create_session_cookie("user123")

            # Verify it works with the same mocked config
            data = verify_cookie_data(cookie_value)
            assert data is not None
            assert data["user_id"] == "user123"
            assert data["csrf_token"] == csrf_token

    async def test_requires_csrf_or_api_key_missing_both(self):
        """Test endpoint that requires either CSRF or API key with neither provided"""
        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        @requires_csrf_or_api_key
        async def test_endpoint():
            return {"status": "ok"}

        async with app.test_client() as client:
            response = await client.post("/test")
            assert response.status_code == 403


@pytest.mark.asyncio
class TestCSRFMethods:
    """Test CSRF on different HTTP methods"""

    async def test_csrf_on_put(self):
        """Test CSRF on PUT requests"""
        app = Quart(__name__)

        @app.route("/test", methods=["PUT"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        cookie_value, csrf_token = create_session_cookie("user123")

        async with app.test_client() as client:
            client.set_cookie(
                server_name="localhost", key="neuron_session", value=cookie_value
            )

            # Without CSRF
            response = await client.put("/test")
            assert response.status_code == 403

            # With CSRF
            response = await client.put("/test", headers={"X-CSRF-Token": csrf_token})
            assert response.status_code == 200

    async def test_csrf_on_delete(self):
        """Test CSRF on DELETE requests"""
        app = Quart(__name__)

        @app.route("/test", methods=["DELETE"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        cookie_value, csrf_token = create_session_cookie("user123")

        async with app.test_client() as client:
            client.set_cookie(
                server_name="localhost", key="neuron_session", value=cookie_value
            )

            # Without CSRF
            response = await client.delete("/test")
            assert response.status_code == 403

            # With CSRF
            response = await client.delete(
                "/test", headers={"X-CSRF-Token": csrf_token}
            )
            assert response.status_code == 200

    async def test_csrf_on_patch(self):
        """Test CSRF on PATCH requests"""
        app = Quart(__name__)

        @app.route("/test", methods=["PATCH"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        cookie_value, csrf_token = create_session_cookie("user123")

        async with app.test_client() as client:
            client.set_cookie(
                server_name="localhost", key="neuron_session", value=cookie_value
            )

            # Without CSRF
            response = await client.patch("/test")
            assert response.status_code == 403

            # With CSRF
            response = await client.patch("/test", headers={"X-CSRF-Token": csrf_token})
            assert response.status_code == 200

    async def test_csrf_skips_head_options(self):
        """Test that CSRF is skipped for HEAD and OPTIONS"""
        app = Quart(__name__)

        @app.route("/test", methods=["HEAD", "OPTIONS"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        async with app.test_client() as client:
            # HEAD should work without CSRF
            response = await client.head("/test")
            assert response.status_code == 200

            # OPTIONS should work without CSRF
            response = await client.options("/test")
            assert response.status_code == 200


@pytest.mark.asyncio
class TestRequestAttributes:
    """Test that request attributes are properly set"""

    async def test_request_attributes_set(self):
        """Test that user_id and session_data are attached to request"""
        app = Quart(__name__)

        captured_attrs = {}

        @app.route("/test", methods=["POST"])
        @requires_csrf
        async def test_endpoint():
            from quart import request

            captured_attrs["user_id"] = getattr(request, "user_id", None)
            captured_attrs["session_data"] = getattr(request, "session_data", None)
            return {"status": "ok"}

        cookie_value, csrf_token = create_session_cookie("user123")

        async with app.test_client() as client:
            client.set_cookie(
                server_name="localhost", key="neuron_session", value=cookie_value
            )

            response = await client.post("/test", headers={"X-CSRF-Token": csrf_token})

            assert response.status_code == 200
            assert captured_attrs["user_id"] == "user123"
            assert captured_attrs["session_data"]["user_id"] == "user123"
            assert captured_attrs["session_data"]["csrf_token"] == csrf_token
