import builtins
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select

from neuron_server.database import MediaListItem, get_session


class MediaListItemModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    media_list_id: UUID = Field(description="ID of the parent media list")
    media_item_id: UUID = Field(description="ID of the associated media item")
    index: int = Field(description="Index of the media item in the list")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @dataclass
    class CreateParams:
        media_list_id: UUID
        media_item_id: UUID
        index: int
        item_id: UUID | None = None

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        async with get_session() as session:
            media_list_item = MediaListItem(
                id=params.item_id,
                media_list_id=params.media_list_id,
                media_item_id=params.media_item_id,
                index=params.index,
            )
            session.add(media_list_item)
            await session.commit()
            return cls(**media_list_item.__dict__)

    @staticmethod
    async def delete(item_id: UUID) -> None:
        async with get_session() as session:
            await session.delete(await session.get(MediaListItem, item_id))
            await session.commit()

    @dataclass
    class UpdateParams:
        item_id: UUID
        index: int
        media_list_id: UUID
        media_item_id: UUID

    @classmethod
    async def update(cls, params: UpdateParams) -> Self:
        async with get_session() as session:
            media_list_item = await session.get(MediaListItem, params.item_id)
            media_list_item.index = params.index
            media_list_item.media_list_id = params.media_list_id
            media_list_item.media_item_id = params.media_item_id
            session.add(media_list_item)
            await session.commit()
            return cls(**media_list_item.__dict__)

    @classmethod
    async def list(cls) -> list[Self]:
        async with get_session() as session:
            results = await session.execute(select(MediaListItem))
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def get(cls, item_id: UUID) -> Self | None:
        async with get_session() as session:
            data = await session.get(MediaListItem, item_id)
            if data:
                return cls(**data.__dict__)
            return None

    async def save(self) -> None:
        async with get_session() as session:
            media_list_item = await session.get(MediaListItem, self.id)
            media_list_item.index = self.index
            media_list_item.media_list_id = self.media_list_id
            media_list_item.media_item_id = self.media_item_id
            await session.commit()

    @classmethod
    async def get_many(cls, ids: builtins.list[UUID]) -> builtins.list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(MediaListItem).where(MediaListItem.id.in_(ids))
            )
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def get_by_media_list(cls, media_list_id: UUID) -> builtins.list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(MediaListItem).where(
                    MediaListItem.media_list_id == media_list_id
                )
            )
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def get_by_media_item(cls, media_item_id: UUID) -> builtins.list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(MediaListItem).where(
                    MediaListItem.media_item_id == media_item_id
                )
            )
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def get_by_list(cls, list_id: UUID) -> builtins.list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(MediaListItem)
                .where(MediaListItem.media_list_id == list_id)
                .order_by(MediaListItem.index)
            )
            return [cls(**item.__dict__) for item in results.scalars().all()]
