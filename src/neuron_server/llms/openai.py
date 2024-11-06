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
    ):
        model = ChatOpenAI(
            model=model_id,
            temperature=0.7,
            streaming=True,
            max_tokens=4096,
        )
        title_model = ChatOpenAI(
            model=model_id,
            temperature=0.7,
            max_tokens=32,
        )
        memory_model = ChatOpenAI(
            model=model_id,
            temperature=0.1,
            max_tokens=1000,
        )
        super().__init__(
            model, title_model, memory_model, tools=tools, max_input_tokens=32000
        )
