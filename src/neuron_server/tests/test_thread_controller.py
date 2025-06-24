from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from quart import Quart
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from neuron_server.api import app as neuron_app
from neuron_server.controllers.auth import TokenPayload
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.thread_model import ThreadModel
from neuron_server.models.thread_user_model import ThreadUserModel
from neuron_server.models.user_model import UserModel

# Constants
TEST_JWT_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"


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
        "thread_user": MagicMock(
            id=uuid4(),
            thread_id=uuid4(),
            user_id="test_user_id",
            role="admin",
            model_dump=lambda: {
                "id": str(uuid4()),
                "thread_id": str(uuid4()),
                "user_id": "test_user_id",
                "role": "admin",
            },
        ),
    }


@pytest.fixture
def app() -> Quart:
    """Return the Quart app with patched test client and request context."""
    return neuron_app


@pytest.fixture
def mock_token() -> TokenPayload:
    """Create a mock token for testing."""
    return TokenPayload(
        user_id="test_user_id",
        roles=[],
        email="test@example.com",
        nickname="test_user",
        picture=None,
        permissions=[],
    )


@pytest.fixture
def mock_thread() -> MagicMock:
    """Create a mock thread for testing."""
    thread = MagicMock()
    thread.id = uuid4()
    thread.user_id = "test_user_id"
    thread.name = "Test Thread"
    thread.context = "Test Context"
    thread.memory = "Test Memory"
    thread.status = "idle"
    thread.personality_id = uuid4()
    thread.message_count = 0
    thread.save = AsyncMock()
    thread.model_dump.return_value = {
        "id": str(thread.id),
        "user_id": thread.user_id,
        "name": thread.name,
        "context": thread.context,
        "memory": thread.memory,
        "status": thread.status,
        "personality_id": str(thread.personality_id),
        "message_count": thread.message_count,
    }
    return thread


@pytest.fixture
def mock_personality() -> MagicMock:
    """Create a mock personality for testing."""
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
def mock_thread_user() -> MagicMock:
    """Create a mock thread user for testing."""
    thread_user = MagicMock()
    thread_user.id = uuid4()
    thread_user.thread_id = uuid4()
    thread_user.user_id = "test_user_id"
    thread_user.role = "admin"
    thread_user.model_dump.return_value = {
        "id": str(thread_user.id),
        "thread_id": str(thread_user.thread_id),
        "user_id": thread_user.user_id,
        "role": thread_user.role,
    }
    return thread_user


@pytest.fixture
def mock_user() -> MagicMock:
    """Create a mock user for testing."""
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
def mock_redis() -> AsyncMock:
    """Mock Redis to avoid connection errors during tests."""
    # Create a comprehensive mock Redis client
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.setex.return_value = True
    mock_redis.delete.return_value = 1
    mock_redis.exists.return_value = 0
    mock_redis.close.return_value = None
    mock_redis.__aenter__.return_value = mock_redis
    mock_redis.__aexit__.return_value = None

    # Mock pipeline operations
    mock_pipeline = AsyncMock()
    mock_pipeline.execute.return_value = []
    mock_redis.pipeline.return_value = mock_pipeline

    # Mock pubsub operations
    mock_pubsub = AsyncMock()
    mock_pubsub.subscribe.return_value = None
    mock_pubsub.get_message.return_value = None
    mock_pubsub.__aiter__.return_value = mock_pubsub
    mock_pubsub.__anext__.side_effect = StopAsyncIteration
    mock_redis.pubsub.return_value = mock_pubsub

    # Create shorter path names for patching
    cache_path = "neuron_server.cache"
    auth_path = "neuron_server.controllers.auth"
    with (
        patch(f"{cache_path}.get_redis_client", return_value=mock_redis),
        patch(f"{cache_path}.cache_response", lambda func=None, ttl=None: lambda f: f),
        patch(f"{auth_path}.get_jwks", new_callable=AsyncMock) as mock_jwks,
    ):
        mock_jwks.return_value = {"keys": []}
        yield mock_redis


@pytest.fixture
def mock_decode_token(mock_redis: AsyncMock) -> AsyncMock:
    """Mock the decode_token function."""
    # Patch the decode_token function directly
    with patch("neuron_server.controllers.auth.decode_token") as mock:
        mock.return_value = TokenPayload(
            user_id="test_user_id",
            roles=[],
            email="test@example.com",
            nickname="test_user",
            picture=None,
            permissions=[],
        )
        yield mock


