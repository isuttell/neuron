from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError
from quart import Quart

from neuron_server.api import app as neuron_app
from neuron_server.controllers.auth import TokenPayload
from neuron_server.controllers.personality_controller import (
    PersonalityGenerationResponse,
    ainvoke_generate_personality,
)
from neuron_server.llms.llm import LLM
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.personality_user_model import PersonalityUserModel
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.user_model import UserModel

# Constants
TEST_JWT_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"
PERSONALITY_USER_GET_CALL_COUNT = 2


@pytest.fixture
def test_context() -> dict:
    """Fixture that combines commonly used test objects to reduce function arguments."""
    return {
        "user": MagicMock(
            id="test_user_id",
            email="test@example.com",
            nickname="test_user",
            model_dump=lambda: {
                "id": "test_user_id",
                "email": "test@example.com",
                "nickname": "test_user",
            },
        ),
        "personality_user": MagicMock(
            id=uuid4(),
            personality_id=uuid4(),
            user_id="test_user_id",
            role="admin",
            model_dump=lambda: {
                "id": str(uuid4()),
                "personality_id": str(uuid4()),
                "user_id": "test_user_id",
                "role": "admin",
            },
        ),
    }


@pytest.fixture
def app() -> Quart:
    """Return the Quart app with patched test client and request context.

    The patching is done in conftest.py mock_quart_app fixture.
    """
    return neuron_app


@pytest.fixture
def mock_token() -> TokenPayload:
    return TokenPayload(
        user_id="test_user_id",
        roles=["user"],
        email="test@example.com",
        nickname="test_user",
        picture=None,
        permissions=[],
    )


@pytest.fixture
def mock_personality() -> MagicMock:
    personality = MagicMock()
    personality.id = uuid4()
    personality.name = "Test Personality"
    personality.description = "Test Description"
    personality.context = "Test Context"
    personality.memory = "Test Memory"
    personality.model_dump.return_value = {
        "id": str(personality.id),
        "name": personality.name,
        "description": personality.description,
        "context": personality.context,
        "memory": personality.memory,
    }
    return personality


@pytest.fixture
def mock_personality_user() -> MagicMock:
    personality_user = MagicMock()
    personality_user.id = uuid4()
    personality_user.personality_id = uuid4()
    personality_user.user_id = "test_user_id"
    personality_user.role = "admin"
    personality_user.model_dump.return_value = {
        "id": str(personality_user.id),
        "personality_id": str(personality_user.personality_id),
        "user_id": personality_user.user_id,
        "role": personality_user.role,
    }
    return personality_user


@pytest.fixture
def mock_user() -> MagicMock:
    user = MagicMock()
    user.id = "test_user_id"
    user.email = "test@example.com"
    user.nickname = "test_user"
    user.model_dump.return_value = {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
    }
    return user


@pytest.fixture
def mock_decode_token() -> AsyncMock:
    with patch("neuron_server.controllers.auth.decode_token") as mock:
        mock.return_value = TokenPayload(
            user_id="test_user_id",
            roles=["user"],
            email="test@example.com",
            nickname="test_user",
            picture=None,
            permissions=[],
        )
        yield mock


