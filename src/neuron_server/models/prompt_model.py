from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import UUID4, BaseModel, Field, field_serializer
from sqlalchemy import select

from neuron_server.database import Prompt, get_session


class PromptModel(BaseModel):
    id: UUID4 = Field(default_factory=lambda: uuid4())
    name: str
    text: str
    personality_id: UUID4 | None = None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @classmethod
    async def create(
        cls, name: str, text: str, personality_id: UUID4 | None = None
    ) -> "PromptModel":
        async with get_session() as session:
            prompt = Prompt(name=name, text=text, personality_id=personality_id)
            session.add(prompt)
            await session.commit()
            return cls(**prompt.__dict__)

    @classmethod
    async def get(cls, prompt_id: UUID4) -> Optional["PromptModel"]:
        async with get_session() as session:
            result = await session.execute(select(Prompt).where(Prompt.id == prompt_id))
            prompt = result.scalar_one_or_none()
            return cls(**prompt.__dict__) if prompt else None

    @classmethod
    async def list(cls, personality_id: UUID4 | None = None) -> list["PromptModel"]:
        async with get_session() as session:
            query = select(Prompt)
            if personality_id:
                query = query.where(Prompt.personality_id == personality_id)
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
    async def delete(cls, prompt_id: UUID4) -> None:
        async with get_session() as session:
            prompt = await session.get(Prompt, prompt_id)
            if prompt:
                await session.delete(prompt)
                await session.commit()
