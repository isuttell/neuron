from typing import Literal

from langchain_google_genai import ChatGoogleGenerativeAI

from neuron_server.llms.llm import LLM


class GoogleLLM(LLM):
    provider: Literal["google"] = "google"

    def __init__(
        self,
        model_id: str | None = "gemini-2.5-pro-preview-03-25",
        provider_model_id: str | None = None,
    ) -> None:
        model = ChatGoogleGenerativeAI(
            model=model_id,
            temperature=1,
            max_tokens=None,
        )
        fast_model = ChatGoogleGenerativeAI(
            model=model_id,
            temperature=1,
        )
        memory_model = ChatGoogleGenerativeAI(
            model=model_id,
            temperature=0.3,
        )
        super().__init__(
            model,
            fast_model,
            memory_model,
            provider_model_id=provider_model_id,
        )
