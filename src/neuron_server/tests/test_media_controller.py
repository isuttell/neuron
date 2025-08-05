from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from quart import Quart

from neuron_server.api import app as neuron_app
from neuron_server.controllers.auth import TokenPayload
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.models.media_list_item_model import MediaListItemModel
from neuron_server.models.media_list_model import MediaListModel

# Constants
TEST_JWT_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"
ISO_DATETIME = "2023-01-01T12:00:00"


@pytest.fixture
def app() -> Quart:
    """Return the Quart app with patched test client and request context."""
    return neuron_app


@pytest.fixture
def mock_token() -> TokenPayload:
    """Create a mock token for testing."""
    return TokenPayload(
        user_id="test_user_id",
        roles=["user"],
        email="test@example.com",
        nickname="test_user",
        picture=None,
        permissions=[],
    )


@pytest.fixture
def mock_media_item() -> MagicMock:
    """Create a mock media item for testing."""
    media_item = MagicMock(name="MockMediaItem")
    media_item.id = uuid4()
    media_item.name = "Test Media"
    media_item.description = "Test Description"
    media_item.url = "https://example.com/test.jpg"
    media_item.media_type = "image"
    media_item.thread_id = uuid4()
    media_item.user_id = "test_user_id"
    media_item.model_dump.return_value = {
        "id": str(media_item.id),
        "name": media_item.name,
        "description": media_item.description,
        "url": media_item.url,
        "media_type": media_item.media_type,
        "thread_id": str(media_item.thread_id),
        "user_id": media_item.user_id,
    }
    return media_item


@pytest.fixture
def mock_media_list() -> MagicMock:
    """Create a mock media list for testing."""
    media_list = MagicMock(name="MockMediaList")
    media_list.id = uuid4()
    media_list.name = "Test Media List"
    media_list.description = "Test Description"
    media_list.tags = ["test", "media"]
    media_list.user_id = "test_user_id"
    media_list.visibility = "private"
    media_list.shared_with = []
    media_list.model_dump.return_value = {
        "id": str(media_list.id),
        "name": media_list.name,
        "description": media_list.description,
        "tags": media_list.tags,
        "user_id": media_list.user_id,
        "visibility": media_list.visibility,
        "shared_with": media_list.shared_with,
    }
    return media_list


@pytest.fixture
def mock_media_list_item() -> MagicMock:
    """Create a mock media list item for testing."""
    media_list_item = MagicMock(name="MockMediaListItem")
    media_list_item.id = uuid4()
    media_list_item.media_list_id = uuid4()
    media_list_item.media_item_id = uuid4()
    media_list_item.index = 0
    # Simplify datetime handling by using constant strings
    media_list_item.created_at.astimezone().isoformat.return_value = ISO_DATETIME
    media_list_item.updated_at.astimezone().isoformat.return_value = ISO_DATETIME
    media_list_item.model_dump.return_value = {
        "id": str(media_list_item.id),
        "media_list_id": str(media_list_item.media_list_id),
        "media_item_id": str(media_list_item.media_item_id),
        "index": media_list_item.index,
    }
    return media_list_item


