import builtins
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select

from neuron_server.database import Personality, get_session


class PersonalityModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    name: str = Field(description="How the personality is referred to in the chat")
    description: str = Field(
        description="A short description of the personality's role and purpose"
    )
    context: str = Field(
        description="Information supplied by the personality for additional context"
    )
    logo: str | None = Field(
        description="A URL to an image that represents the personality", default=None
    )
    memory: str = Field(
        description="Information about the personality's preferences and history"
    )
    tool_set: str | None = Field(
        description="The tool set to use for the personality", default=None
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC).astimezone())

    @dataclass
    class CreateParams:
        name: str
        description: str
        context: str
        memory: str
        logo: str | None = None
        tool_set: str | None = None
        personality_id: UUID | None = None

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        async with get_session() as session:
            personality = Personality(
                id=params.personality_id,
                name=params.name,
                description=params.description,
                context=params.context,
                memory=params.memory,
                tool_set=params.tool_set,
                logo=params.logo,
            )
            session.add(personality)
            await session.commit()
            return cls(**personality.__dict__)

    @staticmethod
    async def delete(personality_id: UUID) -> None:
        async with get_session() as session:
            await session.delete(await session.get(Personality, personality_id))
            await session.commit()

    @dataclass
    class UpdateParams:
        personality_id: UUID
        name: str
        description: str
        context: str
        memory: str
        logo: str | None
        tool_set: str | None

    @classmethod
    async def update(cls, params: UpdateParams) -> Self:
        async with get_session() as session:
            personality = await session.get(Personality, params.personality_id)
            personality.name = params.name
            personality.description = params.description
            personality.context = params.context
            personality.memory = params.memory
            personality.tool_set = params.tool_set
            personality.logo = params.logo
            session.add(personality)
            await session.commit()
            return cls(**personality.__dict__)

    @classmethod
    async def set(
        cls,
        personality_id: UUID,
        key: str,
        value: str | int | float | bool | dict | list | None,
    ) -> Self:
        async with get_session() as session:
            personality = await session.get(Personality, personality_id)
            if not personality:
                raise ValueError(f"Personality with ID {str(personality_id)} not found")
            setattr(personality, key, value)
            session.add(personality)
            await session.commit()
            return cls(**personality.__dict__)

    @classmethod
    async def list(cls) -> list[Self]:
        async with get_session() as session:
            results = await session.execute(select(Personality))
            records = results.scalars().all()
            return [cls(**personality.__dict__) for personality in records]

    @classmethod
    async def get(cls, personality_id: UUID) -> Self | None:
        async with get_session() as session:
            data = await session.get(Personality, personality_id)
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
    async def get_many(cls, ids: builtins.list[UUID]) -> builtins.list[Self]:
        async with get_session() as session:
            results = await session.execute(
                select(Personality).where(Personality.id.in_(ids))
            )
            records = results.scalars().all()
            return [cls(**personality.__dict__) for personality in records]
