import asyncio

import pytest
from langchain_core.runnables import RunnableConfig

from neuron_server.tools.deepseek_reasoning_tool import DeepSeekReasoningTool

pytestmark = pytest.mark.skip(reason="Temporarily disabled to avoid API calls")


@pytest.mark.asyncio
async def test_basic_reasoning() -> None:
    """Test basic reasoning without variable injection"""
    tool = DeepSeekReasoningTool()
    config = RunnableConfig(configurable={"user_id": "test", "thread_id": "test"})

    response = await tool._arun(
        system_prompt="You are an expert at analyzing software architecture",
        user_prompt=(
            "What are the key benefits of microservices? Keep the response short."
        ),
        temperature=0.1,
        config=config,
    )
    assert response and len(response) > 0, "Should return a non-empty response"


@pytest.mark.asyncio
async def test_variable_injection() -> None:
    """Test reasoning with variable injection"""
    tool = DeepSeekReasoningTool()
    config = RunnableConfig(configurable={"user_id": "test", "thread_id": "test"})

    response = await tool._arun(
        system_prompt="As a {role}, analyze {topic} considering {context}",
        user_prompt="What are the main challenges? Keep the response short.",
        user_data={
            "role": "system architect",
            "topic": "distributed databases",
            "context": "high availability requirements",
        },
        temperature=0.1,
        config=config,
    )
    assert response and len(response) > 0, "Should return a non-empty response"


if __name__ == "__main__":
    asyncio.run(test_basic_reasoning())
    print("\nBasic reasoning test completed successfully!")

    asyncio.run(test_variable_injection())
    print("\nVariable injection test completed successfully!")
