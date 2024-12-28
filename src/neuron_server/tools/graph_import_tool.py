from langchain.tools import BaseTool
from neuron_server.logger import logger
from pydantic import BaseModel, Field
from typing import Type
import asyncio
from langchain_core.runnables import RunnableConfig
from neuron_server.graph import process_document, encode_md5
import time


class GraphImportToolArgs(BaseModel):
    text: str = Field(description="The text to import into the knowledge graph.")


class GraphImportTool(BaseTool):
    name: str = "graph_import"
    description: str = (
        """
Use this tool to import text into the knowledge graph for long term memory.
""".strip()
    )
    args_schema: Type[GraphImportToolArgs] = GraphImportToolArgs

    def _run(self, text: str, config: RunnableConfig) -> str:
        return asyncio.run(self._arun(text, config))

    async def _arun(
        self,
        text: str,
        config: RunnableConfig,
    ) -> str:
        try:
            personality_id = config["configurable"].get("personality_id")
            assert personality_id is not None
            start_time = time.perf_counter()
            # Process the document and add it to the graph
            await process_document(
                text=text,
                document_id=f"text:{encode_md5(text.strip())}",
                config=config,
            )
            duration = time.perf_counter() - start_time
            return f"""Added text to knowledge graph in {round(duration)} seconds"""
        except Exception as e:
            logger.exception(e)
            raise e


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Import text into the graph.")
    parser.add_argument(
        "--text",
        type=str,
        help="The text to import into the graph.",
        default="Hello, world!",
    )
    args = parser.parse_args()

    tool = GraphImportTool()
    results = tool._run(
        text=args.text,
    )
    print(results)
