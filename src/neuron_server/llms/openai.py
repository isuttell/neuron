from typing import Literal

from langchain_openai import ChatOpenAI

from neuron_server.llms.llm import LLM


class OpenAILLM(LLM):
    provider: Literal["openai"] = "openai"

    def __init__(
        self,
        model_id: str | None = "gpt-4o",
        provider_model_id: str | None = None,
    ) -> None:
        model = ChatOpenAI(
            model=model_id,
            temperature=1,
            streaming=True,
            stream_usage=True,
            max_tokens=None,
        )
        title_model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=1,
            max_tokens=42,
        )
        memory_model = ChatOpenAI(
            model=model_id,
            temperature=0.3,
        )
        super().__init__(
            model,
            title_model,
            memory_model,
            provider_model_id=provider_model_id,
        )
