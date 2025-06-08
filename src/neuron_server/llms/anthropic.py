import logging
from collections.abc import Sequence
from typing import Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage

from neuron_server.llms.llm import LLM

logger = logging.getLogger(__name__)


class AnthropicLLM(LLM):
    provider: Literal["anthropic"] = "anthropic"

    def __init__(
        self,
        model_id: str | None = "claude-3-5-sonnet-20241022",
        provider_model_id: str | None = None,
        caching_enabled: bool = False,
    ) -> None:
        self.caching_enabled = caching_enabled
        max_tokens = 32_000 if "opus" in (model_id or "").lower() else 64_000

        model = ChatAnthropic(
            model=model_id,
            temperature=1,
            streaming=True,
            max_tokens=max_tokens,
            thinking={"type": "enabled", "budget_tokens": 1024},
            verbose=True,
        )
        fast_model = ChatAnthropic(
            model="claude-3-5-haiku-20241022",
            temperature=1,
        )
        memory_model = ChatAnthropic(
            model=model_id,
            temperature=0.3,
            max_tokens=8192,
        )
        super().__init__(
            model=model,
            fast_model=fast_model,
            memory_model=memory_model,
            provider_model_id=provider_model_id,
        )

    def _apply_caching_to_messages(
        self, messages: Sequence[BaseMessage]
    ) -> Sequence[BaseMessage]:
        """Add cache_control to the last user message for Anthropic models."""
        # Convert to list for modification
        messages_list = list(messages)

        # Find the last human message and add cache control
        for i in range(len(messages_list) - 1, -1, -1):
            if isinstance(messages_list[i], HumanMessage):
                # Create a copy of the message with cache_control
                original_msg = messages_list[i]
                content = original_msg.content

                # Handle string content - convert to list format with cache control
                if isinstance(content, str):
                    content_with_cache = [
                        {
                            "type": "text",
                            "text": content,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ]
                    messages_list[i] = original_msg.model_copy(
                        update={"content": content_with_cache}
                    )
                # Handle list content - add cache_control to the last content block
                elif isinstance(content, list) and len(content) > 0:
                    # Make a copy of the content list
                    content_copy = []
                    for j, block in enumerate(content):
                        if isinstance(block, dict):
                            block_copy = block.copy()
                            # Add cache_control to the last content block
                            if j == len(content) - 1:
                                block_copy["cache_control"] = {"type": "ephemeral"}
                            content_copy.append(block_copy)
                        else:
                            content_copy.append(block)

                    # Create new message with modified content using model_copy
                    messages_list[i] = original_msg.model_copy(
                        update={"content": content_copy}
                    )
                break

        return messages_list
