from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import select

from neuron_server.database import PersonalityRoomUser, get_session


class PersonalityRoomUserModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    personality_room_id: UUID = Field(description="The ID of the personality room")
    user_id: str = Field(description="The ID of the user")
    role: str = Field(description="The user's role in this room", default="user")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @dataclass
    class CreateParams:
        personality_room_id: UUID
        user_id: str
        role: str = "user"

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        """Create a new personality room user association.

        Args:
            params: Parameters for creating the room user association

        Returns:
            The created PersonalityRoomUserModel instance
        """
        async with get_session() as session:
            room_user = PersonalityRoomUser(
                personality_room_id=params.personality_room_id,
                user_id=params.user_id,
                role=params.role,
            )
            session.add(room_user)
            await session.commit()
            return cls(**room_user.__dict__)

    @classmethod
    async def get_room_users(cls, personality_room_id: UUID) -> list[Self]:
        """Get all users associated with a personality room.

        Args:
            personality_room_id: The ID of the room to get users for

        Returns:
            List of PersonalityRoomUserModel instances for the room
        """
        async with get_session() as session:
            stmt = select(PersonalityRoomUser).where(
                PersonalityRoomUser.personality_room_id == personality_room_id
            )
            result = await session.execute(stmt)
            return [cls(**room_user.__dict__) for room_user in result.scalars().all()]

    @classmethod
    async def get_user_rooms(cls, user_id: str) -> list[Self]:
        """Get all rooms a user has access to.

        Args:
            user_id: The ID of the user to get rooms for

        Returns:
            List of PersonalityRoomUserModel instances for the user
        """
        async with get_session() as session:
            stmt = select(PersonalityRoomUser).where(
                PersonalityRoomUser.user_id == user_id
            )
            result = await session.execute(stmt)
            return [cls(**room_user.__dict__) for room_user in result.scalars().all()]

    @classmethod
    async def get_bulk_room_users(cls, room_ids: list[UUID]) -> list[Self]:
        """Get all room users for multiple rooms in a single query.

        Args:
            room_ids: List of room IDs to get users for

        Returns:
            List of PersonalityRoomUserModel instances for all the rooms
        """
        if not room_ids:
            return []

        async with get_session() as session:
            stmt = select(PersonalityRoomUser).where(
                PersonalityRoomUser.personality_room_id.in_(room_ids)
            )
            result = await session.execute(stmt)
            return [cls(**room_user.__dict__) for room_user in result.scalars().all()]

    @classmethod
    async def get(cls, personality_room_id: UUID, user_id: str) -> Self | None:
        """Get a specific personality room user association.

        Args:
            personality_room_id: The ID of the room
            user_id: The ID of the user

        Returns:
            The PersonalityRoomUserModel instance if found, None otherwise
        """
        async with get_session() as session:
            stmt = select(PersonalityRoomUser).where(
                PersonalityRoomUser.personality_room_id == personality_room_id,
                PersonalityRoomUser.user_id == user_id,
            )
            result = await session.execute(stmt)
            room_user = result.scalars().first()
            if room_user:
                return cls(**room_user.__dict__)
            return None

    @classmethod
    async def delete(cls, personality_room_id: UUID, user_id: str) -> None:
        """Remove a user from a personality room.

        Args:
            personality_room_id: The ID of the room
            user_id: The ID of the user to remove
        """
        async with get_session() as session:
            stmt = select(PersonalityRoomUser).where(
                PersonalityRoomUser.personality_room_id == personality_room_id,
                PersonalityRoomUser.user_id == user_id,
            )
            result = await session.execute(stmt)
            room_user = result.scalars().first()
            if room_user:
                await session.delete(room_user)
                await session.commit()

    @classmethod
    async def update_role(
        cls, personality_room_id: UUID, user_id: str, role: str
    ) -> Self:
        """Update a user's role in a personality room.

        Args:
            personality_room_id: The ID of the room
            user_id: The ID of the user
            role: The new role for the user

        Returns:
            The updated PersonalityRoomUserModel instance

        Raises:
            ValueError: If the room user association is not found
        """
        async with get_session() as session:
            stmt = select(PersonalityRoomUser).where(
                PersonalityRoomUser.personality_room_id == personality_room_id,
                PersonalityRoomUser.user_id == user_id,
            )
            result = await session.execute(stmt)
            room_user = result.scalars().first()
            if room_user:
                room_user.role = role
                await session.commit()
                return cls(**room_user.__dict__)
            raise ValueError("PersonalityRoomUser not found")
