from typing import Any, Dict, Optional, Type
from pydantic import BaseModel, Field
from neuron_server.tools.openai_compatible_tool import OpenAICompatibleTool
from neuron_server.config import config
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
import logging
import time
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class DeepSeekReasoningToolArgs(BaseModel):
    system_prompt: str = Field(
        description="""
Define the model's role and how it approaches the task. Start with a high level and general description of how to act. Include how long of response to return, the format of the response. Optionally include key contextual information to guide the model like releveant past memories.
""".strip()
    )

    user_prompt: str = Field(
        description="""
The specific query or task to process. Include relevant context and requirements:
- What needs to be analyzed or understood
- Key context or background information
- Specific aspects to focus on
- Any other relevant information required to complete the task
""".strip()
    )

    temperature: float = Field(
        description="""
Controls response randomness (0.0 to 1.0):
- 0.0: Most deterministic, best for factual tasks
- 0.1-0.3: Balanced, ideal for analysis (recommended)
- 0.4-0.7: More creative responses
- 0.8-1.0: Maximum creativity
""".strip(),
        default=0.1,
        ge=0.0,
        le=1.0,
    )


class DeepSeekReasoningTool(OpenAICompatibleTool):
    name: str = "deepseek_reasoning"
    description: str = (
        """
Access powerful thinking models through OpenRouter's API for complex reasoning tasks. Provides models specialized in careful analysis, detailed explanations, and thorough problem-solving.

Ideal for:
- Deep analytical thinking
- Technical problem-solving
- Strategic planning
- Complex topic explanations
- Complicated coding problems
- Creating detailed plans
""".strip()
    )

    args_schema: Type[DeepSeekReasoningToolArgs] = DeepSeekReasoningToolArgs

    base_system_prompt: str = (
        """
You are a specialized reasoning engine focused on deep analysis and careful thinking. Your purpose is to:
1. Break down complex problems into clear, logical components
2. Consider multiple perspectives and approaches
3. Provide detailed, well-reasoned explanations
4. Maintain a methodical, step-by-step thinking process
5. Do not ask questions, just answer the user's prompt to the best of your ability.
6. Use github flavored markdown formatting to improve readability:
   - Only use code blocks (```) when showing actual code snippets
   - Never wrap your entire response in code blocks
""".strip()
    )

    @property
    def base_url(self) -> str:
        return "https://openrouter.ai/api/v1"

    @property
    def api_key(self) -> str:
        return config.openrouter_api_key

    def _get_client(self, temperature: float) -> ChatOpenAI:
        return ChatOpenAI(
            model="deepseek/deepseek-r1",
            streaming=True,
            temperature=temperature,
            base_url=self.base_url,
            api_key=self.api_key,
            stream_usage=True,
        )

    async def _arun(
        self,
        system_prompt: str,
        user_prompt: str,
        config: RunnableConfig,
        temperature: float = 0.1,
    ) -> str:
        start_time = time.perf_counter()
        try:
            logger.info(
                f"DeepSeek reasoning request:\n"
                f"- System prompt: {system_prompt}\n"
                f"- User prompt: {user_prompt}\n"
                f"- Temperature: {temperature}\n"
            )

            # Combine with base system prompt
            combined_prompt = f"{self.base_system_prompt}\n\n{system_prompt}".strip()

            chain = (
                ChatPromptTemplate.from_messages(
                    [
                        SystemMessage(content=combined_prompt),
                        MessagesPlaceholder(variable_name="messages"),
                    ]
                )
                | self._get_client(temperature=temperature)
                | StrOutputParser()
            )

            response: str = await chain.ainvoke(
                {
                    "messages": [
                        HumanMessage(content=user_prompt),
                    ],
                },
                config=config,
            )
            duration = time.perf_counter() - start_time
            logger.debug(f"DeepSeek reasoning completed - {duration:.2f}s")
            return response
        except Exception as e:
            duration = time.perf_counter() - start_time
            logger.error(
                f"DeepSeek reasoning failed after {duration:.2f}s: {str(e)}",
                exc_info=True,
            )
            raise e
