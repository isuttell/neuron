from uuid import UUID
from typing import List, Optional
from neuron_server.database import get_session, LangchainPGEmbedding
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone
from typing import Literal, Self, Any
from pydantic import field_serializer
from sqlalchemy import select


class EmbeddingModel(BaseModel):
    id: str = Field(description="The ID of the embedding")
    collection_id: Optional[UUID] = Field(
        description="The collection ID associated with the embedding"
    )
    embedding: Optional[List[float]] = Field(
        description="The vector representation of the embedding"
    )
    document: Optional[str] = Field(
        description="The document associated with the embedding"
    )
    cmetadata: Optional[dict] = Field(
        description="Custom metadata associated with the embedding"
    )

    @classmethod
    async def create(
        cls,
        id: str,
        collection_id: Optional[UUID] = None,
        embedding: Optional[List[float]] = None,
        document: Optional[str] = None,
        cmetadata: Optional[dict] = None,
    ) -> Self:
        async with get_session() as session:
            embedding_instance = LangchainPGEmbedding(
                id=id,
                collection_id=collection_id,
                embedding=embedding,
                document=document,
                cmetadata=cmetadata,
            )
            session.add(embedding_instance)
            await session.commit()
            return cls(**embedding_instance.__dict__)

    @staticmethod
    async def delete(id: str) -> None:
        async with get_session() as session:
            await session.delete(await session.get(LangchainPGEmbedding, id))
            await session.commit()

    @classmethod
    async def update(
        cls,
        id: str,
        collection_id: Optional[UUID] = None,
        embedding: Optional[List[float]] = None,
        document: Optional[str] = None,
        cmetadata: Optional[dict] = None,
    ) -> Self:
        async with get_session() as session:
            embedding_instance = await session.get(LangchainPGEmbedding, id)
            if collection_id is not None:
                embedding_instance.collection_id = collection_id
            if embedding is not None:
                embedding_instance.embedding = embedding
            if document is not None:
                embedding_instance.document = document
            if cmetadata is not None:
                embedding_instance.cmetadata = cmetadata
            await session.commit()
            return cls(**embedding_instance.__dict__)

    @classmethod
    async def get(cls, id: str) -> Optional[Self]:
        async with get_session() as session:
            data = await session.get(LangchainPGEmbedding, id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(cls, collection_id: UUID) -> List[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(LangchainPGEmbedding).where(
                    LangchainPGEmbedding.collection_id == collection_id
                )
            )
            return [cls(**embedding.__dict__) for embedding in results.scalars().all()]

    async def save(self) -> None:
        async with get_session() as session:
            embedding_instance = await session.get(LangchainPGEmbedding, self.id)
            embedding_instance.collection_id = self.collection_id
            embedding_instance.embedding = self.embedding
            embedding_instance.document = self.document
            embedding_instance.cmetadata = self.cmetadata
            await session.commit()

    @classmethod
    async def set(cls, id: str, key: str, value: Any) -> Self:
        async with get_session() as session:
            embedding_instance = await session.get(LangchainPGEmbedding, id)
            if not embedding_instance:
                raise ValueError("Embedding not found")
            setattr(embedding_instance, key, value)
            session.add(embedding_instance)
            await session.commit()
            return cls(**embedding_instance.__dict__)