@pytest.mark.asyncio
async def test_get_personality_users(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_user: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting all users associated with a personality."""
    personality_id = mock_personality.id

    # Mock personality_user
    mock_personality_user = MagicMock()
    mock_personality_user.user_id = mock_user.id
    mock_personality_user.role = "admin"

    with (
        patch.object(
            PersonalityModel, "has_admin_access", new_callable=AsyncMock
        ) as mock_has_admin,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            PersonalityUserModel, "get_personality_users", new_callable=AsyncMock
        ) as mock_get_users,
        patch.object(
            UserModel, "get_all", new_callable=AsyncMock
        ) as mock_get_all_users,
    ):
        # Setup mocks
        mock_has_admin.return_value = True
        mock_get.return_value = mock_personality
        mock_get_users.return_value = [mock_personality_user]
        mock_get_all_users.return_value = [mock_user]

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users",
            method="GET",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.personality_controller import (
                get_personality_users,
            )

            result = await get_personality_users(personality_id)

            # Verify response
            assert "users" in result
            assert len(result["users"]) == 1
            assert result["users"][0]["id"] == mock_user.id
            assert result["users"][0]["role"] == "admin"

        # Verify mocks were called correctly
        mock_has_admin.assert_called_once_with(
            personality_id=personality_id, user_id=mock_token.user_id
        )
        mock_get.assert_called_once_with(personality_id=personality_id)
        mock_get_users.assert_called_once_with(personality_id=personality_id)
        mock_get_all_users.assert_called_once()


@pytest.mark.asyncio
async def test_get_personality_users_forbidden(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting personality users without admin access."""
    personality_id = mock_personality.id

    with patch.object(
        PersonalityModel, "has_admin_access", new_callable=AsyncMock
    ) as mock_has_admin:
        # Setup mock to return False (no admin access)
        mock_has_admin.return_value = False

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users",
            method="GET",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from werkzeug.exceptions import Forbidden

            from neuron_server.controllers.personality_controller import (
                get_personality_users,
            )

            with pytest.raises(Forbidden) as excinfo:
                await get_personality_users(personality_id)

            # Verify error message
            assert "permission" in str(excinfo.value).lower()

        # Verify mock was called
        mock_has_admin.assert_called_once_with(
            personality_id=personality_id, user_id=mock_token.user_id
        )


@pytest.mark.asyncio
async def test_get_personality_users_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting users for a non-existent personality."""
    personality_id = uuid4()

    with (
        patch.object(
            PersonalityModel, "has_admin_access", new_callable=AsyncMock
        ) as mock_has_admin,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
    ):
        # Setup mocks
        mock_has_admin.return_value = True
        mock_get.return_value = None  # Personality not found

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users",
            method="GET",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from werkzeug.exceptions import NotFound

            from neuron_server.controllers.personality_controller import (
                get_personality_users,
            )

            with pytest.raises(NotFound) as excinfo:
                await get_personality_users(personality_id)

            # Verify error message
            assert str(personality_id) in str(excinfo.value)

        # Verify mocks were called
        mock_has_admin.assert_called_once_with(
            personality_id=personality_id, user_id=mock_token.user_id
        )
        mock_get.assert_called_once_with(personality_id=personality_id)


@pytest.mark.asyncio
async def test_add_personality_user(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_user: MagicMock,
    mock_personality_user: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test adding a user to a personality."""
    personality_id = mock_personality.id
    new_user_id = "new_user_id"

    # Update mock_personality_user to match the new user
    mock_personality_user.user_id = new_user_id
    mock_personality_user.model_dump.return_value["user_id"] = new_user_id

    with (
        patch.object(
            PersonalityModel, "has_admin_access", new_callable=AsyncMock
        ) as mock_has_admin,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(UserModel, "get_by_ids", new_callable=AsyncMock) as mock_get_users,
        patch.object(
            PersonalityUserModel, "get", new_callable=AsyncMock
        ) as mock_get_pu,
        patch.object(
            PersonalityModel, "add_user", new_callable=AsyncMock
        ) as mock_add_user,
    ):
        # Setup mocks
        mock_has_admin.return_value = True
        mock_get.return_value = mock_personality
        mock_get_users.return_value = [mock_user]  # User exists
        # First check, then return after add
        mock_get_pu.side_effect = [None, mock_personality_user]
        mock_add_user.return_value = None

        # Create request data
        request_data = {"user_id": new_user_id, "role": "user"}

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users",
            method="POST",
            headers={
                "Authorization": TEST_JWT_TOKEN,
                "X-CSRF-Token": "test-csrf-token",
            },
            json=request_data,
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.personality_controller import (
                add_personality_user,
            )

            result = await add_personality_user(personality_id)

            # Verify response
            assert "personality_user" in result
            assert result["personality_user"]["user_id"] == new_user_id
            assert result["personality_user"]["role"] == "admin"

        # Verify mocks were called correctly
        mock_has_admin.assert_called_once_with(
            personality_id=personality_id, user_id=mock_token.user_id
        )
        mock_get.assert_called_once_with(personality_id=personality_id)
        mock_get_users.assert_called_once_with(user_ids=[new_user_id])
        mock_add_user.assert_called_once_with(
            personality_id=personality_id, user_id=new_user_id, role="user"
        )
        # Mock get called twice - once for checking existing, once after adding
        assert mock_get_pu.call_count == PERSONALITY_USER_GET_CALL_COUNT


@pytest.mark.asyncio
async def test_add_personality_user_already_exists(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_user: MagicMock,
    mock_personality_user: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test adding a user that already has access to the personality."""
    personality_id = mock_personality.id
    existing_user_id = mock_personality_user.user_id

    with (
        patch.object(
            PersonalityModel, "has_admin_access", new_callable=AsyncMock
        ) as mock_has_admin,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(UserModel, "get_by_ids", new_callable=AsyncMock) as mock_get_users,
        patch.object(
            PersonalityUserModel, "get", new_callable=AsyncMock
        ) as mock_get_pu,
    ):
        # Setup mocks
        mock_has_admin.return_value = True
        mock_get.return_value = mock_personality
        mock_get_users.return_value = [mock_user]
        mock_get_pu.return_value = mock_personality_user  # User already has access

        # Create request data
        request_data = {"user_id": existing_user_id, "role": "user"}

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users",
            method="POST",
            headers={
                "Authorization": TEST_JWT_TOKEN,
                "X-CSRF-Token": "test-csrf-token",
            },
            json=request_data,
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from werkzeug.exceptions import BadRequest

            from neuron_server.controllers.personality_controller import (
                add_personality_user,
            )

            with pytest.raises(BadRequest) as excinfo:
                await add_personality_user(personality_id)

            # Verify error message
            assert "already associated" in str(excinfo.value)


@pytest.mark.asyncio
async def test_update_personality_user(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_personality_user: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test updating a user's role for a personality."""
    personality_id = mock_personality.id
    user_id = mock_personality_user.user_id

    # Create updated personality user with new role
    updated_personality_user = MagicMock()
    updated_personality_user.id = mock_personality_user.id
    updated_personality_user.personality_id = personality_id
    updated_personality_user.user_id = user_id
    updated_personality_user.role = "user"  # Changed from admin
    updated_personality_user.model_dump.return_value = {
        "id": str(updated_personality_user.id),
        "personality_id": str(personality_id),
        "user_id": user_id,
        "role": "user",
    }

    with (
        patch.object(
            PersonalityModel, "has_admin_access", new_callable=AsyncMock
        ) as mock_has_admin,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            PersonalityUserModel, "get", new_callable=AsyncMock
        ) as mock_get_pu,
        patch.object(
            PersonalityUserModel, "update_role", new_callable=AsyncMock
        ) as mock_update_role,
    ):
        # Setup mocks
        mock_has_admin.return_value = True
        mock_get.return_value = mock_personality
        mock_get_pu.return_value = mock_personality_user  # User exists
        mock_update_role.return_value = updated_personality_user

        # Create request data
        request_data = {"user_id": user_id, "role": "user"}

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users/{user_id}",
            method="PUT",
            headers={
                "Authorization": TEST_JWT_TOKEN,
                "X-CSRF-Token": "test-csrf-token",
            },
            json=request_data,
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.personality_controller import (
                update_personality_user,
            )

            result = await update_personality_user(personality_id, user_id)

            # Verify response
            assert "personality_user" in result
            assert result["personality_user"]["role"] == "user"


@pytest.mark.asyncio
async def test_update_personality_user_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test updating a user that doesn't have access to the personality."""
    personality_id = mock_personality.id
    user_id = "non_existent_user"

    with (
        patch.object(
            PersonalityModel, "has_admin_access", new_callable=AsyncMock
        ) as mock_has_admin,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            PersonalityUserModel, "get", new_callable=AsyncMock
        ) as mock_get_pu,
    ):
        # Setup mocks
        mock_has_admin.return_value = True
        mock_get.return_value = mock_personality
        mock_get_pu.return_value = None  # User not found

        # Create request data
        request_data = {"user_id": user_id, "role": "user"}

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users/{user_id}",
            method="PUT",
            headers={
                "Authorization": TEST_JWT_TOKEN,
                "X-CSRF-Token": "test-csrf-token",
            },
            json=request_data,
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from werkzeug.exceptions import NotFound

            from neuron_server.controllers.personality_controller import (
                update_personality_user,
            )

            with pytest.raises(NotFound) as excinfo:
                await update_personality_user(personality_id, user_id)

            # Verify error message
            assert user_id in str(excinfo.value)


