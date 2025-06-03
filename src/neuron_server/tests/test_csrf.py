from datetime import datetime, timedelta

import pytest
from quart import Quart

from neuron_server.controllers.csrf import (
    create_session_cookie,
    extract_csrf_token,
    generate_csrf_token,
    requires_csrf,
    sign_cookie_data,
    verify_cookie_data,
)


class TestCSRFTokenGeneration:
    def test_generate_csrf_token(self):
        """Test CSRF token generation."""
        token1 = generate_csrf_token()
        token2 = generate_csrf_token()

        # Tokens should be unique
        assert token1 != token2

        # Tokens should be URL-safe
        assert all(c.isalnum() or c in "-_" for c in token1)

        # Tokens should be of reasonable length
        assert len(token1) > 20


class TestCookieSigning:
    def test_sign_and_verify_cookie_data(self):
        """Test cookie signing and verification."""
        data = {
            "user_id": "test123",
            "csrf_token": "test_token",
            "expires": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }

        # Sign the data
        signed = sign_cookie_data(data)
        assert signed is not None
        assert isinstance(signed, str)

        # Verify the signed data
        verified = verify_cookie_data(signed)
        assert verified is not None
        assert verified["user_id"] == data["user_id"]
        assert verified["csrf_token"] == data["csrf_token"]

    def test_verify_expired_cookie(self):
        """Test that expired cookies are rejected."""
        data = {
            "user_id": "test123",
            "expires": (datetime.utcnow() - timedelta(hours=1)).isoformat()
        }

        signed = sign_cookie_data(data)
        verified = verify_cookie_data(signed)

        assert verified is None

    def test_verify_tampered_cookie(self):
        """Test that tampered cookies are rejected."""
        data = {"user_id": "test123"}
        signed = sign_cookie_data(data)

        # Tamper with the cookie
        tampered = signed[:-5] + "xxxxx"

        verified = verify_cookie_data(tampered)
        assert verified is None

    def test_verify_cookie_without_padding(self):
        """Test that cookies without proper base64 padding are handled correctly."""
        data = {
            "user_id": "test123",
            "csrf_token": "test_token",
            "expires": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }

        # Sign the data
        signed = sign_cookie_data(data)

        # Remove padding from the base64 string
        signed_no_padding = signed.rstrip('=')

        # Verify that the cookie can still be decoded
        verified = verify_cookie_data(signed_no_padding)
        assert verified is not None
        assert verified["user_id"] == data["user_id"]
        assert verified["csrf_token"] == data["csrf_token"]

    def test_verify_cookie_with_auth0_user_id(self):
        """Test cookies with Auth0-style user IDs (containing pipes) work correctly."""
        data = {
            "user_id": "auth0|677842260dc433462eaf13a6",
            "csrf_token": "test_token",
            "expires": (datetime.utcnow() + timedelta(hours=1)).isoformat()
        }

        # Sign the data
        signed = sign_cookie_data(data)
        assert signed is not None

        # Verify the signed data
        verified = verify_cookie_data(signed)
        assert verified is not None
        assert verified["user_id"] == "auth0|677842260dc433462eaf13a6"
        assert verified["csrf_token"] == data["csrf_token"]


class TestSessionCookie:
    def test_create_session_cookie_with_csrf(self):
        """Test creating a session cookie with CSRF token."""
        cookie, csrf_token = create_session_cookie("user123", include_csrf=True)

        assert cookie is not None
        assert csrf_token is not None

        # Verify the cookie contains correct data
        data = verify_cookie_data(cookie)
        assert data is not None
        assert data["user_id"] == "user123"
        assert data["csrf_token"] == csrf_token

    def test_create_session_cookie_without_csrf(self):
        """Test creating a session cookie without CSRF token."""
        cookie, csrf_token = create_session_cookie("user123", include_csrf=False)

        assert cookie is not None
        assert csrf_token is None

        # Verify the cookie contains correct data
        data = verify_cookie_data(cookie)
        assert data is not None
        assert data["user_id"] == "user123"
        assert "csrf_token" not in data


@pytest.mark.asyncio
class TestCSRFDecorator:
    async def test_requires_csrf_with_valid_token(self):
        """Test CSRF decorator with valid token."""
        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        # Create a valid session cookie with CSRF
        cookie_value, csrf_token = create_session_cookie("user123")

        async with app.test_client() as client:
            # Set cookie using set_cookie with proper parameters
            client.set_cookie(
                server_name="localhost",
                key="neuron_session",
                value=cookie_value
            )

            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": csrf_token}
            )

            assert response.status_code == 200
            data = await response.get_json()
            assert data["status"] == "ok"

    async def test_requires_csrf_missing_token(self):
        """Test CSRF decorator with missing token."""
        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        # Create a valid session cookie with CSRF
        cookie_value, _ = create_session_cookie("user123")

        async with app.test_client() as client:
            # Set cookie using set_cookie
            client.set_cookie(
                server_name="localhost",
                key="neuron_session",
                value=cookie_value
            )

            # No CSRF token in request
            response = await client.post("/test")

            assert response.status_code == 403

    async def test_requires_csrf_invalid_token(self):
        """Test CSRF decorator with invalid token."""
        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        # Create a valid session cookie with CSRF
        cookie_value, _ = create_session_cookie("user123")

        async with app.test_client() as client:
            # Set cookie using set_cookie
            client.set_cookie(
                server_name="localhost",
                key="neuron_session",
                value=cookie_value
            )

            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": "invalid_token"}
            )

            assert response.status_code == 403

    async def test_requires_csrf_skips_safe_methods(self):
        """Test that CSRF is skipped for safe HTTP methods."""
        app = Quart(__name__)

        @app.route("/test", methods=["GET", "POST"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        async with app.test_client() as client:
            # GET request should work without CSRF
            response = await client.get("/test")
            assert response.status_code == 200

    async def test_requires_csrf_form_data(self):
        """Test CSRF token extraction from form data."""
        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        @requires_csrf
        async def test_endpoint():
            return {"status": "ok"}

        # Create a valid session cookie with CSRF
        cookie_value, csrf_token = create_session_cookie("user123")

        async with app.test_client() as client:
            # Set cookie using set_cookie
            client.set_cookie(
                server_name="localhost",
                key="neuron_session",
                value=cookie_value
            )

            response = await client.post(
                "/test",
                form={"csrf_token": csrf_token, "message": "test"}
            )

            assert response.status_code == 200


class TestCSRFExtraction:
    @pytest.mark.asyncio
    async def test_extract_csrf_from_header(self):
        """Test extracting CSRF token from header."""
        app = Quart(__name__)

        @app.route("/test", methods=["POST"])
        async def test_endpoint():
            from quart import request
            token = await extract_csrf_token(request)
            return {"token": token}

        async with app.test_client() as client:
            response = await client.post(
                "/test",
                headers={"X-CSRF-Token": "test_token"}
            )

            data = await response.get_json()
            assert data["token"] == "test_token"
