import logging
from typing import Literal

from langchain_anthropic import ChatAnthropic

from neuron_server.llms.llm import LLM

logger = logging.getLogger(__name__)


class AnthropicLLM(LLM):
    provider: Literal["anthropic"] = "anthropic"

    def __init__(
        self,
        model_id: str | None = "claude-3-5-sonnet-20241022",
        provider_model_id: str | None = None,
    ) -> None:
        max_tokens = 32_000 if "opus" in (model_id or "").lower() else 64_000

        model = ChatAnthropic(
            model=model_id,
            temperature=1,
            streaming=True,
            max_tokens=max_tokens,
            thinking={"type": "enabled", "budget_tokens": 1024},
            verbose=True,
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
            provider_model_id=provider_model_id,
        )
