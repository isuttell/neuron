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
from uuid import UUID

import tiktoken
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.messages.utils import get_buffer_string
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field

from neuron_server.config import config
from neuron_server.llms.artifact_aware_tool_node import ArtifactAwareToolNode
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

# Thinking mode types and constants
ThinkingLevel = Literal["off", "low", "medium"]

# Models that support thinking mode
THINKING_SUPPORTED_MODELS = {
    "claude-sonnet-4-20250514": True,  # Latest Sonnet model with thinking support
    "claude-opus-4-20250514": True,  # Latest Opus model with thinking support
    # Add future models as they gain thinking support
}

# Token budgets for different thinking levels
THINKING_TOKEN_BUDGETS = {
    "low": 1024,
    "medium": 4096,
}


class ComplexityAnalysis(BaseModel):
    """Quick complexity analysis for thinking mode."""

    thinking_level: ThinkingLevel = Field(
        description="Required thinking level for this request"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in the assessment"
    )
    reason: str = Field(max_length=100, description="Brief reason for the choice")


class AgentState(TypedDict, total=False):
    """The state of the agent.

    Attributes:
        messages: The sequence of messages in the conversation
        username: The username of the current user (default: "user")
        title: The title of the conversation (default: "")
        personality: The personality to use for responses
        location: The user's location (default: "")
        recall_memories: Previously recalled memories (default: "")
        thinking_level: The thinking level for the current request (default: "off")
        complexity_analysis: The complexity analysis result
    """

    messages: Annotated[Sequence[BaseMessage], add_messages]
    username: str  # Optional with default "user"
    title: str  # Optional with default ""
    personality: str  # Required
    location: str  # Optional with default ""
    recall_memories: str  # Optional with default ""
    thinking_level: ThinkingLevel  # Optional with default "off"
    complexity_analysis: ComplexityAnalysis | None  # Optional


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
        fast_model: The fast model for quick operations
    """

    model: Runnable
    title: Runnable
    memory: Runnable
    memory_model: Runnable
    fast_model: Runnable | None

    def __init__(
        self,
        model: Runnable,
        model_id: str,
        fast_model: Runnable | None = None,
        memory_model: Runnable | None = None,
        provider_model_id: UUID | None = None,
    ) -> None:
        """Initialize the LLM wrapper.

        Args:
            model: The base language model
            model_id: Model ID string (e.g., "claude-3-5-sonnet-20241022")
            fast_model: Optional fast model for quick operations
            memory_model: Optional model for memory operations
            provider_model_id: Optional provider model identifier (UUID)
        """
        self.model = model
        self.model_id = model_id
        self.fast_model = fast_model
        self.title = title_prompt | self.fast_model | StrOutputParser()
        self.memory_model = memory_model
        self.memory = memory_prompt | self.memory_model | StrOutputParser()
        self.provider_model_id = provider_model_id
        self._active_tools: list[BaseTool] | None = None

    async def analyze_complexity(
        self, state: AgentState, config: RunnableConfig
    ) -> AgentState:
        """Analyze complexity only if model supports thinking."""

        # Check if the specific model supports thinking
        if not THINKING_SUPPORTED_MODELS.get(self.model_id, False):
            return {"thinking_level": "off"}

        # Check if fast model is available
        if not self.fast_model:
            logger.warning("No fast model available for complexity analysis")
            return {"thinking_level": "off"}

        messages = state.get("messages", [])
        if not messages:
            return {"thinking_level": "off"}

        # Handle None content safely
        latest_message = ""
        if messages and messages[-1].content:
            content = messages[-1].content
            # Handle both string and list content types
            if isinstance(content, str):
                latest_message = content
            elif isinstance(content, list):
                # Extract text from list content (e.g., multimodal messages)
                text_parts = []
                for item in content:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                latest_message = " ".join(text_parts)
            else:
                # Fallback for other types
                latest_message = str(content)

        # Quick prompt for thinking level
        analysis_prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """Quickly assess the thinking level needed:

"off": Simple questions, factual queries, basic tasks
"low": Moderate analysis, straightforward multi-step problems
"medium": Complex reasoning, deep analysis, creative challenges

Most requests should be "off". Use "low" when some analysis helps.
Reserve "medium" for truly complex problems.

Consider user intent - if they explicitly ask for careful analysis or thinking,
lean towards "low" or "medium".""",
                ),
                ("human", "{message}"),
            ]
        )

        try:
            chain = analysis_prompt | self.fast_model.with_structured_output(
                ComplexityAnalysis
            )
            analysis = await chain.ainvoke({"message": latest_message}, config)

            return {
                "thinking_level": analysis.thinking_level,
                "complexity_analysis": analysis,
            }
        except Exception as e:
            logger.warning(f"Complexity analysis failed: {e}")
            return {"thinking_level": "off"}

    async def _dynamic_agent_node(
        self, state: AgentState, config: RunnableConfig
    ) -> AgentState:
        """Agent node that dynamically creates model with thinking config."""

        thinking_level = state.get("thinking_level", "off")
        analysis = state.get("complexity_analysis")

        if analysis:
            logger.debug(
                f"Using thinking level: {thinking_level} "
                f"(confidence: {analysis.confidence}, reason: {analysis.reason})"
            )

        # Create model with appropriate configuration
        model = self._create_model_with_thinking(
            thinking_level=thinking_level, tools=self._active_tools
        )

        return await self.call_model(model, state, config)

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

        # Store tools for dynamic configuration
        self._active_tools = active_tools or []

        # Add tools to our custom ToolNode that handles artifacts
        workflow.add_node("tools", ArtifactAwareToolNode(active_tools))
        workflow.add_node("analyze_complexity", self.analyze_complexity)
        workflow.add_node("agent", self._dynamic_agent_node)
        workflow.add_node("update_title", self.call_title)

        if config.memory_enabled:
            workflow.add_node("load_memory", self.load_memory)
            workflow.add_node("update_memory", self.call_update_memory)
        # Entry point
        if config.memory_enabled:
            workflow.set_entry_point("load_memory")
            workflow.add_edge("load_memory", "analyze_complexity")
        else:
            workflow.set_entry_point("analyze_complexity")

        # Add edge from complexity analysis to agent
        workflow.add_edge("analyze_complexity", "agent")

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

        # Filter out empty AIMessages that are not the last message
        filtered_messages = []
        for i, msg in enumerate(messages):
            if isinstance(msg, AIMessage) and not msg.content and i < len(messages) - 1:
                # Log the full message being filtered
                logger.warning(
                    f"Filtering out empty AIMessage at index {i}/{len(messages) - 1}: "
                    f"{msg.model_dump()}"
                )
            else:
                filtered_messages.append(msg)

        messages = filtered_messages

        # Apply caching if enabled
        if getattr(self, "caching_enabled", False):
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

    def _create_model_with_thinking(
        self, thinking_level: ThinkingLevel, tools: list[BaseTool]
    ) -> Runnable:
        """Base implementation - override in provider-specific classes."""
        # Default implementation just binds tools if they exist
        if tools:
            return self.model.bind_tools(tools)
        return self.model

    def should_call_tools(self, state: AgentState) -> Literal["tools", "continue"]:
        """Determine if tools should be called based on the last message.

        Args:
            state: The current agent state

        Returns:
            "tools" if tools should be called, "continue" otherwise
        """
        messages = state.get("messages", [])
        last_message = messages[-1]
        # Only check for tool calls if it's an AIMessage
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        # Otherwise continue
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
