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
    ):
        model = ChatAnthropic(
            model=model_id,
            temperature=0.7,
            streaming=True,
            max_tokens=4096,
        )
        title_model = ChatAnthropic(
            model=model_id,
            temperature=0.3,
            max_tokens=42,
        )
        memory_model = ChatAnthropic(
            model=model_id,
            temperature=0.3,
            max_tokens=1024,
        )
        super().__init__(
            model=model,
            title_model=title_model,
            memory_model=memory_model,
            tools=tools,
            max_input_tokens=15000,
        )
