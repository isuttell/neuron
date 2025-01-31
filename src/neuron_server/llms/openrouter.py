from typing import Literal

from langchain_openai import ChatOpenAI

from neuron_server.config import config
from neuron_server.llms.llm import LLM


class OpenRouterLLM(LLM):
    provider: Literal["openrouter"] = "openrouter"

    base_url: str = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        model_id: str | None = "openai/gpt-4o",
        provider_model_id: str | None = None,
    ) -> None:
        model = ChatOpenAI(
            model=model_id,
            temperature=1,
            streaming=True,
            stream_usage=True,
            max_tokens=None,
            api_key=config.openrouter_api_key,
            base_url=self.base_url,
        )
        title_model = ChatOpenAI(
            model=model_id,
            temperature=1,
            max_tokens=42,
            api_key=config.openrouter_api_key,
            base_url=self.base_url,
        )
        memory_model = ChatOpenAI(
            model=model_id,
            temperature=0.3,
            max_tokens=4096,
            api_key=config.openrouter_api_key,
            base_url=self.base_url,
        )
        super().__init__(
            model,
            title_model,
            memory_model,
            provider_model_id=provider_model_id,
        )
