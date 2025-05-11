from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import select

from neuron_server.database import ThreadUser, get_session


class ThreadUserModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    thread_id: UUID = Field(description="The ID of the thread")
    user_id: str = Field(description="The ID of the user")
    role: str = Field(description="The user's role in this thread", default="user")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @dataclass
    class CreateParams:
        thread_id: UUID
        user_id: str
        role: str = "user"

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        """Create a new thread user association.

        Args:
            params: Parameters for creating the thread user association

        Returns:
            The created ThreadUserModel instance
        """
        async with get_session() as session:
            thread_user = ThreadUser(
                thread_id=params.thread_id,
                user_id=params.user_id,
                role=params.role,
            )
            session.add(thread_user)
            await session.commit()
            return cls(**thread_user.__dict__)

    @classmethod
    async def get_thread_users(cls, thread_id: UUID) -> list[Self]:
        """Get all users associated with a thread.

        Args:
            thread_id: The ID of the thread to get users for

        Returns:
            List of ThreadUserModel instances for the thread
        """
        async with get_session() as session:
            stmt = select(ThreadUser).where(ThreadUser.thread_id == thread_id)
            result = await session.execute(stmt)
            return [
                cls(**thread_user.__dict__) for thread_user in result.scalars().all()
            ]

    @classmethod
    async def get_user_threads(cls, user_id: str) -> list[Self]:
        """Get all threads a user has access to.

        Args:
            user_id: The ID of the user to get threads for

        Returns:
            List of ThreadUserModel instances for the user
        """
        async with get_session() as session:
            stmt = select(ThreadUser).where(ThreadUser.user_id == user_id)
            result = await session.execute(stmt)
            return [
                cls(**thread_user.__dict__) for thread_user in result.scalars().all()
            ]

    @classmethod
    async def get(cls, thread_id: UUID, user_id: str) -> Self | None:
        """Get a specific thread user association.

        Args:
            thread_id: The ID of the thread
            user_id: The ID of the user

        Returns:
            The ThreadUserModel instance if found, None otherwise
        """
        async with get_session() as session:
            stmt = select(ThreadUser).where(
                ThreadUser.thread_id == thread_id, ThreadUser.user_id == user_id
            )
            result = await session.execute(stmt)
            thread_user = result.scalars().first()
            if thread_user:
                return cls(**thread_user.__dict__)
            return None

    @classmethod
    async def delete(cls, thread_id: UUID, user_id: str) -> None:
        """Remove a user from a thread.

        Args:
            thread_id: The ID of the thread
            user_id: The ID of the user to remove
        """
        async with get_session() as session:
            stmt = select(ThreadUser).where(
                ThreadUser.thread_id == thread_id, ThreadUser.user_id == user_id
            )
            result = await session.execute(stmt)
            thread_user = result.scalars().first()
            if thread_user:
                await session.delete(thread_user)
                await session.commit()

    @classmethod
    async def update_role(cls, thread_id: UUID, user_id: str, role: str) -> Self:
        """Update a user's role in a thread.

        Args:
            thread_id: The ID of the thread
            user_id: The ID of the user
            role: The new role for the user

        Returns:
            The updated ThreadUserModel instance

        Raises:
            ValueError: If the thread user association is not found
        """
        async with get_session() as session:
            stmt = select(ThreadUser).where(
                ThreadUser.thread_id == thread_id, ThreadUser.user_id == user_id
            )
            result = await session.execute(stmt)
            thread_user = result.scalars().first()
            if thread_user:
                thread_user.role = role
                await session.commit()
                return cls(**thread_user.__dict__)
            raise ValueError("ThreadUser not found")
