import builtins
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import JSONB

from neuron_server.database import MediaList, MediaListItem, get_session


class MediaListModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(description="Name of the media list")
    description: str = Field(description="Description of the media list")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    user_id: str = Field(description="ID of the user who owns this list")
    visibility: str = Field(default="private", description="Visibility setting")
    shared_with: list[str] = Field(
        default_factory=list, description="List of users this is shared with"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).astimezone()
    )

    @classmethod
    async def create(
        cls,
        name: str,
        description: str,
        user_id: str,
        tags: list[str] | None = None,
        visibility: str = "private",
        shared_with: list[str] | None = None,
        id: UUID | None = None,
    ) -> Self:
        async with get_session() as session:
            media_list = MediaList(
                id=id,
                name=name,
                description=description,
                tags=tags or [],
                user_id=user_id,
                visibility=visibility,
                shared_with=shared_with or [],
            )
            session.add(media_list)
            await session.commit()
            return cls(**media_list.__dict__)

    @classmethod
    async def get(cls, id: UUID) -> Self | None:
        async with get_session() as session:
            data = await session.get(MediaList, id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(cls) -> list[Self]:
        async with get_session() as session:
            results = await session.execute(select(MediaList))
            records = results.scalars().all()
            return [cls(**list_item.__dict__) for list_item in records]

    @staticmethod
    async def delete(id: UUID) -> None:
        async with get_session() as session:
            await session.delete(await session.get(MediaList, id))
            await session.commit()

    @classmethod
    async def update(
        cls,
        id: UUID,
        name: str,
        description: str,
        tags: builtins.list[str],
        visibility: str,
        shared_with: builtins.list[str],
    ) -> Self:
        async with get_session() as session:
            media_list = await session.get(MediaList, id)
            media_list.name = name
            media_list.description = description
            media_list.tags = tags
            media_list.visibility = visibility
            media_list.shared_with = shared_with
            session.add(media_list)
            await session.commit()
            return cls(**media_list.__dict__)

    async def save(self) -> None:
        async with get_session() as session:
            media_list = await session.get(MediaList, self.id)
            media_list.name = self.name
            media_list.description = self.description
            media_list.tags = self.tags
            media_list.visibility = self.visibility
            media_list.shared_with = self.shared_with
            await session.commit()

    @classmethod
    async def list_for_user(cls, user_id: str) -> builtins.list[Self]:
        """Get all media lists owned by or shared with the user"""
        async with get_session() as session:
            query = select(MediaList).where(
                (MediaList.user_id == user_id)
                | MediaList.shared_with.cast(JSONB).contains([user_id])
            )
            results = await session.execute(query)
            records = results.scalars().all()
            return [cls(**list_item.__dict__) for list_item in records]

    @classmethod
    async def get_max_index(cls, list_id: UUID) -> int | None:
        """Get the highest index currently used in the media list"""
        async with get_session() as session:
            result = await session.execute(
                select(func.max(MediaListItem.index)).where(
                    MediaListItem.media_list_id == list_id
                )
            )
            return result.scalar()

    @classmethod
    async def add_media_item(
        cls, list_id: UUID, media_item_id: UUID, index: int
    ) -> MediaListItem:
        """Add a media item to the list at the specified index"""
        async with get_session() as session:
            media_list_item = MediaListItem(
                media_list_id=list_id, media_item_id=media_item_id, index=index
            )
            session.add(media_list_item)
            await session.commit()
            return media_list_item
