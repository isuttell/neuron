from langchain_cohere import ChatCohere
from typing import Optional, Literal
from neuron_server.llms.llm import LLM
from langchain_openai import ChatOpenAI


class CohereLLM(LLM):
    provider: Literal["cohere"] = "cohere"

    def __init__(
        self,
        model_id: Optional[str] = None,
        provider_model_id: Optional[str] = None,
    ):
        model = ChatCohere(
            temperature=1,
            streaming=True,
            model=model_id,
        )
        title_model = ChatCohere(
            temperature=0.6,
            max_tokens=42,
        )
        memory_model = ChatOpenAI(
            model="gpt-4o",
            temperature=0.3,
        )
        super().__init__(
            model=model,
            title_model=title_model,
            memory_model=memory_model,
            provider_model_id=provider_model_id,
        )
