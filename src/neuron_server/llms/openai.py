from langchain_openai import ChatOpenAI
from neuron_server.llms.llm import LLM
from typing import Optional, Literal


class OpenAILLM(LLM):
    provider: Literal["openai"] = "openai"

    def __init__(
        self,
        model_id: Optional[str] = "gpt-4o",
    ):
        model = ChatOpenAI(
            model=model_id,
            temperature=1,
            streaming=True,
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
            max_tokens=4096,
        )
        super().__init__(
            model,
            title_model,
            memory_model,
        )
