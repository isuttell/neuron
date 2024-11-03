from typing import Literal
from pydantic import BaseModel


Provider = Literal["openai", "anthropic", "huggingface"]


class ProviderModel(BaseModel):
    id: str
    provider: Provider
    model_id: str

    class Config:
        protected_namespaces = ()


class OpenAIProviderModel(ProviderModel):
    provider: Provider = "openai"


class AnthropicProviderModel(ProviderModel):
    provider: Provider = "anthropic"


class HuggingFaceProviderModel(ProviderModel):
    provider: Provider = "huggingface"
