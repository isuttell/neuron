import asyncio

from langchain.tools import BaseTool
from langchain_core.messages import trim_messages
from langchain_core.messages.utils import get_buffer_string
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.graph import OutputState, question_graph
from neuron_server.graph.chains import model
from neuron_server.logger import logger

message_trimmer: Runnable = trim_messages(
    max_tokens=4096,
    strategy="last",
    token_counter=model,  # Use the same model as the graph
    include_system=False,
    allow_partial=True,
    start_on="human",
)


class GraphQuestionToolArgs(BaseModel):
    question: str = Field(
        description=(
            "The question to ask or instructions to give to the graph. Be specific "
            "and give semantic context. If you're asking a question that could be "
            "interpreted in multiple ways, be specific and give context to get the "
            "most relevant answer. Include any constraints or requirements that the "
            "answer must meet. Make no assumptions in this question. Include all "
            "relevant information in the question."
        )
    )
    document_ids: list[str] | None = Field(
        description=(
            "The specific document ids to search for relevant information in otherwise "
            "the graph will search for relevant information in all documents."
        )
    )


class GraphQuestionTool(BaseTool):
    name: str = "graph_question_tool"
    description: str = """
This tool answers questions, and looks for related information from a knowledge
graph database filled with arxiv articles and other knowledge provided by the user.
Use this tool to answer questions from the graph to avoid having to load large
documents into the context window.
""".strip()
    args_schema: type[GraphQuestionToolArgs] = GraphQuestionToolArgs

    def _run(self, question: str, config: RunnableConfig) -> str:
        return asyncio.run(self._arun(question, config))

    async def _arun(
        self,
        question: str,
        config: RunnableConfig,
        document_ids: list[str] | None = None,
        recursion_limit: int = 500,
    ) -> str:
        try:
            assert "thread_id" in config["configurable"]
            logger.debug(
                f"Graph Question: {question} with document ids: {document_ids}"
            )
            from neuron_server.llms.agent import aget_state

            state = await aget_state(thread_id=config["configurable"]["thread_id"])
            messages = state.values.get("messages", [])
            history = get_buffer_string(messages)[-10000:]
            response: OutputState = await question_graph.ainvoke(
                {
                    "document_ids": document_ids,
                    "question": question,
                    # include recent history in case if includes relevant information
                    # to help better answer the question
                    "history": history,
                },
                config={
                    **config,
                    "recursion_limit": recursion_limit,
                },
            )
            return f"""
<answer>
{response["answer"]}
</answer>

<research_analysis>
{response["analysis"]}
</research_analysis>
""".strip()
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Failed to answer question: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ask a question to a graph.")
    parser.add_argument(
        "--question",
        type=str,
        help="The question to ask the graph.",
        default="Tell me about quantum blacked holes",
    )
    args = parser.parse_args()

    tool = GraphQuestionTool()
    results = tool._run(
        question=args.question,
        config={},
    )
    print(results)