@pytest.mark.asyncio
async def test_get_thread(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test getting a thread by ID."""
    thread_id = mock_thread.id

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get,
    ):
        # Setup mocks
        mock_get.return_value = mock_thread

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import get_thread

            result = await get_thread(thread_id)

            # Verify response
            assert "threads" in result
            assert len(result["threads"]) == 1
            assert result["threads"][0]["id"] == str(mock_thread.id)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(thread_id=thread_id)


@pytest.mark.asyncio
async def test_get_thread_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test getting a thread that doesn't exist."""
    thread_id = uuid4()

    with patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get:
        # Setup mocks
        mock_get.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import get_thread

            with pytest.raises(NotFound) as excinfo:
                await get_thread(thread_id)

            # Verify error message
            assert "Thread not found" in str(excinfo.value)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(thread_id=thread_id)


@pytest.mark.asyncio
async def test_get_thread_access_denied(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test getting a thread the user doesn't have access to."""
    thread_id = mock_thread.id
    # Change thread owner to be different from token user
    mock_thread.user_id = "different_user_id"

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_thread_user_get,
    ):
        # Setup mocks
        mock_get.return_value = mock_thread
        mock_thread_user_get.return_value = None  # User doesn't have access

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import get_thread

            with pytest.raises(Forbidden) as excinfo:
                await get_thread(thread_id)

            # Verify error message
            assert "don't have access" in str(excinfo.value)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(thread_id=thread_id)
        mock_thread_user_get.assert_called_once_with(
            thread_id=thread_id, user_id=mock_token.user_id
        )


@pytest.mark.asyncio
async def test_get_threads_for_personality(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test getting threads for a personality."""
    personality_id = mock_thread.personality_id

    with (
        patch.object(ThreadModel, "list", new_callable=AsyncMock) as mock_list,
        patch.object(
            ThreadUserModel, "get_user_threads", new_callable=AsyncMock
        ) as mock_get_user_threads,
    ):
        # Setup mocks
        mock_list.return_value = [mock_thread]
        mock_get_user_threads.return_value = []  # No shared threads

        # Create request context
        async with app.test_request_context(
            f"/api/thread/personality/{personality_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import get_threads

            result = await get_threads(personality_id)

            # Verify response
            assert "threads" in result
            assert len(result["threads"]) == 1
            assert result["threads"][0]["id"] == str(mock_thread.id)

        # Verify mocks were called correctly
        mock_list.assert_called_once_with(
            personality_id=personality_id, user_id=mock_token.user_id
        )
        mock_get_user_threads.assert_called_once_with(user_id=mock_token.user_id)




@pytest.mark.asyncio
async def test_create_thread(thread_test_context: dict) -> None:
    """Test creating a new thread."""
    app = thread_test_context["app"]
    mock_token = thread_test_context["mock_token"]
    mock_thread = thread_test_context["mock_thread"]

    # Create a mock personality for this test
    mock_personality = MagicMock()
    mock_personality.id = uuid4()
    mock_personality.name = "Test Personality"
    mock_personality.model_dump.return_value = {
        "id": str(mock_personality.id),
        "name": mock_personality.name,
    }

    personality_id = mock_personality.id

    # Let's use a simpler approach by mocking directly at the controller level
    with (
        patch.object(
            PersonalityModel, "get", new_callable=AsyncMock
        ) as mock_get_personality,
        patch.object(
            ThreadModel, "create", new_callable=AsyncMock
        ) as mock_create_thread,
        patch.object(
            ThreadUserModel, "create", new_callable=AsyncMock
        ) as mock_create_thread_user,
        patch("asyncio.create_task") as mock_create_task,
    ):
        # Setup mocks
        mock_get_personality.return_value = mock_personality
        mock_create_thread.return_value = mock_thread
        mock_create_thread_user.return_value = MagicMock()

        # Create request context with form data
        form_data = {
            "personality_id": str(personality_id),
            "name": "Test Thread",
            "context": "Test Context",
            "memory": "Test Memory",
            "greeting": "false",
        }

        async with app.test_request_context(
            "/api/thread/",
            method="POST",
            form=form_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly with our own mocks
            from neuron_server.controllers.thread_controller import post_create_thread

            # Mock at the module level, not the property level
            process_path = "neuron_server.controllers.thread_controller"
            msg_path = f"{process_path}.process_message_request"
            with patch(
                msg_path, new_callable=AsyncMock, return_value="Test prompt"
            ) as mock_process:
                result = await post_create_thread()

                # Verify response
                assert "thread" in result
                assert result["thread"]["id"] == str(mock_thread.id)

                # Verify mocks were called correctly
                mock_get_personality.assert_called_once_with(
                    personality_id=personality_id
                )
                mock_create_thread.assert_called_once()
                mock_create_thread_user.assert_called_once()
                # In greeting=false mode, process_message_request should be called
                mock_process.assert_called_once()
                mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_create_thread_missing_personality(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test creating a thread without a personality ID."""
    # Mock the agent.astream to prevent coroutine warnings
    with patch("neuron_server.llms.agent.astream") as mock_astream:
        mock_astream.return_value = None

        form_data = {
            # Missing personality_id
            "name": "Test Thread",
        }

        async with app.test_request_context(
            "/api/thread/",
            method="POST",
            form=form_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import post_create_thread

            with pytest.raises(BadRequest) as excinfo:
                await post_create_thread()

            # Verify error message
            assert "personality_id is required" in str(excinfo.value)


@pytest.mark.asyncio
async def test_create_thread_personality_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test creating a thread with a non-existent personality."""
    personality_id = uuid4()

    # Mock the agent.astream to prevent coroutine warnings
    with patch("neuron_server.llms.agent.astream") as mock_astream:
        with patch.object(
            PersonalityModel, "get", new_callable=AsyncMock
        ) as mock_get_personality:
            # Setup mocks
            mock_get_personality.return_value = None
            mock_astream.return_value = None

            # Create request context with form data
            form_data = {
                "personality_id": str(personality_id),
                "name": "Test Thread",
            }

            async with app.test_request_context(
                "/api/thread/",
                method="POST",
                form=form_data,
                headers={"Authorization": TEST_JWT_TOKEN},
            ):
                # Set token on request
                app.request_class.token = mock_token

                # Call the endpoint function directly
                from neuron_server.controllers.thread_controller import (
                    post_create_thread,
                )

                with pytest.raises(BadRequest) as excinfo:
                    await post_create_thread()

                # Verify error message
                assert "Personality not found" in str(excinfo.value)

        # Verify mocks were called correctly
        mock_get_personality.assert_called_once_with(personality_id=personality_id)


@pytest.mark.asyncio
async def test_delete_thread(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test deleting a thread."""
    thread_id = mock_thread.id

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(ThreadModel, "delete", new_callable=AsyncMock) as mock_delete,
    ):
        # Setup mocks
        mock_get.return_value = mock_thread

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import delete_thread

            response = await delete_thread(thread_id)

            # Verify response
            assert response.status_code == HTTPStatus.NO_CONTENT

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(thread_id=thread_id)
        mock_delete.assert_called_once_with(thread_id=thread_id)


@pytest.mark.asyncio
async def test_delete_thread_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test deleting a thread that doesn't exist."""
    thread_id = uuid4()

    with patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get:
        # Setup mocks
        mock_get.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import delete_thread

            with pytest.raises(NotFound) as excinfo:
                await delete_thread(thread_id)

            # Verify error message
            assert "Thread not found" in str(excinfo.value)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(thread_id=thread_id)


@pytest.mark.asyncio
async def test_delete_thread_not_owner(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test deleting a thread the user doesn't own."""
    thread_id = mock_thread.id
    # Change thread owner to be different from token user
    mock_thread.user_id = "different_user_id"

    with patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get:
        # Setup mocks
        mock_get.return_value = mock_thread

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import delete_thread

            with pytest.raises(Forbidden) as excinfo:
                await delete_thread(thread_id)

            # Verify error message
            assert "Only the thread owner" in str(excinfo.value)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(thread_id=thread_id)


@pytest.mark.asyncio
async def test_update_thread(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test updating a thread."""
    thread_id = mock_thread.id
    update_data = {
        "name": "Updated Thread",
        "context": "Updated Context",
        "memory": "Updated Memory",
        "status": "active",
    }

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_thread_user_get,
        patch.object(ThreadModel, "update", new_callable=AsyncMock) as mock_update,
    ):
        # Setup mocks
        mock_get.return_value = mock_thread
        mock_thread_user_get.return_value = None  # Not relevant for this test
        mock_update.return_value = mock_thread

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}",
            method="PUT",
            json=update_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import update_thread

            result = await update_thread(thread_id)

            # Verify response
            assert "threads" in result
            assert len(result["threads"]) == 1
            assert result["threads"][0]["id"] == str(mock_thread.id)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(thread_id=thread_id)
        mock_update.assert_called_once()


@pytest.mark.asyncio
async def test_update_thread_not_owner(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test updating a thread the user doesn't own."""
    thread_id = mock_thread.id
    # Change thread owner to be different from token user
    mock_thread.user_id = "different_user_id"
    update_data = {
        "name": "Updated Thread",
        "context": "Updated Context",
        "memory": "Updated Memory",
        "status": "active",
    }

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_thread_user_get,
    ):
        # Setup mocks
        mock_get.return_value = mock_thread
        mock_thread_user_get.return_value = None  # Not a thread user

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}",
            method="PUT",
            json=update_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import update_thread

            with pytest.raises(Forbidden) as excinfo:
                await update_thread(thread_id)

            # Verify error message
            assert "You don't have access to this thread" in str(excinfo.value)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(thread_id=thread_id)
        mock_thread_user_get.assert_called_once_with(
            thread_id=thread_id, user_id=mock_token.user_id
        )


# Create a simplified fixture that avoids too many arguments issue
# by bundling the necessary context for thread user tests
@pytest.fixture
def thread_test_context(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_redis: AsyncMock,
    mock_decode_token: AsyncMock,
) -> dict:
    """Fixture that combines common test objects to reduce function arguments."""
    # Create additional mocks needed for tests
    thread_user = MagicMock()
    thread_user.id = uuid4()
    thread_user.thread_id = mock_thread.id
    thread_user.user_id = "test_user_id"
    thread_user.role = "admin"
    thread_user.model_dump.return_value = {
        "id": str(thread_user.id),
        "thread_id": str(thread_user.thread_id),
        "user_id": thread_user.user_id,
        "role": thread_user.role,
    }

    user = MagicMock()
    user.id = "test_user_id"
    user.email = "test@example.com"
    user.nickname = "test_user"
    user.model_dump.return_value = {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
    }

    # Ensure the auth mocking is setup properly for Redis-free tests
    cache_path = "neuron_server.cache"
    auth_path = "neuron_server.controllers.auth"
    with (
        patch(f"{auth_path}.get_jwks", new_callable=AsyncMock) as mock_jwks,
        patch(f"{cache_path}.get_redis_client", return_value=mock_redis),
    ):
        mock_jwks.return_value = {"keys": []}

        return {
            "app": app,
            "mock_token": mock_token,
            "mock_thread": mock_thread,
            "mock_thread_user": thread_user,
            "mock_user": user,
        }


@pytest.mark.asyncio
async def test_get_thread_users(thread_test_context: dict) -> None:
    """Test getting users associated with a thread."""
    app = thread_test_context["app"]
    mock_token = thread_test_context["mock_token"]
    mock_thread = thread_test_context["mock_thread"]
    mock_thread_user = thread_test_context["mock_thread_user"]
    mock_user = thread_test_context["mock_user"]

    thread_id = mock_thread.id

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get_thread,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_get_thread_user,
        patch.object(
            ThreadUserModel, "get_thread_users", new_callable=AsyncMock
        ) as mock_get_thread_users,
        patch.object(
            UserModel, "get_by_ids", new_callable=AsyncMock
        ) as mock_get_by_ids,
    ):
        # Setup mocks
        mock_get_thread.return_value = mock_thread
        mock_get_thread_user.return_value = mock_thread_user
        mock_get_thread_users.return_value = [mock_thread_user]
        mock_get_by_ids.return_value = [mock_user]

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}/users",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import get_thread_users

            result = await get_thread_users(thread_id)

            # Verify response
            assert "users" in result
            assert len(result["users"]) == 1
            assert result["users"][0]["id"] == mock_user.id
            assert "role" in result["users"][0]

        # Verify mocks were called correctly
        assert mock_get_thread.call_count >= 1  # Called multiple times
        mock_get_thread_users.assert_called_once_with(thread_id=thread_id)
        mock_get_by_ids.assert_called_with(user_ids=[mock_thread_user.user_id])


