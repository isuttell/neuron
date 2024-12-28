from langchain_core.messages import trim_messages
from neuron_server.llms.prompts import (
    chat_prompt,
    title_prompt,
    memory_prompt,
)
from langchain_core.runnables import Runnable
from typing import List, Optional
from langchain_core.tools import BaseTool
from typing import Literal
from typing import (
    Annotated,
    Sequence,
    TypedDict,
)
from langchain_core.messages import BaseMessage, AIMessage
from langgraph.graph.message import add_messages
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from datetime import datetime, timezone
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.output_parsers import StrOutputParser
import re
from langchain_core.messages.utils import get_buffer_string
import tiktoken
from neuron_server.tools.memory_recall_tool import (
    MemoryRecallTool,
    MemoryStats,
    NO_MEMORIES_FOUND,
)
from neuron_server.tools.memory_store_tool import MemoryStoreTool
from neuron_server.llms.prompts import memory_prompt
from pydantic import BaseModel, Field
from neuron_server.config import config
from neuron_server.logger import logger
from neuron_server.models.embedding_model import EmbeddingModel
from neuron_server.artifacts import artifact_prompt
from neuron_server.llms.tools import default_tools


tokenizer = tiktoken.encoding_for_model("gpt-4o")


class AgentState(TypedDict):
    """The state of the agent."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    title: str = ""
    personality: str
    memory: str = ""
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
    memory_recall_rankings: List[MemoryRecallRanking] = Field(
        description="A list of existing recall memories ranked by usefulness to the response"
    )
    new_memories: List[str] = Field(
        description="A list of new details and novel information to save for later recall"
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
        title_model: Optional[Runnable] = None,
        memory_model: Optional[Runnable] = None,
    ):
        self.model = model
        self.title_model = title_model
        self.title = title_prompt | self.title_model | StrOutputParser()
        self.memory_model = memory_model
        self.memory = memory_prompt | self.memory_model | StrOutputParser()

    def create_workflow(
        self,
        tools: Optional[List[BaseTool]] = None,
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
            workflow.add_node("update_memory", self.call_update_memory)
            workflow.add_node("load_memory", self.load_memory)

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
        message_trimmer: Runnable = trim_messages(
            max_tokens=1024,
            strategy="last",
            token_counter=self.memory_model,
            include_system=False,
            allow_partial=True,
            start_on="human",
        )
        messages: List[BaseMessage] = await message_trimmer.ainvoke(
            state["messages"],
            config,
        )
        recall_memories: str = await MemoryRecallTool().ainvoke(
            {"query": get_buffer_string(messages), "k": 10},
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

        message_trimmer: Runnable = trim_messages(
            max_tokens=200000,
            strategy="last",
            token_counter=model,
            include_system=True,
            allow_partial=False,
            start_on="human",
        )
        messages: List[BaseMessage] = await message_trimmer.ainvoke(
            state["messages"],
            config,
        )
        # Filter out messages that don't have content
        initial_messages_length = len(messages)
        messages = [message for message in messages if message.content]
        if len(messages) < initial_messages_length:
            logger.debug(f"Filtered {initial_messages_length - len(messages)} messages")

        chain = chat_prompt | model
        response: AIMessage = await chain.ainvoke(
            {
                "messages": messages,
                "personality": state["personality"],
                "location": state["location"] if "location" in state else "unknown",
                "recall_memories": (
                    state["recall_memories"] if "recall_memories" in state else ""
                ),
                "now": datetime.now(timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S %Z"),
                "artifact_prompt": artifact_prompt,
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
            max_tokens=1024,
            strategy="last",
            token_counter=self.title_model,
            include_system=False,
            allow_partial=True,
            start_on="human",
        )
        messages: List[BaseMessage] = await message_trimmer.ainvoke(
            state["messages"],
            config,
        )
        title: str = await self.title.ainvoke(
            {
                "messages": get_buffer_string(messages),
                "last_title": state.get("title", ""),
                "personality": "",
                "now": datetime.now(timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S %Z"),
            },
            config,
        )
        # Strip quotes from the title
        title = re.sub(r'^([\'"])(.*)\1$', r"\2", title)
        return {"title": title}

    async def call_update_memory(
        self,
        state: AgentState,
        config: RunnableConfig,
    ):
        message_trimmer: Runnable = trim_messages(
            max_tokens=1024,
            strategy="last",
            token_counter=self.memory_model,
            include_system=False,
            allow_partial=True,
            start_on="human",
        )
        assert isinstance(message_trimmer, Runnable)
        messages: List[BaseMessage] = await message_trimmer.ainvoke(
            state["messages"],
            config,
        )
        assert isinstance(messages, list)

        model: Runnable = memory_prompt | self.memory_model.with_structured_output(
            MemoryResponse
        )

        response: MemoryResponse = await model.ainvoke(
            {
                "messages": get_buffer_string(messages),
                "recall_memories": state["recall_memories"],
                "now": datetime.now(timezone.utc)
                .astimezone()
                .strftime("%Y-%m-%d %H:%M:%S %Z"),
            },
            config,
        )
        if not response:
            logger.error("No response from memory model")
            return

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
                            datetime.now(timezone.utc).timestamp()
                        )
                        stats["useful"] += 1

                    stats["total"] += 1
                    stats["last_recall_at"] = int(
                        datetime.now(timezone.utc).timestamp()
                    )
                    stats["scores"].append(ranking.score)
                    stats["scores"] = stats["scores"][-100:]
                    document.cmetadata["stats"] = stats
                    logger.debug(
                        "Updating memory {document_id}: {useful_percentage}%".format(
                            document_id=ranking.document_id,
                            useful_percentage=round(
                                (stats["useful"] / stats["total"]) * 100
                            ),
                        )
                    )
                    await document.save()

        if len(response.new_memories) > 0:
            new_memories: List[str] = []
            for memory in response.new_memories:
                matches = await MemoryRecallTool()._arun(
                    query=memory, config=config, score_threshold=0.9, k=1
                )
                if matches == NO_MEMORIES_FOUND:
                    # If there are no matches, then we add the memory to the list
                    # to be saved later
                    new_memories.append(memory)
            if len(new_memories) > 0:
                await MemoryStoreTool().ainvoke({"memories": new_memories})

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

    def should_call_update_memory(
        self, state: AgentState
    ) -> Literal["update_memory", "continue"]:
        if len(state["messages"]) > 1:
            return "update_memory"
        else:
            return "continue"
