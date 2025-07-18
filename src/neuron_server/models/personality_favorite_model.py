from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import select

from neuron_server.database import PersonalityFavorite, get_session


class PersonalityFavoriteModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    personality_id: UUID = Field(description="The ID of the personality")
    user_id: str = Field(description="The ID of the user")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @field_serializer("created_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @dataclass
    class CreateParams:
        personality_id: UUID
        user_id: str

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        """Create a new personality favorite.

        Args:
            params: Parameters for creating the personality favorite

        Returns:
            The created PersonalityFavoriteModel instance
        """
        async with get_session() as session:
            favorite = PersonalityFavorite(
                personality_id=params.personality_id,
                user_id=params.user_id,
            )
            session.add(favorite)
            await session.commit()
            return cls(**favorite.__dict__)

    @classmethod
    async def get_user_favorites(cls, user_id: str) -> list[Self]:
        """Get all personality favorites for a user.

        Args:
            user_id: The ID of the user to get favorites for

        Returns:
            List of PersonalityFavoriteModel instances for the user
        """
        async with get_session() as session:
            stmt = select(PersonalityFavorite).where(
                PersonalityFavorite.user_id == user_id
            )
            result = await session.execute(stmt)
            return [cls(**favorite.__dict__) for favorite in result.scalars().all()]

    @classmethod
    async def get_personality_favorites(cls, personality_id: UUID) -> list[Self]:
        """Get all users who have favorited a personality.

        Args:
            personality_id: The ID of the personality to get favorites for

        Returns:
            List of PersonalityFavoriteModel instances for the personality
        """
        async with get_session() as session:
            stmt = select(PersonalityFavorite).where(
                PersonalityFavorite.personality_id == personality_id
            )
            result = await session.execute(stmt)
            return [cls(**favorite.__dict__) for favorite in result.scalars().all()]

    @classmethod
    async def get(cls, personality_id: UUID, user_id: str) -> Self | None:
        """Get a specific personality favorite.

        Args:
            personality_id: The ID of the personality
            user_id: The ID of the user

        Returns:
            The PersonalityFavoriteModel instance if found, None otherwise
        """
        async with get_session() as session:
            stmt = select(PersonalityFavorite).where(
                PersonalityFavorite.personality_id == personality_id,
                PersonalityFavorite.user_id == user_id,
            )
            result = await session.execute(stmt)
            favorite = result.scalars().first()
            if favorite:
                return cls(**favorite.__dict__)
            return None

    @classmethod
    async def delete(cls, personality_id: UUID, user_id: str) -> None:
        """Remove a personality favorite.

        Args:
            personality_id: The ID of the personality
            user_id: The ID of the user
        """
        async with get_session() as session:
            stmt = select(PersonalityFavorite).where(
                PersonalityFavorite.personality_id == personality_id,
                PersonalityFavorite.user_id == user_id,
            )
            result = await session.execute(stmt)
            favorite = result.scalars().first()
            if favorite:
                await session.delete(favorite)
                await session.commit()

    @classmethod
    async def is_favorite(cls, personality_id: UUID, user_id: str) -> bool:
        """Check if a personality is favorited by a user.

        Args:
            personality_id: The ID of the personality
            user_id: The ID of the user

        Returns:
            True if the personality is favorited by the user, False otherwise
        """
        favorite = await cls.get(personality_id, user_id)
        return favorite is not None

    @classmethod
    async def toggle_favorite(cls, personality_id: UUID, user_id: str) -> bool:
        """Toggle a personality favorite for a user.

        Args:
            personality_id: The ID of the personality
            user_id: The ID of the user

        Returns:
            True if the personality was favorited, False if it was unfavorited
        """
        existing_favorite = await cls.get(personality_id, user_id)
        if existing_favorite:
            await cls.delete(personality_id, user_id)
            return False
        await cls.create(
            cls.CreateParams(personality_id=personality_id, user_id=user_id)
        )
        return True