@pytest.mark.asyncio
async def test_add_thread_user(thread_test_context: dict) -> None:
    """Test adding a user to a thread."""
    app = thread_test_context["app"]
    mock_token = thread_test_context["mock_token"]
    mock_thread = thread_test_context["mock_thread"]
    mock_user = thread_test_context["mock_user"]
    mock_thread_user = thread_test_context["mock_thread_user"]

    thread_id = mock_thread.id
    user_id = "new_user_id"

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get_thread,
        patch.object(
            UserModel, "get_by_ids", new_callable=AsyncMock
        ) as mock_get_by_ids,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_get_thread_user,
        patch.object(
            ThreadUserModel, "create", new_callable=AsyncMock
        ) as mock_create_thread_user,
    ):
        # Setup mocks
        mock_get_thread.return_value = mock_thread
        mock_get_by_ids.return_value = [mock_user]
        # First call returns None (user not found), second call returns mock
        mock_get_thread_user.side_effect = [None]
        mock_create_thread_user.return_value = mock_thread_user

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}/users",
            method="POST",
            json={"user_id": user_id, "role": "user"},
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import add_thread_user

            result = await add_thread_user(thread_id)

            # Verify response
            assert "thread_user" in result
            assert result["thread_user"] == mock_thread_user.model_dump()

        # Verify mocks were called correctly
        assert mock_get_thread.call_count >= 1  # Called multiple times
        mock_get_by_ids.assert_called_once_with(user_ids=[user_id])
        mock_create_thread_user.assert_called_once()


