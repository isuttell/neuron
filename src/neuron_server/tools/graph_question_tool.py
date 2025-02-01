import asyncio

from langchain.tools import BaseTool
from langchain_core.messages import BaseMessage, trim_messages
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


class GraphQuestionTool(BaseTool):
    name: str = "graph_question_tool"
    description: str = """
This tool answers questions, and looks for related information from a knowledge
graph database filled with arxiv articles and other knowledge. Use this tool to
answer deep questions from the graph. Make sure to include as many details as
possible in the question. This may take a while and use a lot of tokens so reuse
past results in the history if possible when answering follow up questions.
""".strip()
    args_schema: type[GraphQuestionToolArgs] = GraphQuestionToolArgs

    def _run(self, question: str, config: RunnableConfig) -> str:
        return asyncio.run(self._arun(question, config))

    async def _arun(
        self,
        question: str,
        config: RunnableConfig,
        recursion_limit: int = 500,
    ) -> str:
        try:
            assert "thread_id" in config["configurable"]
            logger.debug(f"Graph Question: {question}")
            from neuron_server.llms.agent import aget_state

            state = await aget_state(thread_id=config["configurable"]["thread_id"])
            messages: list[BaseMessage] = await message_trimmer.ainvoke(
                state.values.get("messages", []),
                config,
            )
            history = get_buffer_string(messages)
            response: OutputState = await question_graph.ainvoke(
                {
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
