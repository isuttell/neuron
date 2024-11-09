from langchain_core.messages import trim_messages
from neuron_server.llms.prompts import chat_prompt, title_prompt, memory_prompt
from langchain_core.runnables import Runnable
from typing import List, Optional
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent
from langgraph.graph.graph import CompiledGraph
from typing import Literal


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
        self.chat = chat_prompt | model
        self.title = title_prompt | (title_model or model).bind_tools(tools)
        self.memory = memory_prompt | (memory_model or model).bind_tools(tools)
        self.executor = create_react_agent(tools=tools, model=model)
