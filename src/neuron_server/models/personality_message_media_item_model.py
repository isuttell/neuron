from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import and_, select

from neuron_server.database import MediaItem, PersonalityMessageMediaItem, get_session
from neuron_server.models.media_item_model import MediaItemModel


class PersonalityMessageMediaItemModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    personality_message_id: UUID = Field(
        description="The ID of the personality message"
    )
    media_item_id: UUID = Field(description="The ID of the media item")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @dataclass
    class CreateParams:
        personality_message_id: UUID
        media_item_id: UUID

    @classmethod
    async def create_association(cls, params: CreateParams) -> Self:
        """Create an association between a personality message and media item."""
        async with get_session() as session:
            association = PersonalityMessageMediaItem(
                personality_message_id=params.personality_message_id,
                media_item_id=params.media_item_id,
            )
            session.add(association)
            await session.commit()
            return cls(**association.__dict__)

    @classmethod
    async def get_media_for_message(
        cls, personality_message_id: UUID
    ) -> list[MediaItemModel]:
        """Get all media items associated with a personality message."""
        async with get_session() as session:
            # Join with media_items to get the full MediaItem data
            query = (
                select(MediaItem)
                .select_from(PersonalityMessageMediaItem)
                .join(
                    MediaItem, PersonalityMessageMediaItem.media_item_id == MediaItem.id
                )
                .where(
                    PersonalityMessageMediaItem.personality_message_id
                    == personality_message_id
                )
                .order_by(PersonalityMessageMediaItem.created_at)
            )
            results = await session.execute(query)
            records = results.scalars().all()
            return [MediaItemModel(**item.__dict__) for item in records]

    @classmethod
    async def delete_associations_for_message(
        cls, personality_message_id: UUID
    ) -> None:
        """Delete all media item associations for a personality message."""
        async with get_session() as session:
            query = select(PersonalityMessageMediaItem).where(
                PersonalityMessageMediaItem.personality_message_id
                == personality_message_id
            )
            results = await session.execute(query)
            associations = results.scalars().all()

            for association in associations:
                await session.delete(association)

            await session.commit()

    @classmethod
    async def get_associations_for_message(
        cls, personality_message_id: UUID
    ) -> list[Self]:
        """Get all associations for a personality message."""
        async with get_session() as session:
            query = select(PersonalityMessageMediaItem).where(
                PersonalityMessageMediaItem.personality_message_id
                == personality_message_id
            )
            results = await session.execute(query)
            records = results.scalars().all()
            return [cls(**record.__dict__) for record in records]

    @classmethod
    async def association_exists(
        cls, personality_message_id: UUID, media_item_id: UUID
    ) -> bool:
        """Check if an association already exists."""
        async with get_session() as session:
            query = select(PersonalityMessageMediaItem).where(
                and_(
                    PersonalityMessageMediaItem.personality_message_id
                    == personality_message_id,
                    PersonalityMessageMediaItem.media_item_id == media_item_id,
                )
            )
            result = await session.execute(query)
            return result.scalar() is not None

    @classmethod
    async def delete_association(
        cls, personality_message_id: UUID, media_item_id: UUID
    ) -> bool:
        """Delete a specific association. Returns True if found and deleted."""
        async with get_session() as session:
            query = select(PersonalityMessageMediaItem).where(
                and_(
                    PersonalityMessageMediaItem.personality_message_id
                    == personality_message_id,
                    PersonalityMessageMediaItem.media_item_id == media_item_id,
                )
            )
            result = await session.execute(query)
            association = result.scalar()

            if association:
                await session.delete(association)
                await session.commit()
                return True
            return False
