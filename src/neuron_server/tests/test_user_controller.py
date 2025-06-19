from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from quart import Quart

from neuron_server.api import app as neuron_app
from neuron_server.controllers.auth import TokenPayload
from neuron_server.models.user_model import UserModel


@pytest.fixture
def test_user() -> UserModel:
    """Create a test user."""
    return UserModel(
        id="test_user_id",
        email="test@example.com",
        nickname="Test User",
        picture="https://example.com/picture.jpg",
    )


@pytest.fixture
def app() -> Quart:
    """Return the Quart app with patched test client and request context."""
    return neuron_app


@pytest.fixture
def mock_token() -> TokenPayload:
    """Create a mock token for authentication."""
    return TokenPayload(
        sub="test_user",
        user_id="test-user-id",
        nickname="Test User",
        email="test@example.com",
        picture=None,
        roles=["user"],
        permissions=["read:users"],
    )


class TestUserController:
    """Tests for user controller endpoints."""

    @pytest.mark.asyncio
    async def test_search_users_by_email(
        self, app: Quart, test_user: UserModel
    ) -> None:
        """Test searching for users by email."""
        with patch(
            "neuron_server.controllers.auth.decode_token", new_callable=AsyncMock
        ) as mock_decode:
            mock_decode.return_value = TokenPayload(
                sub="test_user",
                user_id="test-user-id",
                nickname="Test User",
                email="test@example.com",
                picture=None,
                roles=["user"],
                permissions=["read:users"],
            )

            with patch.object(
                UserModel, "get_by_email", new_callable=AsyncMock
            ) as mock_get_by_email:
                mock_get_by_email.return_value = test_user

                async with app.test_client() as client:
                    response = await client.get(
                        "/api/users/?email=test@example.com",
                        headers={"Authorization": "Bearer test-token"},
                    )

                    assert response.status_code == HTTPStatus.OK
                    data = await response.get_json()
                    assert "users" in data
                    assert len(data["users"]) == 1
                    assert data["users"][0]["email"] == "test@example.com"
                    assert data["users"][0]["id"] == "test_user_id"
                    assert data["users"][0]["nickname"] == "Test User"

                    mock_get_by_email.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_search_users_no_email_param(self, app: Quart) -> None:
        """Test searching for users without email parameter returns empty list."""
        with patch(
            "neuron_server.controllers.auth.decode_token", new_callable=AsyncMock
        ) as mock_decode:
            mock_decode.return_value = TokenPayload(
                sub="test_user",
                user_id="test-user-id",
                nickname="Test User",
                email="test@example.com",
                picture=None,
                roles=["user"],
                permissions=["read:users"],
            )

            async with app.test_client() as client:
                response = await client.get(
                    "/api/users/",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == HTTPStatus.OK
                data = await response.get_json()
                assert "users" in data
                assert data["users"] == []

    @pytest.mark.asyncio
    async def test_search_users_not_found(self, app: Quart) -> None:
        """Test searching for users that don't exist returns empty list."""
        with patch(
            "neuron_server.controllers.auth.decode_token", new_callable=AsyncMock
        ) as mock_decode:
            mock_decode.return_value = TokenPayload(
                sub="test_user",
                user_id="test-user-id",
                nickname="Test User",
                email="test@example.com",
                picture=None,
                roles=["user"],
                permissions=["read:users"],
            )

            with patch.object(
                UserModel, "get_by_email", new_callable=AsyncMock
            ) as mock_get_by_email:
                mock_get_by_email.return_value = None

                async with app.test_client() as client:
                    response = await client.get(
                        "/api/users/?email=nonexistent@example.com",
                        headers={"Authorization": "Bearer test-token"},
                    )

                    assert response.status_code == HTTPStatus.OK
                    data = await response.get_json()
                    assert "users" in data
                    assert data["users"] == []

                    mock_get_by_email.assert_called_once_with("nonexistent@example.com")

    @pytest.mark.asyncio
    async def test_search_users_unauthorized(self, app: Quart) -> None:
        """Test searching for users without authentication returns 401."""
        async with app.test_client() as client:
            response = await client.get("/api/users/?email=test@example.com")

            assert response.status_code == HTTPStatus.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_login_user(self, app: Quart) -> None:
        """Test user login endpoint."""
        with patch(
            "neuron_server.controllers.auth.decode_token", new_callable=AsyncMock
        ) as mock_decode:
            mock_token = TokenPayload(
                sub="test_user",
                user_id="test-user-id",
                nickname="Test User",
                email="test@example.com",
                picture=None,
                roles=["user"],
                permissions=["read:users"],
            )
            mock_decode.return_value = mock_token

            with patch.object(
                UserModel, "upsert_from_payload", new_callable=AsyncMock
            ) as mock_upsert:
                async with app.test_client() as client:
                    response = await client.post(
                        "/api/users/login",
                        headers={"Authorization": "Bearer test-token"},
                        json={},
                    )

                    assert response.status_code == HTTPStatus.OK
                    data = await response.get_json()
                    assert data["status"] == "success"
                    assert data["user_id"] == "test-user-id"
                    assert "csrf_token" in data

                    # Check that session cookie was set
                    assert "Set-Cookie" in response.headers
                    assert "neuron_session=" in response.headers["Set-Cookie"]

                    mock_upsert.assert_called_once_with(mock_token)
