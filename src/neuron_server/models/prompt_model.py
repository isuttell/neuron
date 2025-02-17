from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Self
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import or_, select

from neuron_server.database import Prompt, get_session


class PromptModel(BaseModel):
    id: UUID = Field(
        default_factory=lambda: uuid4(), description="Unique identifier for the prompt"
    )
    name: str = Field(description="Name of the prompt")
    text: str = Field(description="The prompt text content")
    personality_id: UUID | None = Field(
        default=None, description="Associated personality ID"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).astimezone(),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC).astimezone(),
        description="Last update timestamp",
    )

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @dataclass
    class CreateParams:
        name: str
        text: str
        personality_id: UUID | None = None

    @classmethod
    async def create(cls, params: CreateParams) -> Self:
        async with get_session() as session:
            prompt = Prompt(
                name=params.name, text=params.text, personality_id=params.personality_id
            )
            session.add(prompt)
            await session.commit()
            return cls(**prompt.__dict__)

    @classmethod
    async def get(cls, prompt_id: UUID) -> Self | None:
        async with get_session() as session:
            result = await session.execute(select(Prompt).where(Prompt.id == prompt_id))
            prompt = result.scalar_one_or_none()
            return cls(**prompt.__dict__) if prompt else None

    @classmethod
    async def list(cls, personality_id: UUID | None = None) -> list[Self]:
        async with get_session() as session:
            query = select(Prompt)
            if personality_id:
                query = query.where(
                    or_(
                        Prompt.personality_id == personality_id,
                        Prompt.personality_id.is_(None),
                    )
                )
            result = await session.execute(query)
            prompts = result.scalars().all()
            return [cls(**prompt.__dict__) for prompt in prompts]

    async def save(self) -> None:
        async with get_session() as session:
            prompt = await session.get(Prompt, self.id)
            if prompt:
                prompt.name = self.name
                prompt.text = self.text
                prompt.personality_id = self.personality_id
                await session.commit()

    @classmethod
    async def delete(cls, prompt_id: UUID) -> None:
        async with get_session() as session:
            prompt = await session.get(Prompt, prompt_id)
            if prompt:
                await session.delete(prompt)
                await session.commit()
