from typing import Literal
from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from neuron_server.database import get_session, ProviderModel
from sqlalchemy import select
from pydantic import BaseModel, Field, field_serializer
from uuid import uuid4
from datetime import datetime, timezone
from typing import Literal, Self
from neuron_server.llms.llm import LLM
from neuron_server.llms.openai import OpenAILLM
from neuron_server.llms.anthropic import AnthropicLLM
from neuron_server.llms.huggingface import HuggingFaceLLM
from neuron_server.llms.huggingface_toolless import HuggingFaceToollessLLM

Provider = Literal["openai", "anthropic", "huggingface"]


class ProviderModelModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    provider: Provider = Field(description="The provider of the model")
    model_id: str = Field(description="The model id of the provider")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone()
    )

    model_config = {"protected_namespaces": ()}

    @field_serializer("created_at", "updated_at")
    def parse_date(self, v: datetime) -> str:
        return v.astimezone().isoformat()

    @classmethod
    async def get(cls, id: UUID) -> Optional[Self]:
        async with get_session() as session:
            data = await session.get(ProviderModel, id)
            if data:
                return cls(**data.__dict__)
            return None

    @classmethod
    async def list(cls) -> List[Self]:
        async with get_session() as session:
            rows = await session.execute(
                select(ProviderModel)
                .order_by(ProviderModel.provider)
                .order_by(ProviderModel.model_id)
            )
            return [cls(**row.__dict__) for row in rows.scalars().all()]

    async def save(
        self,
    ) -> None:
        async with get_session() as session:
            provider_model = await session.get(ProviderModel, self.id)
            provider_model.provider = self.provider
            provider_model.model_id = self.model_id
            await session.commit()

    def to_llm(self) -> AnthropicLLM | HuggingFaceToollessLLM | OpenAILLM:
        if self.provider == "anthropic":
            return AnthropicLLM(model_id=self.model_id)
        elif self.provider == "huggingface":
            return HuggingFaceToollessLLM(repo_id=self.model_id)
        elif self.provider == "openai":
            return OpenAILLM(model_id=self.model_id)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