@pytest.mark.asyncio
async def test_add_thread_user_already_exists(thread_test_context: dict) -> None:
    """Test adding a user that's already in the thread."""
    app = thread_test_context["app"]
    mock_token = thread_test_context["mock_token"]
    mock_thread = thread_test_context["mock_thread"]
    mock_user = thread_test_context["mock_user"]
    mock_thread_user = thread_test_context["mock_thread_user"]

    thread_id = mock_thread.id
    user_id = "existing_user_id"

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get_thread,
        patch.object(
            UserModel, "get_by_ids", new_callable=AsyncMock
        ) as mock_get_by_ids,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_get_thread_user,
    ):
        # Setup mocks
        mock_get_thread.return_value = mock_thread
        mock_get_by_ids.return_value = [mock_user]
        # User already exists in thread
        mock_get_thread_user.return_value = mock_thread_user

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}/users",
            method="POST",
            json={"user_id": user_id, "role": "user"},
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import add_thread_user

            with pytest.raises(BadRequest) as excinfo:
                await add_thread_user(thread_id)

            # Verify error message
            assert "already in the thread" in str(excinfo.value)

        # Verify mocks were called correctly
        assert mock_get_thread.call_count >= 1  # Called multiple times
        mock_get_by_ids.assert_called_once_with(user_ids=[user_id])


