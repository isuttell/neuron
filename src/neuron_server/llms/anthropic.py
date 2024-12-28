from langchain_anthropic import ChatAnthropic
from typing import Optional, Literal
from neuron_server.llms.llm import LLM


class AnthropicLLM(LLM):
    provider: Literal["anthropic"] = "anthropic"

    def __init__(
        self,
        model_id: Optional[str] = "claude-3-5-sonnet-20241022",
    ):
        model = ChatAnthropic(
            model=model_id,
            temperature=1,
            streaming=True,
            max_tokens=8192,
        )
        title_model = ChatAnthropic(
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
        )
