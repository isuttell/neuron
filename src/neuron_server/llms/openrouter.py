from langchain_openai import ChatOpenAI
from neuron_server.llms.llm import LLM
from typing import Optional, Literal
from neuron_server.config import config


class OpenRouterLLM(LLM):
    provider: Literal["openrouter"] = "openrouter"

    base_url: str = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        model_id: Optional[str] = "google/gemini-2.0-flash-exp:free",
        provider_model_id: Optional[str] = None,
    ):
        model = ChatOpenAI(
            model=model_id,
            temperature=1,
            streaming=True,
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
