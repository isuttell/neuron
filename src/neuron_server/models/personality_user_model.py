from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import select

from neuron_server.database import PersonalityUser, get_session


class PersonalityUserModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    personality_id: UUID = Field(description="The ID of the personality")
    user_id: str = Field(description="The ID of the user")
    role: str = Field(
        description="The user's role for this personality", default="user"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @dataclass
    class CreateParams:
        personality_id: UUID
        user_id: str
        role: str = "user"

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        """Create a new personality user association.

        Args:
            params: Parameters for creating the personality user association

        Returns:
            The created PersonalityUserModel instance
        """
        async with get_session() as session:
            personality_user = PersonalityUser(
                personality_id=params.personality_id,
                user_id=params.user_id,
                role=params.role,
            )
            session.add(personality_user)
            await session.commit()
            return cls(**personality_user.__dict__)

    @classmethod
    async def get_personality_users(cls, personality_id: UUID) -> list[Self]:
        """Get all users associated with a personality.

        Args:
            personality_id: The ID of the personality to get users for

        Returns:
            List of PersonalityUserModel instances for the personality
        """
        async with get_session() as session:
            stmt = select(PersonalityUser).where(
                PersonalityUser.personality_id == personality_id
            )
            result = await session.execute(stmt)
            return [
                cls(**personality_user.__dict__)
                for personality_user in result.scalars().all()
            ]

    @classmethod
    async def get_user_personalities(cls, user_id: str) -> list[Self]:
        """Get all personalities a user has access to.

        Args:
            user_id: The ID of the user to get personalities for

        Returns:
            List of PersonalityUserModel instances for the user
        """
        async with get_session() as session:
            stmt = select(PersonalityUser).where(PersonalityUser.user_id == user_id)
            result = await session.execute(stmt)
            return [
                cls(**personality_user.__dict__)
                for personality_user in result.scalars().all()
            ]

    @classmethod
    async def get(cls, personality_id: UUID, user_id: str) -> Self | None:
        """Get a specific personality user association.

        Args:
            personality_id: The ID of the personality
            user_id: The ID of the user

        Returns:
            The PersonalityUserModel instance if found, None otherwise
        """
        async with get_session() as session:
            stmt = select(PersonalityUser).where(
                PersonalityUser.personality_id == personality_id,
                PersonalityUser.user_id == user_id,
            )
            result = await session.execute(stmt)
            personality_user = result.scalars().first()
            if personality_user:
                return cls(**personality_user.__dict__)
            return None

    @classmethod
    async def delete(cls, personality_id: UUID, user_id: str) -> None:
        """Remove a user from a personality.

        Args:
            personality_id: The ID of the personality
            user_id: The ID of the user to remove
        """
        async with get_session() as session:
            stmt = select(PersonalityUser).where(
                PersonalityUser.personality_id == personality_id,
                PersonalityUser.user_id == user_id,
            )
            result = await session.execute(stmt)
            personality_user = result.scalars().first()
            if personality_user:
                await session.delete(personality_user)
                await session.commit()

    @classmethod
    async def update_role(cls, personality_id: UUID, user_id: str, role: str) -> Self:
        """Update a user's role for a personality.

        Args:
            personality_id: The ID of the personality
            user_id: The ID of the user
            role: The new role for the user

        Returns:
            The updated PersonalityUserModel instance

        Raises:
            ValueError: If the personality user association is not found
        """
        async with get_session() as session:
            stmt = select(PersonalityUser).where(
                PersonalityUser.personality_id == personality_id,
                PersonalityUser.user_id == user_id,
            )
            result = await session.execute(stmt)
            personality_user = result.scalars().first()
            if personality_user:
                personality_user.role = role
                await session.commit()
                return cls(**personality_user.__dict__)
            raise ValueError("PersonalityUser not found")
