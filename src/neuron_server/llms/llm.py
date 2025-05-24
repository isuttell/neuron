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


class AgentState(TypedDict, total=False):
    """The state of the agent.

    Attributes:
        messages: The sequence of messages in the conversation
        username: The username of the current user (default: "user")
        title: The title of the conversation (default: "")
        personality: The personality to use for responses
        location: The user's location (default: "")
        recall_memories: Previously recalled memories (default: "")
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    username: str  # Optional with default "user"
    title: str  # Optional with default ""
    personality: str  # Required
    location: str  # Optional with default ""
    recall_memories: str  # Optional with default ""


class MemoryRecallRanking(BaseModel):
    document_id: str = Field(description="The ID of the memory recall document")
    score: float = Field(
        description="Give each recall memory a score from 1 to 10 based on how useful"
        "it was in constructing the last AI message"
    )
    useful: bool = Field(
        description="True if the memory was useful in constructing the last AI message"
    )


class MemoryResponse(BaseModel):
    memory_recall_rankings: list[MemoryRecallRanking] = Field(
        description="A list of existing recall memories ranked by"
        "usefulness to the response"
    )


class LLM:
    """Language model wrapper for chat interactions.

    Attributes:
        model: The base language model
        title: The title generation pipeline
        memory: The memory generation pipeline
        memory_model: The memory model for ranking
        title_model: The model for generating titles
    """

    model: Runnable
    title: Runnable
    memory: Runnable
    memory_model: Runnable
    title_model: Runnable | None

    def __init__(
        self,
        model: Runnable,
        title_model: Runnable | None = None,
        memory_model: Runnable | None = None,
        provider_model_id: str | None = None,
    ) -> None:
        """Initialize the LLM wrapper.

        Args:
            model: The base language model
            title_model: Optional model for generating titles
            memory_model: Optional model for memory operations
            provider_model_id: Optional provider model identifier
        """
        self.model = model
        self.title_model = title_model
        self.title = title_prompt | self.title_model | StrOutputParser()
        self.memory_model = memory_model
        self.memory = memory_prompt | self.memory_model | StrOutputParser()
        self.provider_model_id = provider_model_id

    def create_workflow(
        self,
        tools: list[BaseTool] | None = None,
    ) -> StateGraph:
        """Create a workflow for processing messages.

        Args:
            tools: Optional list of tools to bind to the model

        Returns:
            Compiled state graph for message processing
        """
        workflow = StateGraph(AgentState)
        active_tools = tools or default_tools
        
        # Separate native tools from BaseTool instances
        native_tools = []
        
        # Add Anthropic native web search if this is an Anthropic model
        if hasattr(self, 'provider') and self.provider == 'anthropic':
            web_search_tool = {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 10
            }
            native_tools.append(web_search_tool)
        
        # Bind all tools (BaseTool instances + native tools) to the model
        all_tools = list(active_tools) + native_tools
        model = self.model.bind_tools(all_tools)
        
        # Only add BaseTool instances to ToolNode
        # Native tools are handled directly by the model
        workflow.add_node("tools", ToolNode(active_tools))

        async def agent_node(state: AgentState, config: RunnableConfig) -> AgentState:
            # pass the model with the tools into the call_model function
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
    ) -> AgentState:
        """Load recall memories for the conversation.

        Args:
            state: The current agent state
            config: The runnable configuration

        Returns:
            Updated agent state with loaded memories
        """
        logger.debug("Loading recall memories...")
        messages = [
            msg
            for msg in state.get("messages", [])
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
    ) -> AgentState:
        """Get the current state of the workflow.

        Args:
            config: The runnable configuration
            checkpointer: The async postgres saver for checkpointing

        Returns:
            Current state of the workflow
        """
        graph = self.create_workflow()
        graph.checkpointer = checkpointer
        return await graph.aget_state(config)

    def _apply_caching_to_messages(
        self, messages: Sequence[BaseMessage]
    ) -> Sequence[BaseMessage]:
        """Apply caching to messages if this LLM supports it.

        This method can be overridden by specific LLM implementations.
        The default implementation returns messages unchanged.

        Args:
            messages: The original messages

        Returns:
            Messages with caching applied (if supported)
        """
        return messages

    async def call_model(
        self,
        model: Runnable,
        state: AgentState,
        config: RunnableConfig,
    ) -> AgentState:
        """Call the language model with the current state.

        Args:
            model: The language model to use
            state: The current agent state
            config: The runnable configuration

        Returns:
            Updated agent state with model response
        """
        # Filter out messages that don't have content
        messages = state.get("messages", [])

        # Apply caching if enabled
        if getattr(self, 'caching_enabled', False):
            messages = self._apply_caching_to_messages(messages)

        chain = chat_prompt | model
        logger.debug("Invoking model...")
        response: AIMessage = await chain.ainvoke(
            {
                "messages": messages,
                "personality": state.get("personality", ""),
                "location": state.get("location", "unknown"),
                "username": state.get("username", "user"),
                "recall_memories": state.get("recall_memories", ""),
                "now": datetime.now().astimezone().isoformat(timespec="seconds"),
            },
            config,
        )

        # Set the message ID if provided in config (for consistency with streaming)
        ai_message_id = config.get("configurable", {}).get("ai_message_id")
        if ai_message_id:
            response.id = ai_message_id

        response.created_at = datetime.now().astimezone().isoformat()

        # Log non-standard finish reasons
        finish_reason = response.response_metadata.get("finish_reason")
        # Common reasons are 'stop', 'tool_calls', 'length'
        # Log if it's something potentially problematic like 'length'
        if finish_reason and finish_reason not in ["stop", "tool_calls"]:
            logger.warning(f"Model finished with reason: {finish_reason}. ")

        # We return a list, because this will get added to the existing list
        return {"messages": [response]}

    async def call_title(
        self,
        state: AgentState,
        config: RunnableConfig,
    ) -> AgentState:
        """Update the conversation title.

        Args:
            state: The current agent state
            config: The runnable configuration

        Returns:
            Updated agent state with new title
        """
        logger.debug("Updating title...")
        messages = [
            msg
            for msg in state.get("messages", [])
            if not isinstance(msg, ToolMessage) and getattr(msg, "tool_calls", []) == []
        ]
        title: str = await self.title.ainvoke(
            {
                "messages": get_buffer_string(messages),
                "last_title": state.get("title", ""),
                "now": datetime.now().astimezone().isoformat(),
            },
        )
        # Strip quotes from the title
        title = re.sub(r'^([\'"])(.*)\1$', r"\2", title)
        return {"title": title}

    async def rank_memories(
        self,
        state: AgentState,
        config: RunnableConfig,
    ) -> AgentState:
        """Rank and update memory statistics.

        Args:
            state: The current agent state
            config: The runnable configuration

        Returns:
            Updated agent state with ranked memories
        """
        logger.debug("Ranking memories...")
        start_time = time.perf_counter()
        messages = [
            msg
            for msg in state.get("messages", [])
            if not isinstance(msg, ToolMessage) and getattr(msg, "tool_calls", []) == []
        ]

        model: Runnable = memory_prompt | self.memory_model.with_structured_output(
            MemoryResponse
        )

        response: MemoryResponse = await model.ainvoke(
            {
                "messages": get_buffer_string(messages),
                "recall_memories": state.get("recall_memories", ""),
                "now": datetime.now().astimezone().isoformat(),
            },
            config,
        )

        if isinstance(response, dict):
            response = MemoryResponse(**response)

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
                        stats["last_useful_at"] = int(datetime.now(UTC).timestamp())
                        stats["useful"] += 1

                    stats["total"] += 1
                    stats["last_recall_at"] = int(datetime.now(UTC).timestamp())
                    stats["scores"].append(ranking.score)
                    stats["scores"] = stats["scores"][-100:]
                    document.cmetadata["stats"] = stats
                    await document.save()
            logger.debug(
                f"{len(response.memory_recall_rankings)} memories ranked "
                f"in {time.perf_counter() - start_time:.2f}s"
            )

    async def call_update_memory(
        self,
        state: AgentState,
        config: RunnableConfig,
    ) -> AgentState:
        """Update memory rankings asynchronously.

        Args:
            state: The current agent state
            config: The runnable configuration

        Returns:
            The unchanged agent state
        """
        # Schedule ranking memories task in background
        asyncio.create_task(self.rank_memories(state, config))

    def should_call_tools(self, state: AgentState) -> Literal["tools", "continue"]:
        """Determine if tools should be called based on the last message.

        Args:
            state: The current agent state

        Returns:
            "tools" if tools should be called, "continue" otherwise
        """
        messages = state.get("messages", [])
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
        """Determine if memory should be updated.

        Args:
            state: The current agent state

        Returns:
            "update_memory" if memory should be updated, "continue" otherwise
        """
        if len(state.get("recall_memories", "")) > 0:
            return "update_memory"
        return "continue"
