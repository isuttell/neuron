from langchain_anthropic import ChatAnthropic
from typing import Optional, Literal
from neuron_server.llms.llm import LLM


class AnthropicLLM(LLM):
    provider: Literal["anthropic"] = "anthropic"

    def __init__(
        self,
        model_id: Optional[str] = "claude-3-5-sonnet-20241022",
        provider_model_id: Optional[str] = None,
    ):
        model = ChatAnthropic(
            model=model_id,
            temperature=1,
            streaming=True,
        )
        title_model = ChatAnthropic(
            # model=model_id,
            model="claude-3-5-haiku-20241022",
            temperature=1,
            max_tokens=42,
        )
        memory_model = ChatAnthropic(
            model=model_id,
            temperature=0.3,
            max_tokens=8192,
        )
        super().__init__(
            model=model,
            title_model=title_model,
            memory_model=memory_model,
            provider_model_id=provider_model_id,
        )