@pytest.mark.asyncio
async def test_add_thread_user_by_email(thread_test_context: dict) -> None:
    """Test adding a user to a thread by email."""
    app = thread_test_context["app"]
    mock_token = thread_test_context["mock_token"]
    mock_thread = thread_test_context["mock_thread"]
    mock_user = thread_test_context["mock_user"]
    mock_thread_user = thread_test_context["mock_thread_user"]

    thread_id = mock_thread.id
    email = "user@example.com"

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get_thread,
        patch.object(
            UserModel, "get_by_email", new_callable=AsyncMock
        ) as mock_get_by_email,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_get_thread_user,
        patch.object(
            ThreadUserModel, "create", new_callable=AsyncMock
        ) as mock_create_thread_user,
    ):
        # Setup mocks
        mock_get_thread.return_value = mock_thread
        mock_get_by_email.return_value = mock_user
        # User not in thread
        mock_get_thread_user.return_value = None
        mock_create_thread_user.return_value = mock_thread_user

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}/users/email",
            method="POST",
            json={"email": email},
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import (
                add_thread_user_by_email,
            )

            result = await add_thread_user_by_email(thread_id)

            # Verify response
            assert "thread_user" in result
            assert "user" in result
            assert result["thread_user"] == mock_thread_user.model_dump()
            assert result["user"] == mock_user.model_dump()

        # Verify mocks were called correctly
        assert mock_get_thread.call_count >= 1  # Called multiple times
        mock_get_by_email.assert_called_once_with(email=email)
        mock_create_thread_user.assert_called_once()


