"""Unit tests for graph/document.py."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.graph.document import (
    ChunkConfig,
    DocumentMetadata,
    get_document,
    import_chunks,
    process_chunk,
    process_document,
)
from neuron_server.graph.models import (
    AtomicFact,
    DocumentResult,
    Extraction,
    SummaryResponse,
)


class TestDocumentMetadata:
    """Test cases for DocumentMetadata dataclass."""

    def test_document_metadata_creation(self) -> None:
        """Test creating DocumentMetadata with all fields."""
        metadata = DocumentMetadata(
            document_id="doc123",
            document_name="Test Document",
            personality_id="pers456",
            user_id="user789",
            source="test_source",
        )
        assert metadata.document_id == "doc123"
        assert metadata.document_name == "Test Document"
        assert metadata.personality_id == "pers456"
        assert metadata.user_id == "user789"
        assert metadata.source == "test_source"

    def test_document_metadata_optional_fields(self) -> None:
        """Test creating DocumentMetadata with only required fields."""
        metadata = DocumentMetadata(document_id="doc123")
        assert metadata.document_id == "doc123"
        assert metadata.document_name is None
        assert metadata.personality_id is None
        assert metadata.user_id is None
        assert metadata.source is None


class TestChunkConfig:
    """Test cases for ChunkConfig dataclass."""

    def test_chunk_config_defaults(self) -> None:
        """Test ChunkConfig with default values."""
        config = ChunkConfig()
        assert config.chunk_size == 2000  # noqa: PLR2004
        assert config.chunk_overlap == 200  # noqa: PLR2004
        assert config.max_attempts == 3  # noqa: PLR2004
        assert config.retry_delay_seconds == 1

    def test_chunk_config_custom_values(self) -> None:
        """Test ChunkConfig with custom values."""
        config = ChunkConfig(
            chunk_size=1000,
            chunk_overlap=100,
            max_attempts=5,
            retry_delay_seconds=2,
        )
        assert config.chunk_size == 1000  # noqa: PLR2004
        assert config.chunk_overlap == 100  # noqa: PLR2004
        assert config.max_attempts == 5  # noqa: PLR2004
        assert config.retry_delay_seconds == 2  # noqa: PLR2004


class TestImportChunks:
    """Test cases for import_chunks function."""

    @patch("neuron_server.graph.document.get_graph")
    @patch("neuron_server.graph.document.encode_md5")
    def test_import_chunks_success(
        self, mock_encode_md5: Mock, mock_get_graph: Mock
    ) -> None:
        """Test successful import of chunks."""
        # Setup mocks
        mock_encode_md5.side_effect = lambda x: f"md5_{x[:10]}"
        mock_graph = Mock()
        mock_get_graph.return_value = mock_graph

        # Prepare test data
        texts = ["chunk text 1", "chunk text 2"]
        extractions = [
            Extraction(
                description="Desc 1",
                atomic_facts=[
                    AtomicFact(
                        key_elements=["element1"],
                        atomic_fact="fact 1",
                    )
                ],
            ),
            Extraction(
                description="Desc 2",
                atomic_facts=[
                    AtomicFact(
                        key_elements=["element2"],
                        atomic_fact="fact 2",
                    )
                ],
            ),
        ]
        metadata = DocumentMetadata(
            document_id="doc123",
            document_name="Test Doc",
            personality_id="pers456",
            user_id="user789",
            source="test_source",
        )

        # Execute
        import_chunks(texts, extractions, metadata)

        # Verify
        assert mock_graph.query.call_count == 2  # noqa: PLR2004
        assert mock_graph.refresh_schema.called

        # Check first query params
        first_call_params = mock_graph.query.call_args_list[0][1]["params"]
        assert first_call_params["document_id"] == "doc123"
        assert first_call_params["document_name"] == "Test Doc"
        assert first_call_params["personality_id"] == "pers456"
        assert first_call_params["user_id"] == "user789"
        assert first_call_params["source"] == "test_source"
        assert len(first_call_params["data"]) == 2  # noqa: PLR2004

        # Check document data structure
        doc_data = first_call_params["data"][0]
        assert doc_data["chunk_id"] == "md5_chunk text"
        assert doc_data["chunk_text"] == "chunk text 1"
        assert doc_data["index"] == 0
        assert doc_data["atomic_facts"][0]["id"] == "md5_fact 1"

    @patch("neuron_server.graph.document.get_graph")
    def test_import_chunks_empty_lists(self, mock_get_graph: Mock) -> None:
        """Test import_chunks with empty lists."""
        mock_graph = Mock()
        mock_get_graph.return_value = mock_graph

        metadata = DocumentMetadata(document_id="doc123")

        # Execute with empty lists
        import_chunks([], [], metadata)

        # Verify queries were still made
        assert mock_graph.query.call_count == 2  # noqa: PLR2004
        assert mock_graph.refresh_schema.called


class TestProcessChunk:
    """Test cases for process_chunk function."""

    @pytest.mark.asyncio
    async def test_process_chunk_success(self) -> None:
        """Test successful chunk processing."""
        # Setup mock chain
        mock_extraction = Extraction(
            description="Test description",
            atomic_facts=[
                AtomicFact(
                    key_elements=["test"],
                    atomic_fact="test fact",
                )
            ],
        )

        with patch(
            "neuron_server.graph.document.construction_chain"
        ) as mock_chain:
            mock_chain.ainvoke = AsyncMock(return_value=mock_extraction)

            # Create semaphore
            semaphore = asyncio.Semaphore(1)

            # Execute
            result = await process_chunk(
                input_text="test chunk",
                index=0,
                config=None,
                semaphore=semaphore,
            )

            # Verify
            assert result == mock_extraction
            mock_chain.ainvoke.assert_called_once_with(
                "test chunk", config=None
            )

    @pytest.mark.asyncio
    async def test_process_chunk_with_retry(self) -> None:
        """Test chunk processing with retry on error."""
        mock_extraction = Extraction(
            description="Test description",
            atomic_facts=[],
        )

        with patch(
            "neuron_server.graph.document.construction_chain"
        ) as mock_chain:
            # First call fails, second succeeds
            mock_chain.ainvoke = AsyncMock(
                side_effect=[Exception("Test error"), mock_extraction]
            )

            semaphore = asyncio.Semaphore(1)
            chunk_config = ChunkConfig(retry_delay_seconds=0)

            # Execute
            result = await process_chunk(
                input_text="test chunk",
                index=0,
                config=None,
                semaphore=semaphore,
                chunk_config=chunk_config,
            )

            # Verify
            assert result == mock_extraction
            assert mock_chain.ainvoke.call_count == 2  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_process_chunk_max_retries_exceeded(self) -> None:
        """Test chunk processing when max retries are exceeded."""
        with patch(
            "neuron_server.graph.document.construction_chain"
        ) as mock_chain:
            mock_chain.ainvoke = AsyncMock(
                side_effect=Exception("Persistent error")
            )

            semaphore = asyncio.Semaphore(1)
            chunk_config = ChunkConfig(
                max_attempts=2, retry_delay_seconds=0
            )

            # Execute and expect exception
            with pytest.raises(Exception, match="Persistent error"):
                await process_chunk(
                    input_text="test chunk",
                    index=0,
                    config=None,
                    semaphore=semaphore,
                    chunk_config=chunk_config,
                )

            # Verify all attempts were made
            assert mock_chain.ainvoke.call_count == 2  # noqa: PLR2004


class TestProcessDocument:
    """Test cases for process_document function."""

    @pytest.mark.asyncio
    @patch("neuron_server.graph.document.import_chunks")
    @patch("neuron_server.graph.document.summary_chain")
    @patch("neuron_server.graph.document.construction_chain")
    @patch("neuron_server.graph.document.TokenTextSplitter")
    async def test_process_document_success(
        self,
        mock_text_splitter_class: Mock,
        mock_construction_chain: Mock,
        mock_summary_chain: Mock,
        mock_import_chunks: Mock,
    ) -> None:
        """Test successful document processing."""
        # Setup mocks
        mock_text_splitter = Mock()
        mock_text_splitter.split_text.return_value = [
            "chunk1",
            "chunk2",
        ]
        mock_text_splitter_class.return_value = mock_text_splitter

        mock_extraction1 = Extraction(
            description="Description 1",
            atomic_facts=[
                AtomicFact(
                    key_elements=["elem1"],
                    atomic_fact="fact1",
                )
            ],
        )
        mock_extraction2 = Extraction(
            description="Description 2",
            atomic_facts=[
                AtomicFact(
                    key_elements=["elem2"],
                    atomic_fact="fact2",
                )
            ],
        )
        mock_construction_chain.ainvoke = AsyncMock(
            side_effect=[mock_extraction1, mock_extraction2]
        )

        mock_summary = SummaryResponse(
            summary="Test summary",
            critical_analysis="Test analysis",
            keywords=["keyword1", "keyword2"],
        )
        mock_summary_chain.ainvoke = AsyncMock(return_value=mock_summary)

        # Prepare test data
        config = RunnableConfig(
            configurable={
                "personality_id": "pers123",
                "user_id": "user456",
            }
        )
        metadata = DocumentMetadata(
            document_id="doc789",
            document_name="Test Document",
            source="test_source",
        )

        # Execute
        result = await process_document(
            text="Test document text",
            config=config,
            metadata=metadata,
        )

        # Verify
        assert isinstance(result, DocumentResult)
        assert result.document_id == "doc789"
        assert result.document_name == "Test Document"
        assert result.source == "test_source"
        assert result.summary == "Test summary"
        assert result.analysis == "Test analysis"
        assert result.keywords == ["keyword1", "keyword2"]

        # Verify metadata was updated
        assert metadata.personality_id == "pers123"
        assert metadata.user_id == "user456"

        # Verify import_chunks was called
        mock_import_chunks.assert_called_once()
        import_args = mock_import_chunks.call_args[1]
        assert import_args["texts"] == ["chunk1", "chunk2"]
        assert len(import_args["extractions"]) == 2  # noqa: PLR2004
        assert import_args["metadata"] == metadata

        # Verify summary chain was called with descriptions
        summary_input = mock_summary_chain.ainvoke.call_args[0][0]
        assert summary_input["input"] == "Description 1\n\nDescription 2"

    @pytest.mark.asyncio
    async def test_process_document_missing_personality_id(self) -> None:
        """Test process_document with missing personality_id."""
        config = RunnableConfig(configurable={"user_id": "user456"})
        metadata = DocumentMetadata(document_id="doc789")

        with pytest.raises(AssertionError):
            await process_document(
                text="Test document",
                config=config,
                metadata=metadata,
            )

    @pytest.mark.asyncio
    async def test_process_document_missing_user_id(self) -> None:
        """Test process_document with missing user_id."""
        config = RunnableConfig(
            configurable={"personality_id": "pers123"}
        )
        metadata = DocumentMetadata(document_id="doc789")

        with pytest.raises(AssertionError):
            await process_document(
                text="Test document",
                config=config,
                metadata=metadata,
            )


class TestGetDocument:
    """Test cases for get_document function."""

    @patch("neuron_server.graph.document.get_graph")
    def test_get_document_found(self, mock_get_graph: Mock) -> None:
        """Test getting a document that exists."""
        mock_graph = Mock()
        mock_result = [
            {
                "document_id": "doc123",
                "document_name": "Test Doc",
                "chunk_id": "chunk1",
                "text": "chunk text",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        ]
        mock_graph.query.return_value = mock_result
        mock_get_graph.return_value = mock_graph

        # Execute
        result = get_document("doc123", "pers456")

        # Verify
        assert result == mock_result
        mock_graph.query.assert_called_once()
        query_params = mock_graph.query.call_args[1]["params"]
        assert query_params["id"] == "doc123"
        assert query_params["personality_id"] == "pers456"

    @patch("neuron_server.graph.document.get_graph")
    def test_get_document_not_found(self, mock_get_graph: Mock) -> None:
        """Test getting a document that doesn't exist."""
        mock_graph = Mock()
        mock_graph.query.return_value = []
        mock_get_graph.return_value = mock_graph

        # Execute
        result = get_document("nonexistent", "pers456")

        # Verify
        assert result is None

    @patch("neuron_server.graph.document.get_graph")
    def test_get_document_empty_result(self, mock_get_graph: Mock) -> None:
        """Test getting a document with empty result."""
        mock_graph = Mock()
        mock_graph.query.return_value = None
        mock_get_graph.return_value = mock_graph

        # Execute
        result = get_document("doc123", "pers456")

        # Verify
        assert result is None