@pytest.mark.asyncio
async def test_remove_personality_user(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_personality_user: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test removing a user from a personality."""
    personality_id = mock_personality.id
    user_id = "user_to_remove"

    # Create multiple users including admins
    admin1 = MagicMock()
    admin1.user_id = mock_token.user_id
    admin1.role = "admin"

    admin2 = MagicMock()
    admin2.user_id = "another_admin"
    admin2.role = "admin"

    user_to_remove = MagicMock()
    user_to_remove.user_id = user_id
    user_to_remove.role = "user"

    with (
        patch.object(
            PersonalityModel, "has_admin_access", new_callable=AsyncMock
        ) as mock_has_admin,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            PersonalityUserModel, "get_personality_users", new_callable=AsyncMock
        ) as mock_get_users,
        patch.object(
            PersonalityModel, "remove_user", new_callable=AsyncMock
        ) as mock_remove_user,
    ):
        # Setup mocks
        mock_has_admin.return_value = True
        mock_get.return_value = mock_personality
        mock_get_users.return_value = [admin1, admin2, user_to_remove]  # Multiple users
        mock_remove_user.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users/{user_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.personality_controller import (
                remove_personality_user,
            )

            result = await remove_personality_user(personality_id, user_id)

            # Verify response is empty (204 No Content)
            assert result.status_code == HTTPStatus.NO_CONTENT

        # Verify mocks were called correctly
        mock_has_admin.assert_called_once_with(
            personality_id=personality_id, user_id=mock_token.user_id
        )
        mock_get.assert_called_once_with(personality_id=personality_id)
        mock_get_users.assert_called_once_with(personality_id=personality_id)
        mock_remove_user.assert_called_once_with(
            personality_id=personality_id, user_id=user_id
        )


@pytest.mark.asyncio
async def test_remove_last_admin(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test removing the last admin from a personality."""
    personality_id = mock_personality.id
    user_id = mock_token.user_id

    # Create only one admin user
    admin = MagicMock()
    admin.user_id = user_id
    admin.role = "admin"

    with (
        patch.object(
            PersonalityModel, "has_admin_access", new_callable=AsyncMock
        ) as mock_has_admin,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            PersonalityUserModel, "get_personality_users", new_callable=AsyncMock
        ) as mock_get_users,
    ):
        # Setup mocks
        mock_has_admin.return_value = True
        mock_get.return_value = mock_personality
        mock_get_users.return_value = [admin]  # Only one admin user

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/users/{user_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from werkzeug.exceptions import BadRequest

            from neuron_server.controllers.personality_controller import (
                remove_personality_user,
            )

            with pytest.raises(BadRequest) as excinfo:
                await remove_personality_user(personality_id, user_id)

            # Verify error message
            assert "last admin" in str(excinfo.value)

        # Verify mocks were called correctly
        mock_has_admin.assert_called_once_with(
            personality_id=personality_id, user_id=mock_token.user_id
        )
        mock_get.assert_called_once_with(personality_id=personality_id)
        mock_get_users.assert_called_once_with(personality_id=personality_id)


@pytest.mark.asyncio
async def test_set_default_personality_success(
    app: Quart,
    mock_personality: MagicMock,
) -> None:
    """Test setting a personality as default with admin access."""
    personality_id = mock_personality.id

    # Create admin token
    admin_token = TokenPayload(
        user_id="admin_user_id",
        roles=["user", "admin"],
        email="admin@example.com",
        nickname="admin_user",
        picture=None,
        permissions=[],
    )

    # Update mock personality to include default field
    mock_personality.default = True
    mock_personality.model_dump.return_value["default"] = True

    with (
        patch("neuron_server.controllers.auth.decode_token") as mock_decode_token,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(PersonalityModel, "set", new_callable=AsyncMock) as mock_set,
    ):
        # Setup mocks
        mock_decode_token.return_value = admin_token
        mock_get.return_value = mock_personality
        mock_set.return_value = mock_personality

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/set-default",
            method="POST",
            headers={
                "Authorization": TEST_JWT_TOKEN,
                "X-CSRF-Token": "test-csrf-token",
            },
        ):
            # Set token on request
            app.request_class.token = admin_token

            # Call the endpoint function directly
            from neuron_server.controllers.personality_controller import (
                set_default_personality,
            )

            result = await set_default_personality(personality_id)

            # Verify response
            assert "personality" in result
            assert result["personality"]["id"] == str(personality_id)
            assert result["personality"]["default"] is True

        # Verify mocks were called
        mock_get.assert_called_once_with(personality_id=personality_id)
        mock_set.assert_called_once_with(
            personality_id=personality_id, key="default", value=True
        )


