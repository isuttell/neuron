from uuid import UUID
from neuron_server.database import get_session, Personality
from typing import Optional, List, Self
from sqlalchemy import select
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime, timezone
from typing import Any


class PersonalityModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(description="How the personality is referred to in the chat")
    description: str = Field(
        description="A short description of the personality's role and purpose"
    )
    context: str = Field(
        description="Information supplied by the personality for additional context"
    )
    logo: Optional[str] = Field(
        description="A URL to an image that represents the personality", default=None
    )
    memory: str = Field(
        description="Information about the personality's preferences and history"
    )
    tool_set: Optional[str] = Field(
        description="The tool set to use for the personality", default=None
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )

    @classmethod
    async def create(
        cls,
        name: str,
        description: str,
        context: str,
        memory: str,
        logo: Optional[str] = None,
        tool_set: Optional[str] = None,
        id: Optional[UUID] = None,
    ) -> Self:
        async with get_session() as session:
            personality = Personality(
                id=id,
                name=name,
                description=description,
                context=context,
                memory=memory,
                tool_set=tool_set,
                logo=logo,
            )
            session.add(personality)
            await session.commit()
            return cls(**personality.__dict__)

    @staticmethod
    async def delete(id: UUID) -> None:
        async with get_session() as session:
            await session.delete(await session.get(Personality, id))
            await session.commit()

    @classmethod
    async def update(
        cls,
        id: UUID,
        name: str,
        description: str,
        context: str,
        memory: str,
        logo: Optional[str],
        tool_set: Optional[str],
    ) -> Self:
        async with get_session() as session:
            personality = await session.get(Personality, id)
            personality.name = name
            personality.description = description
            personality.context = context
            personality.memory = memory
            personality.tool_set = tool_set
            personality.logo = logo
            session.add(personality)
            await session.commit()
            return cls(**personality.__dict__)

    @classmethod
    async def set(cls, id: UUID, key: str, value: Any) -> Self:
        async with get_session() as session:
            personality = await session.get(Personality, id)
            if not personality:
                raise ValueError(f"Personality with ID {str(id)} not found")
            setattr(personality, key, value)
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

    async def save(
        self,
    ) -> None:
        async with get_session() as session:
            personality = await session.get(Personality, self.id)
            personality.name = self.name
            personality.description = self.description
            personality.context = self.context
            personality.memory = self.memory
            personality.tool_set = self.tool_set
            personality.logo = self.logo
            await session.commit()

    @classmethod
    async def get_many(cls, ids: List[UUID]) -> List[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(Personality).where(Personality.id.in_(ids))
            )
            records = results.scalars().all()
            return [cls(**personality.__dict__) for personality in records]
