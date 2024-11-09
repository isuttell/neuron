from uuid import UUID
from neuron_server.database import get_session, Personality
from typing import Optional, List, Self
from sqlalchemy import select
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone


def get_context_prompt(name: str, context: str) -> str:
    return f"""\
You the assistant are called {name}. Use the following custom instructions to guide your responses:
\"\"\"
{context}
\"\"\"""".strip()


def get_memory_prompt(memory: Optional[str] = None) -> str:
    if not memory or len(memory.strip()) == 0:
        return ""
    return f"""\
Based on past conversations you have determined the following about the personality:
\"\"\"
{memory}
\"\"\"""".strip()


class PersonalityModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(description="How the personality is referred to in the chat")
    context: str = Field(
        description="Information supplied by the personality for additional context"
    )
    memory: str = Field(
        description="Information about the personality's preferences and history"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )

    def get_context_prompt(self) -> str:
        return f"""\
    You the assistant are called {self.name}. Use the following custom instructions to guide your responses:
    \"\"\"
    {self.context}
    \"\"\"""".strip()

    def get_memory_prompt(self) -> str:
        if not self.memory or len(self.memory.strip()) == 0:
            return ""
        return f"""\
    Based on past conversations you have determined the following about the personality:
    \"\"\"
    {self.memory}
    \"\"\"""".strip()

    @classmethod
    async def create(
        cls, name: str, context: str, memory: str, id: Optional[UUID] = None
    ) -> Self:
        async with get_session() as session:
            personality = Personality(id=id, name=name, context=context, memory=memory)
            session.add(personality)
            await session.commit()
            return cls(**personality.__dict__)

    @staticmethod
    async def delete(id: UUID) -> None:
        async with get_session() as session:
            await session.delete(await session.get(Personality, id))
            await session.commit()

    @classmethod
    async def update(cls, id: UUID, name: str, context: str, memory: str) -> Self:
        async with get_session() as session:
            personality = await session.get(Personality, id)
            personality.name = name
            personality.context = context
            personality.memory = memory
            session.add(personality)
            await session.commit()
            return cls(**personality.__dict__)

    @classmethod
    async def list(cls) -> List[Self]:
        async with get_session() as session:
            results = await session.execute(select(Personality))
            records = results.scalars().all()
            return [cls(**personality.__dict__) for personality in records]

    @classmethod
    async def get(cls, id: UUID) -> Optional[Self]:
        async with get_session() as session:
            data = await session.get(Personality, id)
            if data:
                return cls(**data.__dict__)
            return None
