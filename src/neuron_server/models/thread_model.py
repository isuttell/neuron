from uuid import UUID
from typing import List, Optional
from neuron_server.database import get_session, Thread, Message
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone
from typing import Literal, Self


def get_context_prompt(context: str) -> str:
    if not context or len(context.strip()) == 0:
        return ""
    return f"""\
The user has provided the following custom instructions for this specific conversation. Use them to guide your response:
\"\"\"
{context}
\"\"\"""".strip()


def get_memory_prompt(memory: str) -> str:
    if not memory or len(memory.strip()) == 0:
        return ""
    return f"""\
Based on past conversations you determined the following was important to remember:
\"\"\"
{memory}
\"\"\"""".strip()


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
    status: Literal["idle", "thinking", "tools", "streaming"] = Field(
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

    def get_context_prompt(self) -> str:
        if not self.context or len(self.context.strip()) == 0:
            return ""
        return f"""\
    The user has provided the following custom instructions for this specific conversation. Use them to guide your response:
    \"\"\"
    {self.context}
    \"\"\"""".strip()

    def get_memory_prompt(self) -> str:
        if not self.memory or len(self.memory.strip()) == 0:
            return ""
        return f"""\
    Based on past conversations you determined the following was important to remember:
    \"\"\"
    {self.memory}
    \"\"\"""".strip()

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
        cls, id: UUID, name: str, context: str, memory: str, status: str
    ) -> Self:
        async with get_session() as session:
            thread = await session.get(Thread, id)
            thread.name = name
            thread.context = context
            thread.memory = memory
            thread.status = status
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

    async def count_messages(self) -> int:
        async with get_session() as session:
            results = await session.execute(
                select(func.count()).where(
                    Message.thread_id == self.id, Message.role != "system"
                )
            )
            return results.scalar()

    async def save(
        self,
    ) -> None:
        async with get_session() as session:
            thread = await session.get(Thread, self.id)
            thread.name = self.name
            thread.context = self.context
            thread.memory = self.memory
            thread.status = self.status
            await session.commit()
