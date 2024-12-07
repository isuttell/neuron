from langchain_core.messages import trim_messages
from neuron_server.llms.prompts import (
    chat_prompt,
    title_prompt,
    memory_prompt,
)
from langchain_core.runnables import Runnable
from typing import List, Optional
from langchain_core.tools import BaseTool
from langgraph.graph.graph import CompiledGraph
from typing import Literal
from typing import (
    Annotated,
    Sequence,
    TypedDict,
)
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph.message import add_messages
import json
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from datetime import datetime, timezone
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field
from psycopg_pool import AsyncConnectionPool
from neuron_server.database import DB_URI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.output_parsers import StrOutputParser
from neuron_server.logger import logger


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    title: str = ""
    personality: str
    memory: str = ""


class LLM:
    model: Runnable
    model_with_tools: Runnable
    provider: Literal["openai", "anthropic", "huggingface"]
    chat: Runnable
    title: Runnable
    memory: Runnable
    message_trimmer: Runnable
    executor: CompiledGraph

    def __init__(
        self,
        model: Runnable,
        title_model: Optional[Runnable] = None,
        memory_model: Optional[Runnable] = None,
        max_input_tokens: int = 4096,
        tools: Optional[List[BaseTool]] = None,
    ):
        self.model = model
        self.model_with_tools = model.bind_tools(tools)
        self.message_trimmer = trim_messages(
            max_tokens=max_input_tokens,
            strategy="last",
            token_counter=model,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )
        self.chat = chat_prompt | self.model_with_tools
        self.title_model = (title_model or model).bind_tools(tools)
        self.title = title_prompt | self.title_model | StrOutputParser()
        self.memory_model = (memory_model or model).bind_tools(tools)
        self.memory = memory_prompt | self.memory_model | StrOutputParser()
        self.tools = tools

        self.workflow = StateGraph(AgentState)
        self.workflow.add_node("tools", ToolNode(tools))
        self.workflow.add_node("agent", self.call_model)
        self.workflow.add_node("update_title", self.call_title)
        self.workflow.add_node("update_memory", self.call_memory)
        self.workflow.set_entry_point("agent")
        self.workflow.add_conditional_edges(
            "agent",
            self.should_call_tools,
            {
                "tools": "tools",
                "continue": "update_title",
            },
        )
        self.workflow.add_edge("tools", "agent")
        self.workflow.add_edge("update_title", "update_memory")
        self.workflow.add_edge("update_memory", END)
        self.executor = self.workflow.compile()

    async def aget_state(
        self, config: RunnableConfig, checkpointer: AsyncPostgresSaver
    ):
        self.executor.checkpointer = checkpointer
        return await self.executor.aget_state(config)

    # Define the node that calls the model
    async def call_model(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        message_trimmer: Runnable = trim_messages(
            max_tokens=30000,
            strategy="last",
            token_counter=self.model_with_tools,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )
        messages = await message_trimmer.ainvoke(
            state["messages"],
            {**config, "run_name": "trim_messages"},
        )
        response = await self.chat.ainvoke(
            {
                "messages": messages,
                "personality": state["personality"],
                "memory": state["memory"],
                "now": datetime.now(timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S %Z"),
            },
            config,
        )
        # We return a list, because this will get added to the existing list
        return {"messages": [response]}

    async def call_title(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        message_trimmer: Runnable = trim_messages(
            max_tokens=2048,
            strategy="last",
            token_counter=self.title_model,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )
        messages = await message_trimmer.ainvoke(
            [
                *state["messages"],
                HumanMessage(
                    content="Please update the title of our conversation so I can easily find it later"
                ),
            ],
            {**config, "run_name": "trim_messages"},
        )
        response: str = await self.title.ainvoke(
            {
                "messages": messages,
                "last_title": state.get("title", ""),
                "now": datetime.now(timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S %Z"),
            },
            {**config, "run_name": "update_title"},
        )
        response = response.strip('"')
        return {"title": response}

    async def call_memory(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        message_trimmer: Runnable = trim_messages(
            max_tokens=4096,
            strategy="last",
            token_counter=self.memory_model,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )
        messages = await message_trimmer.ainvoke(
            [
                *state["messages"],
                HumanMessage(content="Please update the memory of our conversation"),
            ],
            {
                **config,
                "run_name": "trim_messages",
            },
        )
        response = await self.memory.ainvoke(
            {
                "messages": messages,
                "personality": state["personality"],
                "memory": state.get("memory", ""),
                "now": datetime.now(timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S %Z"),
            },
            {**config, "run_name": "update_memory"},
        )
        return {"memory": response}

    def should_call_tools(self, state: AgentState) -> Literal["tools", "continue"]:
        messages = state["messages"]
        last_message = messages[-1]
        assert isinstance(last_message, AIMessage)
        # If there is no function call, then we finish
        if last_message.tool_calls:
            return "tools"
        # Otherwise if there is, we continue
        else:
            return "continue"
