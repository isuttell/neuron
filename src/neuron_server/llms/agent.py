from neuron_server.logger import logger
from typing import List, TypedDict
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.models.personality_model import PersonalityModel
from uuid import UUID
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from datetime import datetime, timezone
from langgraph.prebuilt import create_react_agent
from neuron_server.llms.message import get_message_content
from langchain.tools import BaseTool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from neuron_server.database import pool

connection_kwargs = {
    "autocommit": True,
    "prepare_threshold": 0,
}


class ThreadConfig(TypedDict):
    thread_id: str


class AgentConfig(TypedDict):
    run_name: str
    configurable: ThreadConfig


async def execute_agent(
    prompt: str,
    config: AgentConfig,
    provider_id: UUID,
    personality_id: UUID,
    tools: List[BaseTool],
) -> str:

    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    provider = await ProviderModelModel.get(provider_id)
    if provider is None:
        raise Exception("Provider not found")
    llm = provider.to_llm()
    personality = await PersonalityModel.get(personality_id)
    if personality is None:
        raise Exception("Personality not found")

    llm.executor.checkpointer = checkpointer

    result: AIMessage = await llm.executor.ainvoke(
        {
            "messages": [
                HumanMessage(content=prompt),
            ],
            "personality": personality.context,
            "now": datetime.now(timezone.utc)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S"),
        },
        config=config,
    )
    result: AIMessage = result["messages"][-1]
    assert isinstance(result, AIMessage)
    content = (get_message_content(result) or "").strip()
    logger.debug(f"Agent {config['run_name']} returned: {content}")
    return content


async def aget_state(thread_id: UUID, provider_id: UUID):
    checkpointer = AsyncPostgresSaver(pool)
    provider = await ProviderModelModel.get(provider_id)
    if provider is None:
        raise Exception("Provider not found")
    llm = provider.to_llm()
    return await llm.aget_state(
        {"configurable": {"thread_id": str(thread_id)}}, checkpointer=checkpointer
    )
