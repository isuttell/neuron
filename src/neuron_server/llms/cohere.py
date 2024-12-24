from langchain_cohere import ChatCohere
from typing import Optional, Literal
from neuron_server.llms.llm import LLM
from neuron_server.llms.tools import default_tools


class CohereLLM(LLM):
    provider: Literal["cohere"] = "cohere"

    def __init__(
        self,
        model_id: Optional[str] = None,
    ):
        model = ChatCohere(
            temperature=1,
            streaming=True,
        )
        title_model = ChatCohere(
            temperature=0.6,
            max_tokens=42,
        )
        memory_model = ChatCohere(
            temperature=0.3,
            max_tokens=4096,
        )
        super().__init__(
            model=model,
            title_model=title_model,
            memory_model=memory_model,
            tools=default_tools,
        )
