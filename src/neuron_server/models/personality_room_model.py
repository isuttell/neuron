from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import select

from neuron_server.database import PersonalityRoom, PersonalityRoomUser, get_session
from neuron_server.models.personality_model import PersonalityModel


class PersonalityRoomModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    personality_id: UUID = Field(description="The ID of the personality")
    name: str = Field(description="The name of the room")
    type: str = Field(description="Room type: private or shared", default="private")
    message_count: int = Field(description="Number of messages in the room", default=0)
    status: str | None = Field(description="Room-specific status", default=None)
    created_by: str | None = Field(
        description="User ID of the room creator", default=None
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @dataclass
    class CreateParams:
        personality_id: UUID
        name: str
        type: str = "private"
        created_by: str | None = None

    @dataclass
    class UpdateParams:
        room_id: UUID
        name: str | None = None
        type: str | None = None

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        """Create a new personality room.

        Args:
            params: Parameters for creating the room

        Returns:
            The created PersonalityRoomModel instance
        """
        async with get_session() as session:
            room = PersonalityRoom(
                personality_id=params.personality_id,
                name=params.name,
                type=params.type,
                created_by=params.created_by,
            )
            session.add(room)
            await session.commit()
            return cls(**room.__dict__)

    @classmethod
    async def get(cls, room_id: UUID) -> Self | None:
        """Get a personality room by ID.

        Args:
            room_id: The ID of the room to retrieve

        Returns:
            The PersonalityRoomModel instance if found, None otherwise
        """
        async with get_session() as session:
            stmt = select(PersonalityRoom).where(PersonalityRoom.id == room_id)
            result = await session.execute(stmt)
            room = result.scalars().first()
            if room:
                return cls(**room.__dict__)
            return None

    @classmethod
    async def get_for_user(
        cls, room_id: UUID, user_id: str, personality_id: UUID
    ) -> Self | None:
        """Get a room with permission check for a specific user.

        Args:
            room_id: The ID of the room
            user_id: The ID of the user
            personality_id: The ID of the personality (for shared room access check)

        Returns:
            The room if user has access, None otherwise
        """
        async with get_session() as session:
            # Get the room
            stmt = select(PersonalityRoom).where(PersonalityRoom.id == room_id)
            result = await session.execute(stmt)
            room = result.scalars().first()

            if not room:
                return None

            # Check if user has access
            if room.type == "shared":
                # For shared rooms, check if user has access to the personality
                personality = await PersonalityModel.get_for_user(
                    personality_id=personality_id, user_id=user_id
                )
                if personality:
                    return cls(**room.__dict__)
            else:
                # For private rooms, check if user is in room users or is creator
                if room.created_by == user_id:
                    return cls(**room.__dict__)

                # Check PersonalityRoomUser table
                stmt = select(PersonalityRoomUser).where(
                    PersonalityRoomUser.personality_room_id == room_id,
                    PersonalityRoomUser.user_id == user_id,
                )
                result = await session.execute(stmt)
                if result.scalars().first():
                    return cls(**room.__dict__)

            return None

    @classmethod
    async def list_for_personality(
        cls, personality_id: UUID, user_id: str
    ) -> list[Self]:
        """List all rooms for a personality that the user has access to.

        Args:
            personality_id: The ID of the personality
            user_id: The ID of the user

        Returns:
            List of PersonalityRoomModel instances
        """
        async with get_session() as session:
            # Get all rooms for the personality
            stmt = select(PersonalityRoom).where(
                PersonalityRoom.personality_id == personality_id
            )
            result = await session.execute(stmt)
            all_rooms = result.scalars().all()

            # Filter rooms based on access
            accessible_rooms = []
            for room in all_rooms:
                if room.type == "shared":
                    # User has access to all shared rooms with personality access
                    accessible_rooms.append(room)
                # For private rooms, check if user is creator or in room users
                elif room.created_by == user_id:
                    accessible_rooms.append(room)
                else:
                    # Check if user is in room users
                    stmt = select(PersonalityRoomUser).where(
                        PersonalityRoomUser.personality_room_id == room.id,
                        PersonalityRoomUser.user_id == user_id,
                    )
                    result = await session.execute(stmt)
                    if result.scalars().first():
                        accessible_rooms.append(room)

            return [cls(**room.__dict__) for room in accessible_rooms]

    @classmethod
    async def update(cls, params: UpdateParams) -> Self | None:
        """Update a personality room.

        Args:
            params: Parameters for updating the room

        Returns:
            The updated PersonalityRoomModel instance if found, None otherwise
        """
        async with get_session() as session:
            stmt = select(PersonalityRoom).where(PersonalityRoom.id == params.room_id)
            result = await session.execute(stmt)
            room = result.scalars().first()

            if not room:
                return None

            if params.name is not None:
                room.name = params.name
            if params.type is not None:
                room.type = params.type

            room.updated_at = datetime.now(UTC).astimezone()
            await session.commit()
            return cls(**room.__dict__)

    @classmethod
    async def update_status(cls, room_id: UUID, status: str) -> Self | None:
        """Update the status of a personality room.

        Args:
            room_id: The ID of the room to update
            status: The new status (empty string for idle)

        Returns:
            The updated PersonalityRoomModel instance or None if not found
        """
        async with get_session() as session:
            stmt = select(PersonalityRoom).where(PersonalityRoom.id == room_id)
            result = await session.execute(stmt)
            room = result.scalars().first()

            if not room:
                return None

            room.status = status if status else None
            room.updated_at = datetime.now(UTC).astimezone()
            await session.commit()
            return cls(**room.__dict__)

    @classmethod
    async def delete(cls, room_id: UUID) -> bool:
        """Delete a personality room.

        Args:
            room_id: The ID of the room to delete

        Returns:
            True if deleted, False if not found
        """
        async with get_session() as session:
            stmt = select(PersonalityRoom).where(PersonalityRoom.id == room_id)
            result = await session.execute(stmt)
            room = result.scalars().first()

            if not room:
                return False

            await session.delete(room)
            await session.commit()
            return True

    @classmethod
    async def has_admin_access(cls, room_id: UUID, user_id: str) -> bool:
        """Check if a user has admin access to a room.

        Args:
            room_id: The ID of the room
            user_id: The ID of the user

        Returns:
            True if user has admin access, False otherwise
        """
        async with get_session() as session:
            # Check if user is the creator
            stmt = select(PersonalityRoom).where(PersonalityRoom.id == room_id)
            result = await session.execute(stmt)
            room = result.scalars().first()

            if not room:
                return False

            if room.created_by == user_id:
                return True

            # Check if user has admin role in room users
            stmt = select(PersonalityRoomUser).where(
                PersonalityRoomUser.personality_room_id == room_id,
                PersonalityRoomUser.user_id == user_id,
                PersonalityRoomUser.role == "admin",
            )
            result = await session.execute(stmt)
            return result.scalars().first() is not None

    @classmethod
    async def update_message_count(
        cls, room_id: UUID, increment: int = 1
    ) -> Self | None:
        """Update the message count for a room.

        Args:
            room_id: The ID of the room
            increment: Amount to increment (negative to decrement)

        Returns:
            The updated room model or None if not found
        """
        async with get_session() as session:
            stmt = select(PersonalityRoom).where(PersonalityRoom.id == room_id)
            result = await session.execute(stmt)
            room = result.scalars().first()

            if not room:
                return None

            room.message_count += increment
            # Ensure count doesn't go negative
            room.message_count = max(room.message_count, 0)

            await session.commit()
            return cls(**room.__dict__)

    @classmethod
    async def get_user_rooms(cls, user_id: str) -> list[Self]:
        """Get all rooms a user has access to across all personalities.

        Args:
            user_id: The ID of the user

        Returns:
            List of PersonalityRoomModel instances
        """
        async with get_session() as session:
            # Get rooms where user is creator
            stmt = select(PersonalityRoom).where(PersonalityRoom.created_by == user_id)
            result = await session.execute(stmt)
            creator_rooms = result.scalars().all()

            # Get rooms where user is a member
            stmt = (
                select(PersonalityRoom)
                .join(PersonalityRoomUser)
                .where(PersonalityRoomUser.user_id == user_id)
            )
            result = await session.execute(stmt)
            member_rooms = result.scalars().all()

            # Combine and deduplicate
            all_rooms = {room.id: room for room in creator_rooms}
            for room in member_rooms:
                all_rooms[room.id] = room

            return [cls(**room.__dict__) for room in all_rooms.values()]
