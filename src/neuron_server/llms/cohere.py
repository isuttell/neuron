from typing import Literal
from uuid import UUID

from langchain_cohere import ChatCohere
from langchain_openai import ChatOpenAI

from neuron_server.llms.llm import LLM


class CohereLLM(LLM):
    provider: Literal["cohere"] = "cohere"

    def __init__(
        self,
        model_id: str | None = None,
        provider_model_id: UUID | None = None,
    ) -> None:
        model = ChatCohere(
            temperature=1,
            streaming=True,
            model=model_id,
        )
        fast_model = ChatCohere(
            temperature=0.6,
        )
        memory_model = ChatOpenAI(
            model="gpt-4o",
            temperature=0.3,
        )
        super().__init__(
            model=model,
            model_id=model_id,
            fast_model=fast_model,
            memory_model=memory_model,
            provider_model_id=provider_model_id,
        )
