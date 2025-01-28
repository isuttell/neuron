import asyncio
import re
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import (
    Annotated,
    Literal,
    TypedDict,
)

import tiktoken
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.messages.utils import get_buffer_string
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel, Field

from neuron_server.config import config
from neuron_server.llms.prompts import (
    chat_prompt,
    memory_prompt,
    title_prompt,
)
from neuron_server.llms.tools import default_tools
from neuron_server.logger import logger
from neuron_server.models.embedding_model import EmbeddingModel
from neuron_server.tools.memory_recall_tool import (
    MemoryRecallTool,
    MemoryStats,
)

tokenizer = tiktoken.encoding_for_model("gpt-4o")


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    username: str = "user"
    title: str = ""
    personality: str
    location: str = ""
    recall_memories: str = ""


class MemoryRecallRanking(BaseModel):
    document_id: str = Field(description="The ID of the memory recall document")
    score: float = Field(
        description="Give each recall memory a score from 1 to 10 based on how useful it was in constructing the last AI message"
    )
    useful: bool = Field(
        description="True if the memory was useful in constructing the last AI message"
    )


class MemoryResponse(BaseModel):
    memory_recall_rankings: list[MemoryRecallRanking] = Field(
        description="A list of existing recall memories ranked by usefulness to the response"
    )


class LLM:
    model: Runnable
    provider: str
    chat: Runnable
    title: Runnable
    memory: Runnable
    memory_model: Runnable
    message_trimmer: Runnable

    def __init__(
        self,
        model: Runnable,
        title_model: Runnable | None = None,
        memory_model: Runnable | None = None,
        provider_model_id: str | None = None,
    ):
        self.model = model
        self.title_model = title_model
        self.title = title_prompt | self.title_model | StrOutputParser()
        self.memory_model = memory_model
        self.memory = memory_prompt | self.memory_model | StrOutputParser()
        self.provider_model_id = provider_model_id

    def create_workflow(
        self,
        tools: list[BaseTool] | None = None,
    ):
        workflow = StateGraph(AgentState)
        model = self.model.bind_tools(tools or default_tools)
        workflow.add_node("tools", ToolNode(tools or default_tools))

        async def agent_node(state, config):
            # pass the model ith the tools into the call_model function
            return await self.call_model(model, state, config)

        workflow.add_node("agent", agent_node)
        workflow.add_node("update_title", self.call_title)

        if config.memory_enabled:
            workflow.add_node("load_memory", self.load_memory)
            workflow.add_node("update_memory", self.call_update_memory)
        # Entry point
        if config.memory_enabled:
            workflow.set_entry_point("load_memory")
            workflow.add_edge("load_memory", "agent")
        else:
            workflow.set_entry_point("agent")

        workflow.add_conditional_edges(
            "agent",
            self.should_call_tools,
            {
                "tools": "tools",
                "continue": "update_title",
            },
        )
        workflow.add_edge("tools", "agent")

        if config.memory_enabled:
            workflow.add_conditional_edges(
                "update_title",
                self.should_call_update_memory,
                {
                    "update_memory": "update_memory",
                    "continue": END,
                },
            )
            workflow.add_edge("update_memory", END)
        else:
            workflow.add_edge("update_title", END)

        return workflow.compile()

    async def load_memory(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        logger.debug("Loading recall memories...")
        messages = [
            msg
            for msg in state["messages"]
            if not isinstance(msg, ToolMessage) and getattr(msg, "tool_calls", []) == []
        ]
        tokens = tokenizer.encode(get_buffer_string(messages))[-1000:]
        messages = tokenizer.decode(tokens)

        recall_memories: str = await MemoryRecallTool().ainvoke(
            {"query": messages, "k": 10},
            config,
        )

        return {
            "recall_memories": recall_memories,
        }

    async def aget_state(
        self, config: RunnableConfig, checkpointer: AsyncPostgresSaver
    ):
        graph = self.create_workflow()
        graph.checkpointer = checkpointer
        return await graph.aget_state(config)

    # Define the node that calls the model
    async def call_model(
        self,
        model: Runnable,
        state: AgentState,
        config: RunnableConfig,
    ):
        # Filter out messages that don't have content
        messages = state["messages"]

        chain = chat_prompt | model
        logger.debug("Invoking model...")
        response: AIMessage = await chain.ainvoke(
            {
                "messages": messages,
                "personality": state["personality"],
                "location": state["location"] if "location" in state else "unknown",
                "username": state["username"] if "username" in state else "user",
                "recall_memories": (
                    state["recall_memories"] if "recall_memories" in state else ""
                ),
                "now": datetime.now().astimezone().isoformat(timespec="seconds"),
            },
            config,
        )
        response.created_at = datetime.now().astimezone().isoformat()
        # We return a list, because this will get added to the existing list
        return {"messages": [response]}

    async def call_title(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        logger.debug("Updating title...")
        messages = [
            msg
            for msg in state["messages"]
            if not isinstance(msg, ToolMessage) and getattr(msg, "tool_calls", []) == []
        ]
        title: str = await self.title.ainvoke(
            {
                "messages": get_buffer_string(messages),
                "last_title": state.get("title", ""),
                "now": datetime.now().astimezone().isoformat(),
            },
            config,
        )
        # Strip quotes from the title
        title = re.sub(r'^([\'"])(.*)\1$', r"\2", title)
        return {"title": title}

    async def rank_memories(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        logger.debug("Ranking memories...")
        start_time = time.perf_counter()
        messages = [
            msg
            for msg in state["messages"]
            if not isinstance(msg, ToolMessage) and getattr(msg, "tool_calls", []) == []
        ]

        model: Runnable = memory_prompt | self.memory_model.with_structured_output(
            MemoryResponse
        )

        response: MemoryResponse = await model.ainvoke(
            {
                "messages": get_buffer_string(messages),
                "recall_memories": state["recall_memories"],
                "now": datetime.now().astimezone().isoformat(),
            },
            config,
        )

        if len(response.memory_recall_rankings) > 0:
            for ranking in response.memory_recall_rankings:
                document = await EmbeddingModel.get(ranking.document_id)
                if document:
                    stats: MemoryStats = document.cmetadata.get(
                        "stats",
                        MemoryStats(
                            useful=0,
                            total=0,
                            last_useful_at=None,
                            last_recall_at=None,
                            scores=[],
                        ),
                    )

                    if ranking.useful:
                        stats["last_useful_at"] = int(
                            datetime.now(UTC).timestamp()
                        )
                        stats["useful"] += 1

                    stats["total"] += 1
                    stats["last_recall_at"] = int(
                        datetime.now(UTC).timestamp()
                    )
                    stats["scores"].append(ranking.score)
                    stats["scores"] = stats["scores"][-100:]
                    document.cmetadata["stats"] = stats
                    await document.save()
            logger.debug(
                f"{len(response.memory_recall_rankings) } memories ranked - {time.perf_counter() - start_time:.2f}s"
            )

    async def call_update_memory(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        # call but don't wait for it to finish
        asyncio.create_task(self.rank_memories(state, config))

    def should_call_tools(self, state: AgentState) -> Literal["tools", "continue"]:
        messages = state["messages"]
        last_message = messages[-1]
        assert isinstance(last_message, AIMessage)
        # If there is no function call, then we finish
        if last_message.tool_calls:
            return "tools"
        # Otherwise if there is, we continue
        return "continue"

    def should_call_update_memory(
        self, state: AgentState
    ) -> Literal["update_memory", "continue"]:
        if len(state["recall_memories"]) > 0:
            return "update_memory"
        return "continue"