@pytest.fixture
def mock_decode_token() -> AsyncMock:
    """Mock the decode_token function."""
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
async def test_get_recent_media(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_item: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting recent media items."""
    # Setup mocks
    with patch.object(
        MediaItemModel, "get_recent", new_callable=AsyncMock
    ) as mock_get_recent:
        mock_get_recent.return_value = [mock_media_item]

        # Create request context
        async with app.test_request_context(
            "/api/media/recent?limit=10&offset=0",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import get_recent_media

            result = await get_recent_media()

            # Verify response
            assert "media_items" in result
            assert len(result["media_items"]) == 1
            assert result["media_items"][0]["id"] == str(mock_media_item.id)

        # Verify mocks were called correctly
        mock_get_recent.assert_called_once_with(mock_token.user_id, limit=10, offset=0)


@pytest.mark.asyncio
async def test_get_recent_media_empty(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting recent media items when there are no items."""
    # Setup mocks
    with patch.object(
        MediaItemModel, "get_recent", new_callable=AsyncMock
    ) as mock_get_recent:
        mock_get_recent.return_value = []

        # Create request context
        async with app.test_request_context(
            "/api/media/recent?limit=10&offset=0",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import get_recent_media

            result = await get_recent_media()

            # Verify response
            assert "media_items" in result
            assert len(result["media_items"]) == 0

        # Verify mocks were called correctly
        mock_get_recent.assert_called_once_with(mock_token.user_id, limit=10, offset=0)


@pytest.mark.asyncio
async def test_create_media_list(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test creating a new media list."""
    # Setup test data
    test_data = {
        "name": "Test Media List",
        "description": "Test Description",
        "tags": ["test", "media"],
        "visibility": "private",
        "shared_with": [],
    }

    # Setup mocks
    with patch.object(MediaListModel, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_media_list

        # Create request context
        async with app.test_request_context(
            "/api/media/lists",
            method="POST",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import create_media_list

            result = await create_media_list()

            # Verify response
            assert "media_lists" in result
            assert len(result["media_lists"]) == 1
            assert result["media_lists"][0]["id"] == str(mock_media_list.id)

        # Verify mocks were called correctly with correct CreateParams
        mock_create.assert_called_once()
        create_params = mock_create.call_args[1]["params"]
        assert create_params.name == test_data["name"]
        assert create_params.description == test_data["description"]
        assert create_params.tags == test_data["tags"]
        assert create_params.visibility == test_data["visibility"]
        assert create_params.shared_with == test_data["shared_with"]
        assert create_params.user_id == mock_token.user_id


@pytest.fixture
def test_context(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_media_list_item: MagicMock,
    mock_media_item: MagicMock,
) -> dict:
    """Fixture that combines commonly used test objects."""
    return {
        "app": app,
        "mock_token": mock_token,
        "mock_media_list": mock_media_list,
        "mock_media_list_item": mock_media_list_item,
        "mock_media_item": mock_media_item,
    }


@pytest.mark.asyncio
async def test_get_media_lists(
    test_context: dict,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting all media lists for a user."""
    app = test_context["app"]
    mock_token = test_context["mock_token"]
    mock_media_list = test_context["mock_media_list"]
    mock_media_list_item = test_context["mock_media_list_item"]
    mock_media_item = test_context["mock_media_item"]

    # Setup mocks
    with (
        patch.object(
            MediaListModel, "list_for_user", new_callable=AsyncMock
        ) as mock_list_for_user,
        patch.object(
            MediaListItemModel, "get_by_list", new_callable=AsyncMock
        ) as mock_get_by_list,
        patch.object(
            MediaItemModel, "get_many", new_callable=AsyncMock
        ) as mock_get_many,
    ):
        mock_list_for_user.return_value = [mock_media_list]
        mock_get_by_list.return_value = [mock_media_list_item]
        mock_get_many.return_value = [mock_media_item]

        # Create request context
        async with app.test_request_context(
            "/api/media/lists",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import get_media_lists

            result = await get_media_lists()

            # Verify response
            assert "media_lists" in result
            assert "media_list_items" in result
            assert "media_items" in result
            assert len(result["media_lists"]) == 1
            assert len(result["media_list_items"]) == 1
            assert len(result["media_items"]) == 1
            assert result["media_lists"][0]["id"] == str(mock_media_list.id)
            assert result["media_list_items"][0]["id"] == str(mock_media_list_item.id)
            assert result["media_items"][0]["id"] == str(mock_media_item.id)

        # Verify mocks were called correctly
        mock_list_for_user.assert_called_once_with(mock_token.user_id)
        mock_get_by_list.assert_called_once_with(mock_media_list.id)
        mock_get_many.assert_called_once()


@pytest.mark.asyncio
async def test_get_media_list(
    test_context: dict,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting a specific media list."""
    app = test_context["app"]
    mock_token = test_context["mock_token"]
    mock_media_list = test_context["mock_media_list"]
    mock_media_list_item = test_context["mock_media_list_item"]
    mock_media_item = test_context["mock_media_item"]
    list_id = mock_media_list.id

    # Setup mocks
    with (
        patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            MediaListItemModel, "get_by_list", new_callable=AsyncMock
        ) as mock_get_by_list,
        patch.object(
            MediaItemModel, "get_many", new_callable=AsyncMock
        ) as mock_get_many,
    ):
        mock_get.return_value = mock_media_list
        mock_get_by_list.return_value = [mock_media_list_item]
        mock_get_many.return_value = [mock_media_item]

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import get_media_list

            result = await get_media_list(list_id)

            # Verify response
            assert "media_lists" in result
            assert "media_list_items" in result
            assert "media_items" in result
            assert len(result["media_lists"]) == 1
            assert len(result["media_list_items"]) == 1
            assert len(result["media_items"]) == 1
            assert result["media_lists"][0]["id"] == str(mock_media_list.id)
            assert result["media_list_items"][0]["id"] == str(mock_media_list_item.id)
            assert result["media_items"][0]["id"] == str(mock_media_item.id)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)
        mock_get_by_list.assert_called_once_with(list_id)
        mock_get_many.assert_called_once()


@pytest.mark.asyncio
async def test_get_media_list_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting a non-existent media list."""
    list_id = uuid4()

    # Setup mocks
    with patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import get_media_list

            result, status = await get_media_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Media list not found"
            assert status == HTTPStatus.NOT_FOUND

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_get_media_list_unauthorized(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test getting a media list without proper access."""
    list_id = mock_media_list.id

    # Change media list owner to be different from token user
    mock_media_list.user_id = "different_user_id"
    mock_media_list.shared_with = []
    mock_media_list.visibility = "private"

    # Setup mocks
    with patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_media_list

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import get_media_list

            result, status = await get_media_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Unauthorized"
            assert status == HTTPStatus.FORBIDDEN

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_get_media_list_public_visibility(
    test_context: dict,
    mock_decode_token: AsyncMock,
) -> None:
    """Test accessing a media list with public visibility."""
    app = test_context["app"]
    mock_token = test_context["mock_token"]
    mock_media_list = test_context["mock_media_list"]
    mock_media_list_item = test_context["mock_media_list_item"]
    mock_media_item = test_context["mock_media_item"]
    list_id = mock_media_list.id

    # Change media list owner to be different from token user but with public visibility
    mock_media_list.user_id = "different_user_id"
    mock_media_list.shared_with = []
    mock_media_list.visibility = "public"

    # Setup mocks
    with (
        patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            MediaListItemModel, "get_by_list", new_callable=AsyncMock
        ) as mock_get_by_list,
        patch.object(
            MediaItemModel, "get_many", new_callable=AsyncMock
        ) as mock_get_many,
    ):
        mock_get.return_value = mock_media_list
        mock_get_by_list.return_value = [mock_media_list_item]
        mock_get_many.return_value = [mock_media_item]

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import get_media_list

            result = await get_media_list(list_id)

            # Verify response - should succeed because it's public
            assert "media_lists" in result
            assert "media_list_items" in result
            assert "media_items" in result
            assert len(result["media_lists"]) == 1
            assert result["media_lists"][0]["id"] == str(mock_media_list.id)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)
        mock_get_by_list.assert_called_once_with(list_id)
        mock_get_many.assert_called_once()


@pytest.mark.asyncio
async def test_get_media_list_shared_with_user(
    test_context: dict,
    mock_decode_token: AsyncMock,
) -> None:
    """Test accessing a media list that is shared with the user."""
    app = test_context["app"]
    mock_token = test_context["mock_token"]
    mock_media_list = test_context["mock_media_list"]
    mock_media_list_item = test_context["mock_media_list_item"]
    mock_media_item = test_context["mock_media_item"]
    list_id = mock_media_list.id

    # Change media list owner to be different from token user but shared with the user
    mock_media_list.user_id = "different_user_id"
    mock_media_list.shared_with = ["test_user_id"]  # User is in shared_with list
    mock_media_list.visibility = "private"  # Private but shared

    # Setup mocks
    with (
        patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(
            MediaListItemModel, "get_by_list", new_callable=AsyncMock
        ) as mock_get_by_list,
        patch.object(
            MediaItemModel, "get_many", new_callable=AsyncMock
        ) as mock_get_many,
    ):
        mock_get.return_value = mock_media_list
        mock_get_by_list.return_value = [mock_media_list_item]
        mock_get_many.return_value = [mock_media_item]

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import get_media_list

            result = await get_media_list(list_id)

            # Verify response - should succeed because it's shared with the user
            assert "media_lists" in result
            assert "media_list_items" in result
            assert "media_items" in result
            assert len(result["media_lists"]) == 1
            assert result["media_lists"][0]["id"] == str(mock_media_list.id)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)
        mock_get_by_list.assert_called_once_with(list_id)
        mock_get_many.assert_called_once()


@pytest.mark.asyncio
async def test_update_media_list(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test updating a media list."""
    list_id = mock_media_list.id

    # Setup test data
    test_data = {
        "name": "Updated Media List",
        "description": "Updated Description",
        "tags": ["updated", "media"],
        "visibility": "public",
        "shared_with": ["user1", "user2"],
    }

    # Setup mocks
    with (
        patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(MediaListModel, "update", new_callable=AsyncMock) as mock_update,
    ):
        mock_get.return_value = mock_media_list
        mock_update.return_value = mock_media_list

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            method="PUT",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import update_media_list

            result = await update_media_list(list_id)

            # Verify response
            assert "media_list" in result
            assert result["media_list"]["id"] == str(mock_media_list.id)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)
        mock_update.assert_called_once()
        update_params = mock_update.call_args[1]["params"]
        assert update_params.list_id == list_id
        assert update_params.name == test_data["name"]
        assert update_params.description == test_data["description"]
        assert update_params.tags == test_data["tags"]
        assert update_params.visibility == test_data["visibility"]
        assert update_params.shared_with == test_data["shared_with"]


@pytest.mark.asyncio
async def test_update_media_list_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
) -> None:
    """Test updating a non-existent media list."""
    list_id = uuid4()

    # Setup test data
    test_data = {
        "name": "Updated Media List",
        "description": "Updated Description",
        "tags": ["updated", "media"],
        "visibility": "public",
        "shared_with": ["user1", "user2"],
    }

    # Setup mocks
    with patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            method="PUT",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import update_media_list

            result, status = await update_media_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Media list not found"
            assert status == HTTPStatus.NOT_FOUND

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_update_media_list_unauthorized(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test updating a media list without proper access."""
    list_id = mock_media_list.id

    # Change media list owner to be different from token user
    mock_media_list.user_id = "different_user_id"

    # Setup test data
    test_data = {
        "name": "Updated Media List",
        "description": "Updated Description",
        "tags": ["updated", "media"],
        "visibility": "public",
        "shared_with": ["user1", "user2"],
    }

    # Setup mocks
    with patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_media_list

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            method="PUT",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import update_media_list

            result, status = await update_media_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Unauthorized"
            assert status == HTTPStatus.FORBIDDEN

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_delete_media_list(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test deleting a media list."""
    list_id = mock_media_list.id

    # Setup mocks
    with (
        patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(MediaListModel, "delete", new_callable=AsyncMock) as mock_delete,
    ):
        mock_get.return_value = mock_media_list
        mock_delete.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import delete_media_list

            result = await delete_media_list(list_id)

            # Verify response
            assert "success" in result
            assert result["success"] is True

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)
        mock_delete.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_delete_media_list_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
) -> None:
    """Test deleting a non-existent media list."""
    list_id = uuid4()

    # Setup mocks
    with patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import delete_media_list

            result, status = await delete_media_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Media list not found"
            assert status == HTTPStatus.NOT_FOUND

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_delete_media_list_unauthorized(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test deleting a media list without proper access."""
    list_id = mock_media_list.id

    # Change media list owner to be different from token user
    mock_media_list.user_id = "different_user_id"

    # Setup mocks
    with patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_media_list

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import delete_media_list

            result, status = await delete_media_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Unauthorized"
            assert status == HTTPStatus.FORBIDDEN

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_add_media_to_list(
    test_context: dict,
    mock_decode_token: AsyncMock,
) -> None:
    """Test adding a media item to a list."""
    app = test_context["app"]
    mock_token = test_context["mock_token"]
    mock_media_list = test_context["mock_media_list"]
    mock_media_item = test_context["mock_media_item"]
    mock_media_list_item = test_context["mock_media_list_item"]

    list_id = mock_media_list.id
    media_item_id = mock_media_item.id

    # Setup test data
    test_data = {"media_item_id": str(media_item_id)}

    # Setup mocks
    with (
        patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(MediaItemModel, "get", new_callable=AsyncMock) as mock_get_item,
        patch.object(
            MediaListModel, "get_max_index", new_callable=AsyncMock
        ) as mock_get_max_index,
        patch.object(
            MediaListModel, "add_media_item", new_callable=AsyncMock
        ) as mock_add_media_item,
    ):
        mock_get.return_value = mock_media_list
        mock_get_item.return_value = mock_media_item
        # Mock the current max index as 1, so next index should be 2
        mock_get_max_index.return_value = 1
        mock_add_media_item.return_value = mock_media_list_item

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}/media",
            method="POST",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import add_media_to_list

            result = await add_media_to_list(list_id)

            # Verify response
            assert "media_list_items" in result
            assert len(result["media_list_items"]) == 1
            # No assertion on the actual response content as it's different from mock

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)
        mock_get_item.assert_called_once_with(media_id=media_item_id)
        mock_get_max_index.assert_called_once_with(list_id)
        # Index should be current max index + 1 (1 + 1 = 2)
        # This matches the logic in media_controller.py lines 171-172
        mock_add_media_item.assert_called_once_with(
            list_id=list_id, media_item_id=media_item_id, index=2
        )


@pytest.mark.asyncio
async def test_add_media_to_list_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
) -> None:
    """Test adding a media item to a non-existent list."""
    list_id = uuid4()

    # Setup test data
    test_data = {"media_item_id": str(uuid4())}

    # Setup mocks
    with patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}/media",
            method="POST",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import add_media_to_list

            result, status = await add_media_to_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Media list not found"
            assert status == HTTPStatus.NOT_FOUND

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_add_media_to_list_unauthorized(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test adding a media item to a list without proper access."""
    list_id = mock_media_list.id

    # Change media list owner to be different from token user
    mock_media_list.user_id = "different_user_id"

    # Setup test data
    test_data = {"media_item_id": str(uuid4())}

    # Setup mocks
    with patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_media_list

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}/media",
            method="POST",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import add_media_to_list

            result, status = await add_media_to_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Unauthorized"
            assert status == HTTPStatus.FORBIDDEN

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)


@pytest.mark.asyncio
async def test_add_media_to_list_media_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_media_list: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test adding a non-existent media item to a list."""
    list_id = mock_media_list.id
    media_item_id = uuid4()

    # Setup test data
    test_data = {"media_item_id": str(media_item_id)}

    # Setup mocks
    with (
        patch.object(MediaListModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(MediaItemModel, "get", new_callable=AsyncMock) as mock_get_item,
    ):
        mock_get.return_value = mock_media_list
        mock_get_item.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/media/lists/{list_id}/media",
            method="POST",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.media_controller import add_media_to_list

            result, status = await add_media_to_list(list_id)

            # Verify response
            assert "error" in result
            assert result["error"] == "Media item not found"
            assert status == HTTPStatus.NOT_FOUND

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(list_id=list_id)
        mock_get_item.assert_called_once_with(media_id=media_item_id)
