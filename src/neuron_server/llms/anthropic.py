from langchain_anthropic import ChatAnthropic
from typing import Optional
from neuron_server.llms.llm import LLM
from neuron_server.models.provider_model import Provider
from neuron_server.llms.tools import tools


class AnthropicLLM(LLM):
    provider: Provider = "anthropic"

    def __init__(
        self,
        model_id: Optional[str] = "claude-3-opus-20240229",
        max_tokens: int = 4096,
        max_title_tokens: int = 32,
        max_memory_tokens: int = 1024,
    ):
        model = ChatAnthropic(
            model=model_id,
            temperature=0.7,
            streaming=True,
            max_tokens=max_tokens,
        )
        title_model = ChatAnthropic(
            model=model_id,
            temperature=0.3,
            max_tokens=max_title_tokens,
        )
        memory_model = ChatAnthropic(
            model=model_id,
            temperature=0.3,
            max_tokens=max_memory_tokens,
        )
        super().__init__(model, title_model, memory_model, tools=tools)
