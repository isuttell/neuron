import builtins
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select

from neuron_server.controllers.events.media_events import MediaEvent
from neuron_server.database import MediaItem, get_session
from neuron_server.secure_pubsub import secure_pubsub


class MediaItemModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(default="", description="Name of the media item")
    description: str = Field(default="", description="Description of the media item")
    url: str = Field(description="URL where the media is stored")
    media_type: str = Field(description="Type of media (image, video, audio, etc)")
    thread_id: UUID | None = Field(description="Associated thread ID", default=None)
    user_id: str = Field(description="ID of the user who owns this media")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @dataclass
    class CreateParams:
        url: str
        media_type: str
        user_id: str
        name: str = ""
        description: str = ""
        thread_id: UUID | None = None
        media_id: UUID | None = None

    @dataclass
    class UpdateParams:
        media_id: UUID
        name: str | None = None
        description: str | None = None

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        async with get_session() as session:
            media_item = MediaItem(
                id=params.media_id,
                name=params.name,
                description=params.description,
                url=params.url,
                media_type=params.media_type,
                thread_id=params.thread_id,
                user_id=params.user_id,
            )
            session.add(media_item)
            await session.commit()
            result = cls(**media_item.__dict__)
            await secure_pubsub.publish_media_event(MediaEvent(media=[result]))
            return result

    @classmethod
    async def update(cls, params: UpdateParams) -> Self | None:
        """Update a media item's name and/or description."""
        async with get_session() as session:
            media_item = await session.get(MediaItem, params.media_id)
            if not media_item:
                return None
            if params.name is not None:
                media_item.name = params.name
            if params.description is not None:
                media_item.description = params.description
            session.add(media_item)
            await session.commit()
            result = cls(**media_item.__dict__)
            await secure_pubsub.publish_media_event(MediaEvent(media=[result]))
            return result

    @classmethod
    async def get(cls, media_id: UUID) -> Self | None:
        async with get_session() as session:
            data = await session.get(MediaItem, media_id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(cls) -> list[Self]:
        async with get_session() as session:
            results = await session.execute(select(MediaItem))
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def get_recent(
        cls, user_id: str, limit: int = 20, offset: int = 0
    ) -> builtins.list[Self]:
        """
        Get recent media items for a user with pagination support.

        Args:
            user_id: The ID of the user
            limit: Maximum number of items to return
            offset: Number of items to skip

        Returns:
            List of MediaItemModel instances
        """
        async with get_session() as session:
            query = (
                select(MediaItem)
                .where(MediaItem.user_id == user_id)
                .order_by(desc(MediaItem.created_at))
                .limit(limit)
                .offset(offset)
            )
            results = await session.execute(query)
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def get_thread_media(
        cls, thread_id: UUID, user_id: str
    ) -> builtins.list[Self]:
        """
        Get media items for a specific thread and user.

        Args:
            thread_id: The ID of the thread
            user_id: The ID of the user

        Returns:
            List of MediaItemModel instances
        """
        async with get_session() as session:
            query = (
                select(MediaItem)
                .where(
                    and_(MediaItem.thread_id == thread_id, MediaItem.user_id == user_id)
                )
                .order_by(desc(MediaItem.created_at))
            )
            results = await session.execute(query)
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def get_many(cls, ids: builtins.list[UUID]) -> builtins.list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(MediaItem).where(MediaItem.id.in_(ids))
            )
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]
