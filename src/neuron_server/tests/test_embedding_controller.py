from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from quart import Quart
from werkzeug.exceptions import NotFound

from neuron_server.api import app as neuron_app
from neuron_server.controllers.auth import TokenPayload
from neuron_server.models.embedding_model import EmbeddingModel

# Constants
TEST_JWT_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"
TEST_EMBEDDING_ID = "test-embedding-123"


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
def mock_embedding() -> MagicMock:
    """Create a mock embedding for testing."""
    embedding = MagicMock(name="MockEmbedding")
    embedding.id = TEST_EMBEDDING_ID
    embedding.document = "Test document content"
    embedding.cmetadata = {"source": "test", "user_id": "test_user_id"}
    embedding.embedding = [0.1, 0.2, 0.3]
    embedding.model_dump.return_value = {
        "id": embedding.id,
        "document": embedding.document,
        "cmetadata": embedding.cmetadata,
        "embedding": embedding.embedding,
    }
    return embedding


@pytest.fixture
def mock_decode_token() -> AsyncMock:
    """Mock the decode_token function."""
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
async def test_upsert_embedding(
    app: Quart,
    mock_token: TokenPayload,
    mock_embedding: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test upserting an embedding (creating a new one)."""
    # Setup test data
    test_data = {
        "content": "Test document content",
        "metadata": {"source": "test", "user_id": "test_user_id"},
    }

    # Setup mocks
    with (
        patch(
            "neuron_server.controllers.embedding_controller.memories_store",
            new_callable=AsyncMock,
        ) as mock_memories_store,
        patch.object(EmbeddingModel, "get", new_callable=AsyncMock) as mock_get,
    ):
        # First call returns None (not found), second call returns the created embedding
        mock_get.side_effect = [None, mock_embedding]

        # Mock the memories_store.aadd_texts method
        mock_memories_store.aadd_texts = AsyncMock()

        # Create request context
        async with app.test_request_context(
            f"/api/embedding/{TEST_EMBEDDING_ID}",
            method="POST",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.embedding_controller import upsert_embedding

            result = await upsert_embedding(TEST_EMBEDDING_ID)

            # Verify response
            assert "embeddings" in result
            assert len(result["embeddings"]) == 1
            assert result["embeddings"][0]["id"] == TEST_EMBEDDING_ID

        # Verify mocks were called correctly
        mock_get.assert_called_with(embedding_id=TEST_EMBEDDING_ID)
        mock_memories_store.aadd_texts.assert_called_once_with(
            texts=[test_data["content"]],
            metadatas=[test_data["metadata"]],
            ids=[TEST_EMBEDDING_ID],
        )


@pytest.mark.asyncio
async def test_upsert_embedding_existing(
    app: Quart,
    mock_token: TokenPayload,
    mock_embedding: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test upserting an embedding (updating an existing one)."""
    # Setup test data
    test_data = {
        "content": "Updated document content",
        "metadata": {"source": "updated", "tag": "new_tag"},
    }

    # Existing metadata in the embedding
    existing_metadata = {"source": "original", "user_id": "test_user_id"}
    mock_embedding.cmetadata = existing_metadata

    # Expected merged metadata
    expected_merged_metadata = {
        "source": "updated",  # Overwritten by new metadata
        "user_id": "test_user_id",  # Preserved from existing metadata
        "tag": "new_tag",  # Added from new metadata
    }

    # Setup mocks
    with (
        patch(
            "neuron_server.controllers.embedding_controller.memories_store",
            new_callable=AsyncMock,
        ) as mock_memories_store,
        patch.object(EmbeddingModel, "get", new_callable=AsyncMock) as mock_get,
    ):
        # Both calls return the existing embedding
        mock_get.return_value = mock_embedding

        # Mock the memories_store.aadd_texts method
        mock_memories_store.aadd_texts = AsyncMock()

        # Create request context
        async with app.test_request_context(
            f"/api/embedding/{TEST_EMBEDDING_ID}",
            method="POST",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.embedding_controller import upsert_embedding

            result = await upsert_embedding(TEST_EMBEDDING_ID)

            # Verify response
            assert "embeddings" in result
            assert len(result["embeddings"]) == 1
            assert result["embeddings"][0]["id"] == TEST_EMBEDDING_ID

        # Verify mocks were called correctly
        mock_get.assert_called_with(embedding_id=TEST_EMBEDDING_ID)
        mock_memories_store.aadd_texts.assert_called_once_with(
            texts=[test_data["content"]],
            metadatas=[expected_merged_metadata],
            ids=[TEST_EMBEDDING_ID],
        )


@pytest.mark.asyncio
async def test_delete_embedding(
    app: Quart,
    mock_token: TokenPayload,
    mock_embedding: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test deleting an embedding."""
    # Setup mocks
    with (
        patch.object(EmbeddingModel, "get", new_callable=AsyncMock) as mock_get,
        patch.object(EmbeddingModel, "delete", new_callable=AsyncMock) as mock_delete,
    ):
        mock_get.return_value = mock_embedding
        mock_delete.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/embedding/{TEST_EMBEDDING_ID}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.embedding_controller import delete_embedding

            response = await delete_embedding(TEST_EMBEDDING_ID)

            # Verify response
            assert response.status_code == HTTPStatus.NO_CONTENT

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(embedding_id=TEST_EMBEDDING_ID)
        mock_delete.assert_called_once_with(embedding_id=TEST_EMBEDDING_ID)


@pytest.mark.asyncio
async def test_delete_embedding_not_found(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
) -> None:
    """Test deleting a non-existent embedding."""
    # Setup mocks
    with patch.object(EmbeddingModel, "get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None

        # Create request context
        async with app.test_request_context(
            f"/api/embedding/{TEST_EMBEDDING_ID}",
            method="DELETE",
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.embedding_controller import delete_embedding

            with pytest.raises(NotFound, match="Embedding not found"):
                await delete_embedding(TEST_EMBEDDING_ID)

        # Verify mocks were called correctly
        mock_get.assert_called_once_with(embedding_id=TEST_EMBEDDING_ID)


@pytest.mark.asyncio
async def test_bulk_delete_embeddings(
    app: Quart,
    mock_token: TokenPayload,
    mock_embedding: MagicMock,
    mock_decode_token: AsyncMock,
) -> None:
    """Test bulk deleting embeddings."""
    embedding_ids = [TEST_EMBEDDING_ID, "test-embedding-456", "test-embedding-789"]

    # Setup test data
    test_data = {
        "embedding_ids": embedding_ids,
    }

    # Create multiple mock embeddings
    embeddings = []
    for embedding_id in embedding_ids:
        embedding = MagicMock(name=f"MockEmbedding-{embedding_id}")
        embedding.id = embedding_id
        embedding.document = f"Test document content for {embedding_id}"
        embedding.cmetadata = {"source": "test", "user_id": "test_user_id"}
        embedding.embedding = [0.1, 0.2, 0.3]
        embeddings.append(embedding)

    # Setup mocks
    with (
        patch.object(
            EmbeddingModel, "get_many", new_callable=AsyncMock
        ) as mock_get_many,
        patch.object(
            EmbeddingModel, "delete_many", new_callable=AsyncMock
        ) as mock_delete_many,
    ):
        mock_get_many.return_value = embeddings
        mock_delete_many.return_value = None

        # Create request context
        async with app.test_request_context(
            "/api/embedding/bulk",
            method="DELETE",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.embedding_controller import (
                bulk_delete_embeddings,
            )

            response = await bulk_delete_embeddings()

            # Verify response
            assert response.status_code == HTTPStatus.NO_CONTENT

        # Verify mocks were called correctly
        mock_get_many.assert_called_once_with(ids=embedding_ids)
        mock_delete_many.assert_called_once_with(ids=embedding_ids)


@pytest.mark.asyncio
async def test_bulk_delete_embeddings_missing(
    app: Quart,
    mock_token: TokenPayload,
    mock_decode_token: AsyncMock,
) -> None:
    """Test bulk deleting embeddings with some missing IDs."""
    valid_embedding_id = "test-embedding-123"
    missing_embedding_id = "test-embedding-missing"
    embedding_ids = [valid_embedding_id, missing_embedding_id]

    # Setup test data
    test_data = {
        "embedding_ids": embedding_ids,
    }

    # Create a mock embedding for the valid ID only
    embedding = MagicMock(name=f"MockEmbedding-{valid_embedding_id}")
    embedding.id = valid_embedding_id
    embedding.document = f"Test document content for {valid_embedding_id}"
    embedding.cmetadata = {"source": "test", "user_id": "test_user_id"}
    embedding.embedding = [0.1, 0.2, 0.3]

    # Setup mocks
    with patch.object(
        EmbeddingModel, "get_many", new_callable=AsyncMock
    ) as mock_get_many:
        # Return only the valid embedding
        mock_get_many.return_value = [embedding]

        # Create request context
        async with app.test_request_context(
            "/api/embedding/bulk",
            method="DELETE",
            json=test_data,
            headers={"Authorization": TEST_JWT_TOKEN},
        ):
            # Set token on request
            app.request_class.token = mock_token

            # Call the endpoint function directly
            from neuron_server.controllers.embedding_controller import (
                bulk_delete_embeddings,
            )

            with pytest.raises(
                NotFound, match=f"Embeddings not found: {missing_embedding_id}"
            ):
                await bulk_delete_embeddings()

        # Verify mocks were called correctly
        mock_get_many.assert_called_once_with(ids=embedding_ids)
