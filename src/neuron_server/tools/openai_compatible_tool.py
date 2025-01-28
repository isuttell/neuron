
from langchain.tools import BaseTool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from neuron_server.logger import logger


class OpenAICompatibleToolArgs(BaseModel):
    model: str = Field(
        default="deepseek/deepseek-r1",
        description="DeepSeek R1: A powerful model optimized for technical reasoning and step-by-step analysis.",
    )

    system_prompt: str = Field(
        description="""
Define the model's role and behavior. Be specific about expertise and approach needed:
- "You are an expert analyst breaking down complex topics..."
- "You are a strategic planner developing actionable solutions..."
The system prompt shapes how the model approaches the task.
""".strip()
    )

    user_prompt: str = Field(
        description="""
The specific query or task to process. Include relevant context and requirements:
- What needs to be analyzed or understood
- Key context or background information
- Specific aspects to focus on
- Expected response format
""".strip()
    )

    temperature: float = Field(
        description="""
Controls response randomness (0.0 to 1.0):
- 0.0: Most deterministic, best for factual tasks
- 0.1-0.3: Balanced, ideal for analysis
- 0.4-0.7: More creative responses
- 0.8-1.0: Maximum creativity
""".strip(),
        default=0.1,
        ge=0.0,
        le=1.0,
    )


class OpenAICompatibleTool(BaseTool):
    name: str = "openai_compatible"
    description: str = (
        """
Base tool for OpenAI-compatible APIs, designed for complex reasoning and analysis tasks.

Key uses:
- Complex problem analysis
- Technical reasoning
- Strategic planning
- Detailed explanations
""".strip()
    )

    args_schema: type[OpenAICompatibleToolArgs] = OpenAICompatibleToolArgs

    @property
    def base_url(self) -> str:
        raise NotImplementedError

    @property
    def api_key(self) -> str:
        raise NotImplementedError

    def _get_client(self, model: str, temperature: float) -> ChatOpenAI:
        return ChatOpenAI(
            model=model,
            streaming=True,
            temperature=temperature,
            base_url=self.base_url,
            api_key=self.api_key,
        )

    def _run(self, *args, **kwargs):
        raise NotImplementedError("OpenAICompatibleTool only supports async operations")

    async def _arun(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        config: RunnableConfig,
        temperature: float = 0.1,
    ) -> str:
        try:
            client = self._get_client(model, temperature)
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt),
            ]

            response = await client.ainvoke(messages, config=config)
            return response.content
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e
