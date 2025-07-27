from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from neuron_server.database import PersonalityMessage, get_session


class PersonalityMessageModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    personality_id: UUID = Field(description="The ID of the personality")
    user_id: str | None = Field(
        default=None, description="The user ID or None if personality is responding"
    )
    content: str = Field(description="The content of the message")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @dataclass
    class CreateParams:
        personality_id: UUID
        content: str
        user_id: str | None = None
        message_id: UUID | None = None

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        """Create a new personality message."""
        async with get_session() as session:
            new_message = PersonalityMessage(
                id=params.message_id or uuid4(),
                personality_id=params.personality_id,
                user_id=params.user_id,
                content=params.content,
            )
            session.add(new_message)
            await session.commit()
            return cls(**new_message.__dict__)

    @dataclass
    class UpsertParams:
        personality_id: UUID
        content: str
        user_id: str | None = None
        message_id: UUID | None = None

    @classmethod
    async def upsert(cls, params: UpsertParams) -> Self:
        """Upsert a personality message."""
        async with get_session() as session:
            stmt = (
                pg_insert(PersonalityMessage)
                .values(
                    id=params.message_id or uuid4(),
                    personality_id=params.personality_id,
                    user_id=params.user_id,
                    content=params.content,
                )
                .on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "content": params.content,
                        "user_id": params.user_id,
                    },
                )
                .returning(PersonalityMessage)
            )
            result = await session.execute(stmt)
            await session.commit()
            return cls(**result.scalar_one().__dict__)

    @classmethod
    async def list(
        cls, personality_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Self]:
        """List messages for a personality."""
        async with get_session() as session:
            result = await session.execute(
                select(PersonalityMessage)
                .where(PersonalityMessage.personality_id == personality_id)
                .order_by(PersonalityMessage.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            return [cls(**message.__dict__) for message in result.scalars().all()]

    @classmethod
    async def get(cls, message_id: UUID) -> Self | None:
        """Get a personality message by ID."""
        async with get_session() as session:
            data = await session.get(PersonalityMessage, message_id)
            if data:
                return cls(**data.__dict__)
            return None

    @staticmethod
    async def delete(message_id: UUID) -> None:
        """Delete a personality message."""
        async with get_session() as session:
            message = await session.get(PersonalityMessage, message_id)
            if message:
                await session.delete(message)
                await session.commit()

    @dataclass
    class UpdateParams:
        message_id: UUID
        content: str

    @classmethod
    async def update(cls, params: UpdateParams) -> Self | None:
        """Update a personality message's content."""
        async with get_session() as session:
            message = await session.get(PersonalityMessage, params.message_id)
            if not message:
                return None
            message.content = params.content
            session.add(message)
            await session.commit()
            return cls(**message.__dict__)

    @classmethod
    async def get_with_media_items(cls, message_id: UUID) -> tuple[Self | None, list]:
        """Get a personality message with its associated media items."""
        from neuron_server.models.personality_message_media_item_model import (
            PersonalityMessageMediaItemModel,
        )

        message = await cls.get(message_id)
        if not message:
            return None, []

        media_items = await PersonalityMessageMediaItemModel.get_media_for_message(
            message_id
        )
        return message, media_items

    @classmethod
    async def associate_media_items(
        cls, message_id: UUID, media_item_ids: list[UUID]
    ) -> list:
        """Associate media items with a personality message."""
        from neuron_server.models.personality_message_media_item_model import (
            PersonalityMessageMediaItemModel,
        )

        associations = []
        for media_item_id in media_item_ids:
            # Check if association already exists to avoid duplicates
            if not await PersonalityMessageMediaItemModel.association_exists(
                message_id, media_item_id
            ):
                params = PersonalityMessageMediaItemModel.CreateParams(
                    personality_message_id=message_id, media_item_id=media_item_id
                )
                association = await PersonalityMessageMediaItemModel.create_association(
                    params
                )
                associations.append(association)
        return associations
