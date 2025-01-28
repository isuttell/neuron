from typing import Literal
from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional, Any
from sqlalchemy import select
from pydantic import BaseModel, Field, field_serializer
from uuid import uuid4
from datetime import datetime, timezone
from typing import Literal, Self
from neuron_server.llms.llm import LLM
from neuron_server.llms.openai import OpenAILLM
from neuron_server.llms.anthropic import AnthropicLLM
from neuron_server.llms.cohere import CohereLLM
from neuron_server.llms.openrouter import OpenRouterLLM
from neuron_server.config import config
from neuron_server.database import get_session, ProviderModel

Provider = Literal["openai", "anthropic", "cohere", "openrouter"]


class ProviderModelModel(BaseModel):
    id: UUID = Field(default_factory=lambda: uuid4())
    provider: Provider = Field(description="The provider of the model")
    model_id: str = Field(description="The model id of the provider")
    enabled: bool = Field(description="Whether the model is enabled")
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
            provider_model.enabled = self.enabled

            # If enabling this provider, disable all others
            if self.enabled:
                result = await session.execute(
                    select(ProviderModel)
                    .where(ProviderModel.id != self.id)
                    .where(ProviderModel.enabled == True)
                )
                other_providers = result.scalars().all()

                # Disable other providers
                for other_provider in other_providers:
                    other_provider.enabled = False

            await session.commit()

    def to_llm(self):
        if self.provider == "anthropic":
            return AnthropicLLM(model_id=self.model_id, provider_model_id=self.id)
        elif self.provider == "openai":
            return OpenAILLM(model_id=self.model_id, provider_model_id=self.id)
        elif self.provider == "openrouter":
            return OpenRouterLLM(model_id=self.model_id, provider_model_id=self.id)
        elif self.provider == "cohere":
            return CohereLLM(model_id=self.model_id, provider_model_id=self.id)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    @classmethod
    async def get_active_provider(cls) -> Self:
        """Get the currently active provider from the database"""
        async with get_session() as session:
            result = await session.execute(
                select(ProviderModel).where(ProviderModel.enabled == True)
            )
            provider = result.scalar_one_or_none()

            if not provider:
                raise ValueError("No active provider found")

            return cls(**provider.__dict__)

    @classmethod
    async def get_active_llm(cls) -> LLM:
        """Get LLM instance for the active provider"""
        provider = await cls.get_active_provider()
        return provider.to_llm()

    @classmethod
    async def setup(cls, provider_id: Optional[UUID] = None):
        """Setup a provider as active"""
        provider = await cls.get(provider_id)
        if not provider:
            raise ValueError("Provider not found")

        # Find and disable currently active provider
        async with get_session() as session:
            result = await session.execute(
                select(ProviderModel).where(ProviderModel.enabled == True)
            )
            active_provider: Any | None = result.scalar_one_or_none()

            if active_provider:
                active_provider.enabled = False
                await session.commit()

        provider.enabled = True
        await provider.save()

    @classmethod
    async def get_active_provider_id(cls) -> Optional[UUID]:
        """Get the currently active provider ID from database"""
        provider = await cls.get_active_provider()
        return provider.id
