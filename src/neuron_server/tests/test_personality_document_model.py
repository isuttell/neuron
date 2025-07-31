"""Tests for PersonalityDocumentModel."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from langchain.schema import Document
from sqlalchemy.ext.asyncio import AsyncSession

from neuron_server.database import PersonalityDocument
from neuron_server.models.personality_document_model import PersonalityDocumentModel


@pytest.fixture
def test_document_params():
    return PersonalityDocumentModel.CreateParams(
        personality_id=uuid4(),
        user_id="test_user_id",
        name="test_document.txt",
        content="This is a test document. It has multiple sentences. "
        * 100,  # Long content for splitting
    )


@pytest.fixture
def mock_session():
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_memory_store():
    store = MagicMock()
    store.collection_name = "test_collection"
    store.aadd_documents = AsyncMock()
    store.delete_documents = AsyncMock(return_value=True)
    return store


@pytest.fixture
def mock_document_entity():
    doc = MagicMock(spec=PersonalityDocument)
    doc.id = uuid4()
    doc.personality_id = uuid4()
    doc.user_id = "test_user_id"
    doc.name = "test_document.txt"
    doc.content = "Test content"
    doc.doc_metadata = {"chunk_ids": ["chunk1", "chunk2"]}
    doc.created_at = "2024-01-01T00:00:00Z"
    return doc


@pytest.mark.asyncio
@patch("neuron_server.models.personality_document_model.get_session")
@patch("neuron_server.models.personality_document_model.memories_store")
async def test_create_document_with_text_splitting(
    mock_memories_store,
    mock_get_session,
    test_document_params,
    mock_session,
    mock_memory_store,
    mock_document_entity,
):
    """Test creating a document with text splitting and memory integration."""
    # Setup mocks
    mock_get_session.return_value.__aenter__.return_value = mock_session
    mock_memories_store.aadd_documents = mock_memory_store.aadd_documents

    # Mock document creation in database
    mock_session.execute = AsyncMock()
    mock_session.execute.return_value.scalar_one_or_none = AsyncMock(return_value=None)

    # Test document creation
    # Mock the document entity to be returned
    mock_session.add = MagicMock()

    # Create a proper mock document object
    created_doc = MagicMock(spec=PersonalityDocument)
    created_doc.id = mock_document_entity.id
    created_doc.personality_id = test_document_params.personality_id
    created_doc.user_id = test_document_params.user_id
    created_doc.name = test_document_params.name
    created_doc.content = test_document_params.content
    created_doc.doc_metadata = {"chunk_ids": []}
    created_doc.created_at = "2024-01-01T00:00:00Z"

    # Mock PersonalityDocument constructor to return our mock
    with patch(
        "neuron_server.models.personality_document_model.PersonalityDocument"
    ) as mock_doc_class:
        mock_doc_class.return_value = created_doc
        with patch(
            "neuron_server.models.personality_document_model.uuid4"
        ) as mock_uuid:
            # Create a generator that returns unique IDs for all chunks
            def uuid_generator():
                # First return the document ID (not used since we mock
                # PersonalityDocument)
                yield mock_document_entity.id
                # Then return chunk IDs for as many chunks as needed
                chunk_num = 1
                while True:
                    yield f"chunk{chunk_num}_id"
                    chunk_num += 1

            mock_uuid.side_effect = uuid_generator()

            await PersonalityDocumentModel.create(test_document_params)

        # Verify session operations
        mock_session.add.assert_called_once()
        assert mock_session.commit.call_count >= 1  # Called at least once

        # Verify text was split and added to memory
        mock_memory_store.aadd_documents.assert_called_once()
        documents_added = mock_memory_store.aadd_documents.call_args[0][0]

        # Should have multiple chunks due to long content
        assert len(documents_added) > 1

        # Verify chunk metadata
        for i, doc in enumerate(documents_added):
            assert isinstance(doc, Document)
            assert doc.metadata["personality_id"] == str(
                test_document_params.personality_id
            )
            assert doc.metadata["document_id"] == str(created_doc.id)
            assert doc.metadata["document_name"] == test_document_params.name
            assert doc.metadata["chunk_index"] == i
            assert doc.metadata["total_chunks"] == len(documents_added)
            assert doc.metadata["source"] == "personality_document"

        # Verify document metadata was updated with chunk IDs
        assert created_doc.doc_metadata["chunk_ids"]


@pytest.mark.asyncio
@patch("neuron_server.models.personality_document_model.get_session")
async def test_list_documents_by_personality(
    mock_get_session,
    mock_session,
    mock_document_entity,
):
    """Test listing documents for a personality."""
    personality_id = uuid4()

    # Setup mocks
    mock_get_session.return_value.__aenter__.return_value = mock_session

    # Mock query results
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        mock_document_entity,
        mock_document_entity,
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Test listing
    documents = await PersonalityDocumentModel.list(personality_id)

    assert len(documents) == 2
    for doc in documents:
        assert hasattr(doc, "id")
        assert hasattr(doc, "name")
        assert hasattr(doc, "content")


@pytest.mark.asyncio
@patch("neuron_server.models.personality_document_model.get_session")
async def test_get_document_by_personality_and_id(
    mock_get_session,
    mock_session,
    mock_document_entity,
):
    """Test getting a specific document."""
    personality_id = uuid4()
    document_id = uuid4()

    # Setup mocks
    mock_get_session.return_value.__aenter__.return_value = mock_session

    # Mock query result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_document_entity
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Test getting document
    document = await PersonalityDocumentModel.get_by_personality_and_id(
        personality_id, document_id
    )

    assert document is not None
    assert document.id == mock_document_entity.id


@pytest.mark.asyncio
@patch("neuron_server.models.personality_document_model.get_session")
@patch("neuron_server.models.personality_document_model.EmbeddingModel")
async def test_delete_document_with_memory_cleanup(
    mock_embedding_model,
    mock_get_session,
    mock_session,
    mock_memory_store,
    mock_document_entity,
):
    """Test deleting a document and its memory chunks."""
    document_id = uuid4()

    # Setup mocks
    mock_get_session.return_value.__aenter__.return_value = mock_session
    mock_embedding_model.delete_many = AsyncMock()

    # Mock getting the document
    mock_session.get = AsyncMock(return_value=mock_document_entity)

    # Mock deletion
    mock_session.delete = AsyncMock()

    # Test deletion
    await PersonalityDocumentModel.delete(document_id)

    # Verify document was deleted from database
    mock_session.delete.assert_called_once_with(mock_document_entity)
    mock_session.commit.assert_called_once()

    # Verify memory chunks were deleted
    mock_embedding_model.delete_many.assert_called_once_with(["chunk1", "chunk2"])


@pytest.mark.asyncio
@patch("neuron_server.models.personality_document_model.get_session")
async def test_delete_document_not_found(
    mock_get_session,
    mock_session,
):
    """Test deleting a non-existent document."""
    document_id = uuid4()

    # Setup mocks
    mock_get_session.return_value.__aenter__.return_value = mock_session

    # Mock document not found
    mock_session.get = AsyncMock(return_value=None)

    # Test deletion - should raise ValueError
    with pytest.raises(ValueError, match=f"Document {document_id} not found"):
        await PersonalityDocumentModel.delete(document_id)

    # Verify no deletion was attempted
    assert not hasattr(mock_session.delete, "called") or not mock_session.delete.called


@pytest.mark.asyncio
@patch("neuron_server.models.personality_document_model.get_session")
@patch("neuron_server.models.personality_document_model.memories_store")
async def test_create_document_with_small_content(
    mock_memories_store,
    mock_get_session,
    mock_session,
    mock_memory_store,
    mock_document_entity,
):
    """Test creating a document with content that results in a single chunk."""
    params = PersonalityDocumentModel.CreateParams(
        personality_id=uuid4(),
        user_id="test_user_id",
        name="small_doc.txt",
        content="This is a small document.",
    )

    # Setup mocks
    mock_get_session.return_value.__aenter__.return_value = mock_session
    mock_memories_store.aadd_documents = mock_memory_store.aadd_documents
    mock_memories_store.delete_documents = mock_memory_store.delete_documents

    # Mock document creation
    mock_session.execute = AsyncMock()

    # Create a proper mock document object
    created_doc = MagicMock(spec=PersonalityDocument)
    created_doc.id = mock_document_entity.id
    created_doc.personality_id = params.personality_id
    created_doc.user_id = params.user_id
    created_doc.name = params.name
    created_doc.content = params.content
    created_doc.doc_metadata = {"chunk_ids": []}
    created_doc.created_at = "2024-01-01T00:00:00Z"

    # Mock PersonalityDocument constructor to return our mock
    with patch(
        "neuron_server.models.personality_document_model.PersonalityDocument"
    ) as mock_doc_class:
        mock_doc_class.return_value = created_doc
        with patch(
            "neuron_server.models.personality_document_model.uuid4"
        ) as mock_uuid:
            # Create a generator that returns unique IDs
            def uuid_generator():
                yield mock_document_entity.id
                yield "single_chunk_id"
                # Yield more in case needed
                chunk_num = 2
                while True:
                    yield f"chunk{chunk_num}_id"
                    chunk_num += 1

            mock_uuid.side_effect = uuid_generator()

            await PersonalityDocumentModel.create(params)

    # Verify only one chunk was created
    mock_memory_store.aadd_documents.assert_called_once()
    documents_added = mock_memory_store.aadd_documents.call_args[0][0]
    assert len(documents_added) == 1
    assert documents_added[0].page_content == "This is a small document."


@pytest.mark.asyncio
@patch("neuron_server.models.personality_document_model.get_session")
@patch("neuron_server.models.personality_document_model.memories_store")
async def test_create_document_memory_store_error_handling(
    mock_memories_store,
    mock_get_session,
    test_document_params,
    mock_session,
    mock_memory_store,
    mock_document_entity,
):
    """Test error handling when memory store fails."""
    # Setup mocks
    mock_get_session.return_value.__aenter__.return_value = mock_session
    mock_memories_store.aadd_documents = mock_memory_store.aadd_documents
    mock_memories_store.delete_documents = mock_memory_store.delete_documents

    # Mock memory store failure
    mock_memory_store.aadd_documents.side_effect = Exception("Memory store error")

    # Mock document creation in database
    mock_session.execute = AsyncMock()

    # Test should still succeed (memory store errors are logged but not raised)
    # Create a proper mock document object
    created_doc = MagicMock(spec=PersonalityDocument)
    created_doc.id = mock_document_entity.id
    created_doc.personality_id = test_document_params.personality_id
    created_doc.user_id = test_document_params.user_id
    created_doc.name = test_document_params.name
    created_doc.content = test_document_params.content
    created_doc.doc_metadata = {"chunk_ids": []}
    created_doc.created_at = "2024-01-01T00:00:00Z"

    # Mock PersonalityDocument constructor to return our mock
    with patch(
        "neuron_server.models.personality_document_model.PersonalityDocument"
    ) as mock_doc_class:
        mock_doc_class.return_value = created_doc
        with patch(
            "neuron_server.models.personality_document_model.uuid4"
        ) as mock_uuid:
            # Create a generator that returns the document ID and then chunk IDs
            def uuid_generator():
                yield mock_document_entity.id
                chunk_num = 1
                while True:
                    yield f"chunk{chunk_num}_id"
                    chunk_num += 1

            mock_uuid.side_effect = uuid_generator()

            # Memory store error will be raised since there's no error handling
            with pytest.raises(Exception, match="Memory store error"):
                await PersonalityDocumentModel.create(test_document_params)

    # Document creation should have been attempted
    mock_session.add.assert_called_once()
    # First commit happens before memory store, so it should be called
    assert mock_session.commit.call_count >= 1

    # Verify memory store was attempted
    mock_memory_store.aadd_documents.assert_called_once()


@pytest.mark.asyncio
async def test_create_params_validation():
    """Test CreateParams validation."""
    # Valid params
    params = PersonalityDocumentModel.CreateParams(
        personality_id=uuid4(),
        user_id="test_user",
        name="doc.txt",
        content="content",
    )
    assert params.personality_id
    assert params.user_id == "test_user"
    assert params.name == "doc.txt"
    assert params.content == "content"

    # Test with empty content - should still be valid
    params_empty = PersonalityDocumentModel.CreateParams(
        personality_id=uuid4(),
        user_id="test_user",
        name="empty.txt",
        content="",
    )
    assert params_empty.content == ""
