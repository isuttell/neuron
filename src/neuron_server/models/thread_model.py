import builtins
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import select

from neuron_server.database import Thread, get_session


class ThreadModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    user_id: str = Field(description="The ID of the user who owns this thread")
    name: str = Field(description="The name of the thread", default="")
    context: str = Field(
        description="Additional context for the thread provided by the user",
        default="",
    )
    memory: str = Field(
        description="Additional context for the thread provided by the personality",
        default="",
    )
    status: str = Field(
        description="The status of the thread",
        default="idle",
    )
    personality_id: UUID = Field(
        description="The personality ID associated with the thread"
    )
    message_count: int = Field(
        description="The number of messages in the thread",
        default=0,
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
        name: str = ""
        context: str = ""
        memory: str = ""
        status: str = "idle"
        thread_id: UUID | None = None
        message_count: int = 0

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        async with get_session() as session:
            thread = Thread(
                id=params.thread_id,
                user_id=params.user_id,
                name=params.name,
                context=params.context,
                memory=params.memory,
                status=params.status,
                personality_id=params.personality_id,
                message_count=params.message_count,
            )
            session.add(thread)
            await session.commit()
            return cls(**thread.__dict__)

    @staticmethod
    async def delete(thread_id: UUID) -> None:
        async with get_session() as session:
            await session.delete(await session.get(Thread, thread_id))
            await session.commit()

    @dataclass
    class UpdateParams:
        thread_id: UUID
        name: str
        context: str
        memory: str
        status: str
        message_count: int

    @classmethod
    async def update(cls, params: UpdateParams) -> Self:
        async with get_session() as session:
            thread = await session.get(Thread, params.thread_id)
            thread.name = params.name
            thread.context = params.context
            thread.memory = params.memory
            thread.status = params.status
            thread.message_count = params.message_count
            await session.commit()
            return cls(**thread.__dict__)

    @classmethod
    async def get(cls, thread_id: UUID) -> Self | None:
        async with get_session() as session:
            data = await session.get(Thread, thread_id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(
        cls, personality_id: UUID, user_id: str | None = None, limit: int | None = None
    ) -> list[Self]:
        async with get_session() as session:
            query = select(Thread).where(Thread.personality_id == personality_id)
            if user_id:
                query = query.where(Thread.user_id == user_id)

            # Order by updated_at DESC to show most recent threads first
            query = query.order_by(Thread.updated_at.desc())

            # Apply limit if specified
            if limit:
                query = query.limit(limit)

            results = await session.execute(query)
            return [cls(**thread.__dict__) for thread in results.scalars().all()]

    async def save(
        self,
    ) -> None:
        async with get_session() as session:
            thread = await session.get(Thread, self.id)
            if not thread:
                raise ValueError("Thread not found")
            thread.name = self.name
            thread.context = self.context
            thread.memory = self.memory
            thread.status = self.status
            thread.message_count = self.message_count
            await session.commit()

    @classmethod
    async def set(
        cls,
        thread_id: UUID,
        key: str,
        value: str | int | float | bool | dict | Sequence | None,
    ) -> Self:
        async with get_session() as session:
            thread = await session.get(Thread, thread_id)
            if not thread:
                raise ValueError("Thread not found")
            setattr(thread, key, value)
            session.add(thread)
            await session.commit()
            return cls(**thread.__dict__)

    @classmethod
    async def get_recent_threads(
        cls, hours: int = 1, limit: int = 10, user_id: str | None = None
    ) -> builtins.list[Self]:
        """Get all threads that have received messages in the last specified hours.

        Args:
            hours: Number of hours to look back (default: 1)
            limit: Maximum number of threads to return (default: 10)
            user_id: Optional user ID to filter threads by owner

        Returns:
            List of ThreadModel instances with recent messages
        """
        async with get_session() as session:
            cutoff_time = datetime.now(UTC) - timedelta(hours=hours)

            query = (
                select(Thread)
                .where(
                    Thread.created_at >= cutoff_time,
                )
                .order_by(Thread.updated_at.desc())
            )

            if user_id:
                query = query.where(Thread.user_id == user_id)

            query = query.limit(limit)
            results = await session.execute(query)
            return [cls(**thread.__dict__) for thread in results.scalars().all()]
