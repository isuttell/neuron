from uuid import UUID
from typing import List, Optional
from neuron_server.database import get_session, Thread, Message
from sqlalchemy import select, func, and_
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone, timedelta
from typing import Literal, Self, Any
from pydantic import field_serializer


class ThreadModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @classmethod
    async def create(
        cls,
        personality_id: UUID,
        name: Optional[str] = "",
        context: Optional[str] = "",
        memory: Optional[str] = "",
        status: Optional[str] = "idle",
        id: Optional[UUID] = None,
    ) -> Self:
        async with get_session() as session:
            thread = Thread(
                id=id,
                name=name,
                context=context,
                memory=memory,
                status=status,
                personality_id=personality_id,
            )
            session.add(thread)
            await session.commit()
            return cls(**thread.__dict__)

    @staticmethod
    async def delete(id: UUID) -> None:
        async with get_session() as session:
            await session.delete(await session.get(Thread, id))
            await session.commit()

    @classmethod
    async def update(
        cls,
        id: UUID,
        name: str,
        context: str,
        memory: str,
        status: str,
        message_count: int,
    ) -> Self:
        async with get_session() as session:
            thread = await session.get(Thread, id)
            thread.name = name
            thread.context = context
            thread.memory = memory
            thread.status = status
            thread.message_count = message_count
            await session.commit()
            return cls(**thread.__dict__)

    @classmethod
    async def get(cls, id: UUID) -> Optional[Self]:
        async with get_session() as session:
            data = await session.get(Thread, id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(cls, personality_id: UUID) -> List[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(Thread).where(Thread.personality_id == personality_id)
            )
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
    async def set(cls, id: UUID, key: str, value: Any) -> Self:
        async with get_session() as session:
            thread = await session.get(Thread, id)
            if not thread:
                raise ValueError("Thread not found")
            setattr(thread, key, value)
            session.add(thread)
            await session.commit()
            return cls(**thread.__dict__)

    @classmethod
    async def get_recent_threads(cls, hours: int = 1, limit: int = 10) -> List[Self]:
        """Get all threads that have received messages in the last specified hours.

        Args:
            hours: Number of hours to look back (default: 1)

        Returns:
            List of ThreadModel instances with recent messages
        """
        async with get_session() as session:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

            # Query for threads with messages newer than cutoff time
            query = (
                select(Thread)
                .where(
                    Thread.created_at >= cutoff_time,
                )
                .order_by(Thread.updated_at.desc())
                .limit(limit)
            )

            results = await session.execute(query)
            return [cls(**thread.__dict__) for thread in results.scalars().all()]
