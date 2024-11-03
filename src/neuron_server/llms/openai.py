from langchain_openai import ChatOpenAI
from neuron_server.llms.llm import LLM
from typing import Optional
from neuron_server.models.provider_model import Provider
from neuron_server.llms.tools import tools


class OpenAILLM(LLM):
    provider: Provider = "openai"

    def __init__(
        self,
        model_id: Optional[str] = "gpt-4o",
        max_tokens: int = 4096,
        max_title_tokens: int = 32,
        max_memory_tokens: int = 1024,
    ):
        model = ChatOpenAI(
            model=model_id,
            temperature=0.7,
            streaming=True,
            max_tokens=max_tokens,
        )
        title_model = ChatOpenAI(
            model=model_id,
            temperature=0.7,
            max_tokens=max_title_tokens,
        )
        memory_model = ChatOpenAI(
            model=model_id,
            temperature=0.1,
            max_tokens=max_memory_tokens,
        )
        super().__init__(model, title_model, memory_model, tools=tools)