@pytest.mark.asyncio
async def test_set_default_personality_forbidden_non_admin(
    app: Quart,
    mock_token: TokenPayload,
    mock_personality: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test setting a personality as default without admin access."""
    personality_id = mock_personality.id

    # Create request context
    async with app.test_request_context(
        f"/api/personality/{personality_id}/set-default",
        method="POST",
        headers={
            "Authorization": TEST_JWT_TOKEN,
            "X-CSRF-Token": "test-csrf-token",
        },
    ):
        # Set non-admin token on request
        app.request_class.token = mock_token

        # Call the endpoint function directly
        from werkzeug.exceptions import Forbidden

        from neuron_server.controllers.personality_controller import (
            set_default_personality,
        )

        with pytest.raises(Forbidden) as excinfo:
            await set_default_personality(personality_id)

        # Verify error message
        assert "Admin access required" in str(excinfo.value)


@pytest.mark.asyncio
async def test_set_default_personality_not_found(
    app: Quart,
) -> None:
    """Test setting a non-existent personality as default."""
    personality_id = uuid4()

    # Create admin token
    admin_token = TokenPayload(
        user_id="admin_user_id",
        roles=["user", "admin"],
        email="admin@example.com",
        nickname="admin_user",
        picture=None,
        permissions=[],
    )

    with (
        patch("neuron_server.controllers.auth.decode_token") as mock_decode_token,
        patch.object(PersonalityModel, "get", new_callable=AsyncMock) as mock_get,
    ):
        # Setup mocks
        mock_decode_token.return_value = admin_token
        mock_get.return_value = None  # Personality not found

        # Create request context
        async with app.test_request_context(
            f"/api/personality/{personality_id}/set-default",
            method="POST",
            headers={
                "Authorization": TEST_JWT_TOKEN,
                "X-CSRF-Token": "test-csrf-token",
            },
        ):
            # Set token on request
            app.request_class.token = admin_token

            # Call the endpoint function directly
            from werkzeug.exceptions import NotFound

            from neuron_server.controllers.personality_controller import (
                set_default_personality,
            )

            with pytest.raises(NotFound) as excinfo:
                await set_default_personality(personality_id)

            # Verify error message
            assert f"Personality with id {personality_id} not found" in str(
                excinfo.value
            )

        # Verify mock was called
        mock_get.assert_called_once_with(personality_id=personality_id)


# Personality Generation Tests


@pytest.fixture
def mock_llm() -> MagicMock:
    """Mock LLM instance for testing."""
    llm = MagicMock(spec=LLM)
    llm.model = MagicMock()
    return llm


@pytest.fixture
def sample_personality_response() -> PersonalityGenerationResponse:
    """Sample personality generation response for testing."""
    return PersonalityGenerationResponse(
        name="Test Expert",
        description="A knowledgeable expert in testing and quality assurance",
        context=(
            "You are Test Expert, a seasoned professional in software testing. "
            "You provide detailed, practical advice on testing strategies, tools, "
            "and best practices. Always be thorough and methodical in your responses."
        ),
        memory="",
    )


class TestPersonalityGenerationResponse:
    """Test cases for PersonalityGenerationResponse Pydantic model."""

    def test_valid_personality_response(
        self, sample_personality_response: PersonalityGenerationResponse
    ) -> None:
        """Test creating a valid PersonalityGenerationResponse."""
        assert sample_personality_response.name == "Test Expert"
        assert "expert in testing" in sample_personality_response.description
        assert "You are Test Expert" in sample_personality_response.context
        assert sample_personality_response.memory == ""

    def test_personality_response_missing_required_field(self) -> None:
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError) as excinfo:
            PersonalityGenerationResponse(
                name="Test Expert",
                description="A testing expert",
                # missing context and memory
            )

        error_details = excinfo.value.errors()
        missing_fields = [
            error["loc"][0] for error in error_details if error["type"] == "missing"
        ]
        assert "context" in missing_fields
        assert "memory" in missing_fields

    def test_personality_response_empty_strings(self) -> None:
        """Test that empty strings are valid for all fields."""
        response = PersonalityGenerationResponse(
            name="",
            description="",
            context="",
            memory="",
        )
        assert response.name == ""
        assert response.description == ""
        assert response.context == ""
        assert response.memory == ""

    def test_personality_response_serialization(
        self, sample_personality_response: PersonalityGenerationResponse
    ) -> None:
        """Test that PersonalityGenerationResponse serializes correctly."""
        data = sample_personality_response.model_dump()
        assert data["name"] == "Test Expert"
        expected_desc = "A knowledgeable expert in testing and quality assurance"
        assert data["description"] == expected_desc
        assert "You are Test Expert" in data["context"]
        assert data["memory"] == ""


class TestAinvokeGeneratePersonality:
    """Test cases for ainvoke_generate_personality function."""

    @pytest.mark.asyncio
    async def test_successful_personality_generation(
        self,
        mock_llm: MagicMock,
        sample_personality_response: PersonalityGenerationResponse,
    ) -> None:
        """Test successful personality generation with structured output."""
        # Setup mock chain
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(return_value=sample_personality_response)

        # Mock the chain creation
        with patch(
            "neuron_server.controllers.personality_controller.personality_generation_prompt"
        ) as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_llm.model.with_structured_output.return_value = mock_chain

            # Call the function
            result = await ainvoke_generate_personality(
                mock_llm, "Create a testing expert personality"
            )

            # Verify result
            assert isinstance(result, PersonalityGenerationResponse)
            assert result.name == "Test Expert"
            expected_desc = "A knowledgeable expert in testing and quality assurance"
            assert result.description == expected_desc
            assert "You are Test Expert" in result.context
            assert result.memory == ""

            # Verify mocks were called
            mock_llm.model.with_structured_output.assert_called_once_with(
                PersonalityGenerationResponse
            )
            mock_chain.ainvoke.assert_called_once_with(
                {"prompt": "Create a testing expert personality"}
            )

    @pytest.mark.asyncio
    async def test_personality_generation_with_validation_error(
        self, mock_llm: MagicMock
    ) -> None:
        """Test that Pydantic validation errors are properly raised."""
        # Setup mock chain to raise ValidationError
        mock_chain = MagicMock()
        mock_chain.ainvoke = AsyncMock(
            side_effect=ValidationError.from_exception_data(
                "PersonalityGenerationResponse",
                [{"type": "missing", "loc": ("name",), "msg": "Field required"}],
            )
        )

        with patch(
            "neuron_server.controllers.personality_controller.personality_generation_prompt"
        ) as mock_prompt:
            mock_prompt.__or__ = MagicMock(return_value=mock_chain)
            mock_llm.model.with_structured_output.return_value = mock_chain

            # Call the function and expect ValidationError
            with pytest.raises(ValidationError) as excinfo:
                await ainvoke_generate_personality(mock_llm, "Invalid prompt")

            # Verify error details
            error_details = excinfo.value.errors()
            assert len(error_details) == 1
            assert error_details[0]["type"] == "missing"
            assert error_details[0]["loc"] == ("name",)


class TestGeneratePersonalityEndpoint:
    """Test cases for the /api/personality/generate endpoint."""

    @pytest.mark.asyncio
    async def test_generate_personality_success(
        self,
        app: Quart,
        mock_token: TokenPayload,
        mock_decode_token: AsyncMock,
        sample_personality_response: PersonalityGenerationResponse,
    ) -> None:
        """Test successful personality generation endpoint."""
        # Mock the created personality
        mock_created_personality = MagicMock()
        mock_created_personality.id = uuid4()
        mock_created_personality.model_dump.return_value = {
            "id": str(mock_created_personality.id),
            "name": sample_personality_response.name,
            "description": sample_personality_response.description,
            "context": sample_personality_response.context,
            "memory": sample_personality_response.memory,
        }

        with (
            patch.object(
                ProviderModelModel, "get_active_llm", new_callable=AsyncMock
            ) as mock_get_llm,
            patch(
                "neuron_server.controllers.personality_controller.ainvoke_generate_personality",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch.object(
                PersonalityModel, "create", new_callable=AsyncMock
            ) as mock_create,
        ):
            # Setup mocks
            mock_llm = MagicMock(spec=LLM)
            mock_get_llm.return_value = mock_llm
            mock_generate.return_value = sample_personality_response
            mock_create.return_value = mock_created_personality

            # Create request data
            request_data = {
                "prompt": "Create a testing expert personality",
                "tool_set": None,
            }

            # Create request context
            async with app.test_request_context(
                "/api/personality/generate",
                method="POST",
                headers={
                    "Authorization": TEST_JWT_TOKEN,
                    "X-CSRF-Token": "test-csrf-token",
                },
                json=request_data,
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly
                from neuron_server.controllers.personality_controller import (
                    generate_personality,
                )

                result = await generate_personality()

                # Verify response
                assert "personality" in result
                assert result["personality"]["name"] == sample_personality_response.name
                assert (
                    result["personality"]["description"]
                    == sample_personality_response.description
                )

            # Verify mocks were called correctly
            mock_get_llm.assert_called_once()
            mock_generate.assert_called_once_with(
                llm=mock_llm, prompt="Create a testing expert personality"
            )
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_personality_with_tool_set(
        self,
        app: Quart,
        mock_decode_token: AsyncMock,
        sample_personality_response: PersonalityGenerationResponse,
    ) -> None:
        """Test personality generation with tool set specified."""
        # Create token with tool permission
        mock_token = TokenPayload(
            user_id="test_user_id",
            roles=["user", "tool-search"],
            email="test@example.com",
            nickname="test_user",
            picture=None,
            permissions=[],
        )

        # Mock the created personality
        mock_created_personality = MagicMock()
        mock_created_personality.id = uuid4()
        mock_created_personality.model_dump.return_value = {
            "id": str(mock_created_personality.id),
            "name": sample_personality_response.name,
            "description": sample_personality_response.description,
            "context": sample_personality_response.context,
            "memory": sample_personality_response.memory,
            "tool_set": "search",
        }

        with (
            patch.object(
                ProviderModelModel, "get_active_llm", new_callable=AsyncMock
            ) as mock_get_llm,
            patch(
                "neuron_server.controllers.personality_controller.ainvoke_generate_personality",
                new_callable=AsyncMock,
            ) as mock_generate,
            patch.object(
                PersonalityModel, "create", new_callable=AsyncMock
            ) as mock_create,
            patch(
                "neuron_server.controllers.personality_controller.validate_tool_set_permissions"
            ) as mock_validate_tools,
        ):
            # Setup mocks
            mock_llm = MagicMock(spec=LLM)
            mock_get_llm.return_value = mock_llm
            mock_generate.return_value = sample_personality_response
            mock_create.return_value = mock_created_personality
            mock_validate_tools.return_value = None  # No validation errors
            mock_decode_token.return_value = mock_token

            # Create request data
            request_data = {
                "prompt": "Create a search expert personality",
                "tool_set": "search",
            }

            # Create request context
            async with app.test_request_context(
                "/api/personality/generate",
                method="POST",
                headers={
                    "Authorization": TEST_JWT_TOKEN,
                    "X-CSRF-Token": "test-csrf-token",
                },
                json=request_data,
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly
                from neuron_server.controllers.personality_controller import (
                    generate_personality,
                )

                result = await generate_personality()

                # Verify response
                assert "personality" in result
                assert result["personality"]["tool_set"] == "search"

            # Verify tool validation was called
            mock_validate_tools.assert_called_once_with(
                "search", ["user", "tool-search"]
            )

    @pytest.mark.asyncio
    async def test_generate_personality_validation_error(
        self,
        app: Quart,
        mock_token: TokenPayload,
        mock_decode_token: AsyncMock,
    ) -> None:
        """Test personality generation endpoint with validation error."""
        with (
            patch.object(
                ProviderModelModel, "get_active_llm", new_callable=AsyncMock
            ) as mock_get_llm,
            patch(
                "neuron_server.controllers.personality_controller.ainvoke_generate_personality",
                new_callable=AsyncMock,
            ) as mock_generate,
        ):
            # Setup mocks
            mock_llm = MagicMock(spec=LLM)
            mock_get_llm.return_value = mock_llm

            # Mock ValidationError from Pydantic
            mock_generate.side_effect = ValidationError.from_exception_data(
                "PersonalityGenerationResponse",
                [{"type": "missing", "loc": ("name",), "msg": "Field required"}],
            )

            # Create request data
            request_data = {
                "prompt": "Invalid prompt that causes validation error",
                "tool_set": None,
            }

            # Create request context
            async with app.test_request_context(
                "/api/personality/generate",
                method="POST",
                headers={
                    "Authorization": TEST_JWT_TOKEN,
                    "X-CSRF-Token": "test-csrf-token",
                },
                json=request_data,
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly
                from neuron_server.controllers.personality_controller import (
                    generate_personality,
                )

                # Expect ValidationError to be raised (not caught by endpoint)
                with pytest.raises(ValidationError):
                    await generate_personality()
