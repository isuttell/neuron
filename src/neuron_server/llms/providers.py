from typing import Optional, List
from neuron_server.llms.llm import LLM
from neuron_server.llms.openai import OpenAILLM
from neuron_server.llms.anthropic import AnthropicLLM
from neuron_server.llms.huggingface import HuggingFaceLLM
from neuron_server.llms.huggingface_toolless import HuggingFaceToollessLLM
from neuron_server.models.provider_model import (
    ProviderModel,
    OpenAIProviderModel,
    AnthropicProviderModel,
    HuggingFaceProviderModel,
)

providers: List[ProviderModel] = [
    OpenAIProviderModel(id="f47ac10b-58cc-4372-a567-0e02b2c3d479", model_id="gpt-4o"),
    OpenAIProviderModel(
        id="d1e1f3e1-1b2e-4c3b-8c1e-1c1e1c1e1c2", model_id="gpt-4o-mini"
    ),
    AnthropicProviderModel(
        id="c9eb1f3e-1b2e-4c3b-8c1e-1c1e1c1e1c3",
        model_id="claude-3-opus-20240229",
    ),
    AnthropicProviderModel(
        id="c9eb1f3e-1b2e-4c3b-8c1e-1c1e1c1e1c4",
        model_id="claude-3-5-sonnet-20241022",
    ),
    HuggingFaceProviderModel(
        id="d3b1f3e1-1b2e-4c3b-8c1e-1c1e1c1e1c5",
        model_id="meta-llama/Llama-3.1-70B-Instruct",
    ),
    HuggingFaceProviderModel(
        id="e4b1f3e1-1b2e-4c3b-8c1e-1c1e1c1e1c6",
        provider="huggingface",
        model_id="meta-llama/Llama-3.1-8B-Instruct",
    ),
    HuggingFaceProviderModel(
        id="e4b1f3e1-1b2e-4c3b-8c1e-1c1e1c1e1c7",
        provider="huggingface",
        model_id="Qwen/Qwen2.5-72B-Instruct",
    ),
    HuggingFaceProviderModel(
        id="e4b1f3e1-1b2e-4c3b-8c1e-1c1e1c1e1c8",
        provider="huggingface",
        model_id="mistralai/Mistral-Nemo-Instruct-2407",
    ),
    HuggingFaceProviderModel(
        id="e4b1f3e1-1b2e-4c3b-8c1e-1c1e1c1e1c9",
        provider="huggingface",
        model_id="google/gemma-2-9b-it",
    ),
]


def get_provider(provider_id: Optional[str]) -> LLM:
    if not provider_id:
        return OpenAILLM()
    provider = next((p for p in providers if p.id == provider_id), None)
    if not provider:
        raise ValueError(f"Unknown provider id: {provider_id}")
    if provider.provider == "anthropic":
        return AnthropicLLM(model_id=provider.model_id)
    elif provider.provider == "huggingface":
        return HuggingFaceToollessLLM(repo_id=provider.model_id)
    elif provider.provider == "openai":
        return OpenAILLM(model_id=provider.model_id)
    else:
        raise ValueError(f"Unknown provider: {provider.provider}")
