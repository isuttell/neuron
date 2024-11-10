from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from neuron_server.config import config
from neuron_server.llms.llm import LLM
from typing import Literal
from neuron_server.llms.prompts import chat_prompt
from langchain_core.runnables import Runnable


class HuggingFaceToollessLLM(LLM):
    provider: Literal["huggingface"] = "huggingface"
    executor: Runnable

    def __init__(
        self,
        repo_id: str,
        max_tokens: int = 1024,
    ):
        llm = HuggingFaceEndpoint(
            repo_id=repo_id,
            task="text-generation",
            huggingfacehub_api_token=config.hf_token,
            streaming=True,
            temperature=0.7,
            max_new_tokens=max_tokens,
        )
        model = ChatHuggingFace(llm=llm, temperature=0.7, streaming=True)
        low_temp_model = ChatHuggingFace(llm=llm, temperature=0.1, streaming=True)
        super().__init__(
            model, title_model=model, memory_model=low_temp_model, tools=[]
        )
        self.executor = chat_prompt | model