@pytest.mark.asyncio
async def test_update_thread_user(thread_test_context: dict) -> None:
    """Test updating a user's role in a thread."""
    app = thread_test_context["app"]
    mock_token = thread_test_context["mock_token"]
    mock_thread = thread_test_context["mock_thread"]
    mock_thread_user = thread_test_context["mock_thread_user"]

    thread_id = mock_thread.id
    user_id = "target_user_id"
    new_role = "admin"

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get_thread,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_get_thread_user,
        patch.object(
            ThreadUserModel, "update_role", new_callable=AsyncMock
        ) as mock_update_role,
    ):
        # Setup mocks
        mock_get_thread.return_value = mock_thread
        # Current user is in thread
        mock_get_thread_user.return_value = mock_thread_user
        mock_update_role.return_value = mock_thread_user

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}/users/{user_id}",
            method="PUT",
            json={"user_id": user_id, "role": new_role},
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import update_thread_user

            result = await update_thread_user(thread_id, user_id)

            # Verify response
            assert "thread_user" in result
            assert result["thread_user"] == mock_thread_user.model_dump()

        # Verify mocks were called correctly
        assert mock_get_thread.call_count >= 1  # Called multiple times
        mock_update_role.assert_called_once_with(
            thread_id=thread_id, user_id=user_id, role=new_role
        )


@pytest.mark.asyncio
async def test_remove_thread_user(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test removing a user from a thread when the current user is an admin."""
    thread_id = mock_thread.id
    user_id = "target_user_id"  # Different from current user

    # Change the thread's user_id to be different from the token's user_id
    # This is critical because we're testing admin access, not owner access
    mock_thread.user_id = "different_owner_id"  # Not the current user

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get_thread,
        patch.object(
            ThreadUserModel, "get", new_callable=AsyncMock
        ) as mock_get_thread_user,
        patch.object(
            ThreadUserModel, "delete", new_callable=AsyncMock
        ) as mock_delete_thread_user,
    ):
        # Setup mocks
        mock_get_thread.return_value = mock_thread
        # Current user is admin
        mock_get_thread_user.return_value = MagicMock(role="admin")

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}/users/{user_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import remove_thread_user

            response = await remove_thread_user(thread_id, user_id)

            # Verify response
            assert response.status_code == HTTPStatus.NO_CONTENT

        # Verify mocks were called correctly
        mock_get_thread.assert_called_once_with(thread_id=thread_id)
        # Since this is NOT the user removing themselves AND
        # the thread owner is different, get_thread_user should be called
        mock_get_thread_user.assert_called_once_with(
            thread_id=thread_id, user_id=mock_token.user_id
        )
        mock_delete_thread_user.assert_called_once_with(
            thread_id=thread_id, user_id=user_id
        )


@pytest.mark.asyncio
async def test_remove_thread_user_self(
    app: Quart,
    mock_token: TokenPayload,
    mock_thread: MagicMock,
    mock_decode_token: AsyncMock,
    mock_redis: AsyncMock,
) -> None:
    """Test a user removing themselves from a thread."""
    thread_id = mock_thread.id
    user_id = mock_token.user_id  # Self

    with (
        patch.object(ThreadModel, "get", new_callable=AsyncMock) as mock_get_thread,
        patch.object(
            ThreadUserModel, "delete", new_callable=AsyncMock
        ) as mock_delete_thread_user,
    ):
        # Setup mocks
        mock_get_thread.return_value = mock_thread

        # Create request context
        async with app.test_request_context(
            f"/api/thread/{thread_id}/users/{user_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.thread_controller import remove_thread_user

            response = await remove_thread_user(thread_id, user_id)

            # Verify response
            assert response.status_code == HTTPStatus.NO_CONTENT

        # Verify mocks were called correctly
        assert mock_get_thread.call_count >= 1  # Called multiple times
        mock_delete_thread_user.assert_called_once_with(
            thread_id=thread_id, user_id=user_id
        )
