from uuid import UUID
from neuron_server.database import get_session, MediaItem
from typing import Optional, List, Self
from sqlalchemy import select, desc
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone
from sqlalchemy import and_
from neuron_server.pubsub import pubsub
from neuron_server.controllers.events.media_events import MediaEvent


class MediaItemModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(default="", description="Name of the media item")
    description: str = Field(default="", description="Description of the media item")
    url: str = Field(description="URL where the media is stored")
    type: str = Field(description="Type of media (image, video, audio, etc)")
    thread_id: Optional[UUID] = Field(description="Associated thread ID", default=None)
    user_id: str = Field(description="ID of the user who owns this media")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )

    @classmethod
    async def create(
        cls,
        url: str,
        type: str,
        user_id: str,
        name: str = "",
        description: str = "",
        thread_id: Optional[UUID] = None,
        id: Optional[UUID] = None,
    ) -> Self:
        async with get_session() as session:
            media_item = MediaItem(
                id=id,
                name=name,
                description=description,
                url=url,
                type=type,
                thread_id=thread_id,
                user_id=user_id,
            )
            session.add(media_item)
            await session.commit()
            result = cls(**media_item.__dict__)
            await pubsub.publish("app", MediaEvent(media=[result]))
            return result

    @classmethod
    async def get(cls, id: UUID) -> Optional[Self]:
        async with get_session() as session:
            data = await session.get(MediaItem, id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(cls) -> List[Self]:
        async with get_session() as session:
            results = await session.execute(select(MediaItem))
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]

    @classmethod
    async def get_recent(
        cls, user_id: str, limit: int = 20, offset: int = 0
    ) -> List[Self]:
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
    async def get_thread_media(cls, thread_id: UUID, user_id: str) -> List[Self]:
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
    async def get_many(cls, ids: List[UUID]) -> List[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(MediaItem).where(MediaItem.id.in_(ids))
            )
            records = results.scalars().all()
            return [cls(**item.__dict__) for item in records]
