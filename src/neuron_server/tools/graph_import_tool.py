import asyncio
import time

import tiktoken
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.graph import encode_md5, process_document
from neuron_server.logger import logger

encoder = tiktoken.encoding_for_model("gpt-4o")


class GraphImportToolArgs(BaseModel):
    text: str = Field(
        description="The full unabridged text to import into the knowledge graph."
    )


class GraphImportTool(BaseTool):
    name: str = "graph_import"
    description: str = """
Use this tool to import text into the knowledge graph for long term memory.
""".strip()
    args_schema: type[GraphImportToolArgs] = GraphImportToolArgs

    def _run(self, text: str, config: RunnableConfig) -> str:
        return asyncio.run(self._arun(text, config))

    async def _arun(
        self,
        text: str,
        config: RunnableConfig,
    ) -> str:
        try:
            start_time = time.perf_counter()
            # Process the document and add it to the graph
            doc_result = await process_document(
                text=text,
                document_id=f"text:{encode_md5(text.strip())}",
                config=config,
            )
            duration = time.perf_counter() - start_time
            keywords = ", ".join(doc_result.keywords)
            token_count = len(encoder.encode(text))
            return f"""
# Graph Import Result

Added text to knowledge graph in {round(duration)} seconds

## Document {doc_result.document_id}

* **Name:** {doc_result.document_name or "unknown"}
* **Source:** {doc_result.source or "unknown"}
* **Keywords:** {keywords or "None"}
* **Tokens:** {token_count:,}

### Summary

{doc_result.summary}

### Analysis

{doc_result.analysis}
"""
        except Exception as e:
            logger.error(e, exc_info=True)
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
