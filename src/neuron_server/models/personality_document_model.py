from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field
from sqlalchemy import select

from neuron_server.database import PersonalityDocument, get_session
from neuron_server.logger import logger
from neuron_server.models.embedding_model import EmbeddingModel
from neuron_server.vectorstores import memories_store


class PersonalityDocumentModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    personality_id: UUID = Field(description="Associated personality ID")
    user_id: str = Field(description="ID of the user who uploaded this document")
    name: str = Field(description="Name of the document")
    content: str = Field(description="Full content of the document")
    doc_metadata: dict = Field(default_factory=dict, description="Document metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @dataclass
    class CreateParams:
        personality_id: UUID
        user_id: str
        name: str
        content: str

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        """Create a new personality document and add its chunks to memory."""
        async with get_session() as session:
            # Create the document record
            document = PersonalityDocument(
                personality_id=params.personality_id,
                user_id=params.user_id,
                name=params.name,
                content=params.content,
                doc_metadata={},
            )
            session.add(document)
            await session.commit()

            # Split the document into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                is_separator_regex=False,
            )
            chunks = text_splitter.split_text(params.content)

            # Add chunks to memory with document metadata
            chunk_ids = []
            documents = []

            for i, chunk in enumerate(chunks):
                chunk_id = str(uuid4())
                chunk_ids.append(chunk_id)

                metadata = {
                    "personality_id": str(params.personality_id),
                    "document_id": str(document.id),
                    "document_name": params.name,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "user_id": params.user_id,
                    "source": "personality_document",
                    "created_at": int(datetime.now(UTC).timestamp()),
                }

                doc = Document(page_content=chunk, id=chunk_id, metadata=metadata)
                documents.append(doc)

            # Add all documents at once for better performance
            await memories_store.aadd_documents(documents)

            # Update document metadata with chunk IDs
            document.doc_metadata = {"chunk_ids": chunk_ids}
            await session.commit()

            logger.info(
                "Created personality document '%s' with %d chunks for personality %s",
                params.name,
                len(chunks),
                params.personality_id,
            )

            return cls(**document.__dict__)

    @classmethod
    async def get(cls, document_id: UUID) -> Self | None:
        """Get a personality document by ID."""
        async with get_session() as session:
            data = await session.get(PersonalityDocument, document_id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(cls, personality_id: UUID) -> list[Self]:
        """List all documents for a personality."""
        async with get_session() as session:
            results = await session.execute(
                select(PersonalityDocument)
                .where(PersonalityDocument.personality_id == personality_id)
                .order_by(PersonalityDocument.created_at.desc())
            )
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def delete(cls, document_id: UUID) -> None:
        """Delete a personality document and all its associated memory chunks."""
        async with get_session() as session:
            document = await session.get(PersonalityDocument, document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Get chunk IDs from metadata
            chunk_ids = document.doc_metadata.get("chunk_ids", [])

            if chunk_ids:
                # Delete all chunks from the embedding store
                await EmbeddingModel.delete_many(chunk_ids)
                logger.info(
                    "Deleted %d memory chunks for document %s",
                    len(chunk_ids),
                    document_id,
                )

            # Delete the document record
            await session.delete(document)
            await session.commit()

            logger.info("Deleted personality document %s", document_id)

    @classmethod
    async def get_by_personality_and_id(
        cls, personality_id: UUID, document_id: UUID
    ) -> Self | None:
        """Get a document that belongs to a specific personality."""
        async with get_session() as session:
            results = await session.execute(
                select(PersonalityDocument).where(
                    PersonalityDocument.id == document_id,
                    PersonalityDocument.personality_id == personality_id,
                )
            )
            data = results.scalar_one_or_none()
            if data:
                return cls(**data.__dict__)
            return None
