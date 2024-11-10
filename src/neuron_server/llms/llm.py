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
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages
import json
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from datetime import datetime, timezone
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]


class LLM:
    model: Runnable
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
        self.message_trimmer = trim_messages(
            max_tokens=max_input_tokens,
            strategy="last",
            token_counter=model,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )
        self.chat = chat_prompt | model.bind_tools(tools)
        self.title = title_prompt | (title_model or model).bind_tools(tools)
        self.memory = memory_prompt | (memory_model or model).bind_tools(tools)

        workflow = StateGraph(AgentState)
        workflow.add_node("tools", ToolNode(tools))
        workflow.add_node("agent", self.call_model)
        workflow.set_entry_point("agent")
        workflow.add_conditional_edges(
            "agent",
            self.should_continue,
            {
                "continue": "tools",
                "end": END,
            },
        )
        workflow.add_edge("tools", "agent")
        self.executor = workflow.compile()

    # Define the node that calls the model
    async def call_model(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        response = await self.chat.ainvoke(
            {
                "messages": state["messages"],
                "now": datetime.now(timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S"),
            },
            config,
        )
        # We return a list, because this will get added to the existing list
        return {"messages": [response]}

    def should_continue(self, state: AgentState) -> Literal["end", "continue"]:
        messages = state["messages"]
        last_message = messages[-1]
        assert isinstance(last_message, AIMessage)
        # If there is no function call, then we finish
        if not last_message.tool_calls:
            return "end"
        # Otherwise if there is, we continue
        else:
            return "continue"
