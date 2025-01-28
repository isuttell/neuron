import builtins
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from neuron_server.database import (
    LangchainPGCollection,
    LangchainPGEmbedding,
    get_session,
)


class EmbeddingModel(BaseModel):
    id: str = Field(description="The ID of the embedding")
    collection_id: UUID | None = Field(
        description="The collection ID associated with the embedding"
    )
    collection_name: str | None = Field(
        description="The name of the collection this embedding belongs to", default=None
    )
    embedding: list[float] | None = Field(
        description="The vector representation of the embedding"
    )
    document: str | None = Field(
        description="The document associated with the embedding"
    )
    cmetadata: dict | None = Field(
        description="Custom metadata associated with the embedding"
    )

    @classmethod
    async def create(
        cls,
        id: str,
        collection_id: UUID | None = None,
        embedding: list[float] | None = None,
        document: str | None = None,
        cmetadata: dict | None = None,
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
        collection_id: UUID | None = None,
        embedding: list[float] | None = None,
        document: str | None = None,
        cmetadata: dict | None = None,
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
    async def get(cls, id: str) -> Self | None:
        async with get_session() as session:
            data = await session.get(LangchainPGEmbedding, id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(cls, collection_id: UUID) -> list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(
                    LangchainPGEmbedding.id,
                    LangchainPGEmbedding.collection_id,
                    LangchainPGEmbedding.embedding,
                    LangchainPGEmbedding.document,
                    LangchainPGEmbedding.cmetadata,
                    LangchainPGCollection.name.label("collection_name"),
                )
                .join(
                    LangchainPGCollection,
                    LangchainPGEmbedding.collection_id == LangchainPGCollection.uuid,
                    isouter=True,
                )
                .where(LangchainPGEmbedding.collection_id == collection_id)
            )
            embeddings = []
            for row in results.all():
                embedding_dict = {
                    "id": row.id,
                    "collection_id": row.collection_id,
                    "embedding": row.embedding,
                    "document": row.document,
                    "cmetadata": row.cmetadata,
                    "collection_name": row.collection_name,
                }
                embeddings.append(cls(**embedding_dict))
            return embeddings

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

    @classmethod
    async def filter_by_metadata(cls, key: str, value: str) -> builtins.list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(
                    LangchainPGEmbedding.id,
                    LangchainPGEmbedding.collection_id,
                    LangchainPGEmbedding.embedding,
                    LangchainPGEmbedding.document,
                    LangchainPGEmbedding.cmetadata,
                    LangchainPGCollection.name.label("collection_name"),
                )
                .join(
                    LangchainPGCollection,
                    LangchainPGEmbedding.collection_id == LangchainPGCollection.uuid,
                    isouter=True,
                )
                .where(
                    func.jsonb_extract_path_text(LangchainPGEmbedding.cmetadata, key)
                    == str(value)
                )
            )
            embeddings = []
            for row in results.all():
                embedding_dict = {
                    "id": row.id,
                    "collection_id": row.collection_id,
                    "embedding": row.embedding,
                    "document": row.document,
                    "cmetadata": row.cmetadata,
                    "collection_name": row.collection_name,
                }
                embeddings.append(cls(**embedding_dict))
            return embeddings

    @staticmethod
    async def delete(id: str) -> None:
        async with get_session() as session:
            embedding_instance = await session.get(LangchainPGEmbedding, id)
            await session.delete(embedding_instance)
            await session.commit()

    @classmethod
    async def get_many(cls, ids: builtins.list[str]) -> builtins.list[Self]:
        """Get multiple embeddings by their IDs.

        Args:
            ids: List of embedding IDs to retrieve

        Returns:
            List of found embeddings
        """
        async with get_session() as session:
            results = await session.execute(
                select(
                    LangchainPGEmbedding.id,
                    LangchainPGEmbedding.collection_id,
                    LangchainPGEmbedding.embedding,
                    LangchainPGEmbedding.document,
                    LangchainPGEmbedding.cmetadata,
                    LangchainPGCollection.name.label("collection_name"),
                )
                .join(
                    LangchainPGCollection,
                    LangchainPGEmbedding.collection_id == LangchainPGCollection.uuid,
                    isouter=True,
                )
                .where(LangchainPGEmbedding.id.in_(ids))
            )

            embeddings = []
            for row in results.all():
                embedding_dict = {
                    "id": row.id,
                    "collection_id": row.collection_id,
                    "embedding": row.embedding,
                    "document": row.document,
                    "cmetadata": row.cmetadata,
                    "collection_name": row.collection_name,
                }
                embeddings.append(cls(**embedding_dict))
            return embeddings

    @classmethod
    async def delete_many(cls, ids: builtins.list[str]) -> None:
        """Delete multiple embeddings by their IDs.

        Args:
            ids: List of embedding IDs to delete
        """
        async with get_session() as session:
            await session.execute(
                LangchainPGEmbedding.__table__.delete().where(
                    LangchainPGEmbedding.id.in_(ids)
                )
            )
            await session.commit()