class TestIntegration:
    """Integration tests for document processing."""

    @pytest.mark.asyncio
    @patch("neuron_server.graph.document.get_graph")
    @patch("neuron_server.graph.document.summary_chain")
    @patch("neuron_server.graph.document.construction_chain")
    async def test_end_to_end_document_processing(
        self,
        mock_construction_chain: Mock,
        mock_summary_chain: Mock,
        mock_get_graph: Mock,
    ) -> None:
        """Test complete document processing flow."""
        # Setup comprehensive mocks
        mock_graph = Mock()
        mock_get_graph.return_value = mock_graph

        # Mock construction chain to return extractions
        mock_extraction = Extraction(
            description="Test extraction",
            atomic_facts=[
                AtomicFact(
                    key_elements=["test", "element"],
                    atomic_fact="This is a test fact",
                )
            ],
        )
        mock_construction_chain.ainvoke = AsyncMock(
            return_value=mock_extraction
        )

        # Mock summary chain
        mock_summary = SummaryResponse(
            summary="Document summary",
            critical_analysis="Critical analysis",
            keywords=["test", "document"],
        )
        mock_summary_chain.ainvoke = AsyncMock(return_value=mock_summary)

        # Prepare test data
        test_document = """
        This is a test document with multiple paragraphs.

        It contains information that should be processed and stored in the graph.

        The document processing should handle chunking and extraction properly.
        """

        config = RunnableConfig(
            configurable={
                "personality_id": "test_personality",
                "user_id": "test_user",
            }
        )

        metadata = DocumentMetadata(
            document_id="test_doc_123",
            document_name="Integration Test Document",
            source="test_integration",
        )

        # Execute
        result = await process_document(
            text=test_document,
            config=config,
            metadata=metadata,
            chunk_config=ChunkConfig(chunk_size=100, chunk_overlap=20),
        )

        # Verify result
        assert isinstance(result, DocumentResult)
        assert result.document_id == "test_doc_123"
        assert result.document_name == "Integration Test Document"
        assert result.source == "test_integration"
        assert result.summary == "Document summary"
        assert result.analysis == "Critical analysis"
        assert result.keywords == ["test", "document"]

        # Verify graph operations
        assert mock_graph.query.call_count == 2  # noqa: PLR2004
        assert mock_graph.refresh_schema.called
