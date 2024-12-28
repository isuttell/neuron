from langchain.tools import BaseTool
from neuron_server.logger import logger
from pydantic import BaseModel, Field
from typing import Type
import asyncio
from langchain_core.runnables import RunnableConfig
from neuron_server.graph import process_document, get_document, encode_md5
import os
import time
import pymupdf4llm
from neuron_server.config import config as neuron_config
import aiohttp


class GraphPDFImportToolArgs(BaseModel):
    pdf_url: str = Field(description="The url of the PDF file to import.")


class GraphPDFImportTool(BaseTool):
    name: str = "pdf_graph_import"
    description: str = (
        """
Use this tool to import PDF files into the knowledge graph or check if a url has already been imported. Be aware that this is a can be a slow process depending on the size of the PDF file.
""".strip()
    )
    args_schema: Type[GraphPDFImportToolArgs] = GraphPDFImportToolArgs

    def _run(self, pdf_url: str, config: RunnableConfig) -> str:
        return asyncio.run(self._arun(pdf_url, config))

    async def _arun(
        self,
        pdf_url: str,
        config: RunnableConfig,
    ) -> str:
        if ".pdf" not in pdf_url:
            raise ValueError("pdf_url must end with '.pdf'")
        pdf_path = os.path.abspath(
            os.path.join(neuron_config.temp_folder, f"{encode_md5(pdf_url)}.pdf")
        )
        try:
            personality_id = config["configurable"].get("personality_id")
            assert personality_id is not None
            # Record the start time for performance measurement
            start_time = time.perf_counter()

            # Create a unique document ID for the article
            document_id = f"pdf:{encode_md5(pdf_url)}"

            # Check if the document already exists in the graph
            document = get_document(document_id, personality_id=personality_id)
            if document:
                return f"""PDF {pdf_url} already exists in knowledge graph. Skipping import."""

            # Log the processing of the article
            logger.debug(f"Processing {pdf_url}")

            # Download the PDF to a temporary directory

            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url) as response:
                    response.raise_for_status()
                    with open(pdf_path, "wb") as f:
                        while True:
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            f.write(chunk)

            # Convert the PDF to markdown text
            text = pymupdf4llm.to_markdown(str(pdf_path), show_progress=True)

            # Process the document and add it to the graph
            await process_document(
                text=text,
                document_id=document_id,
                source=pdf_url,
                config=config,
            )
            duration = time.perf_counter() - start_time
            logger.debug(f"Processed '{pdf_url}' - {duration:.2f}s")
            return f"Processed '{pdf_url}' - {duration:.2f}s"
        except Exception as e:
            logger.exception(e)
            raise e
        finally:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Import an arxiv article into the graph."
    )
    parser.add_argument(
        "--arxiv_id",
        type=str,
        help="The arxiv id of the article to import.",
        default="2412.14455",
    )
    args = parser.parse_args()

    tool = GraphPDFImportTool()
    results = tool._run(
        arxiv_id=args.arxiv_id,
    )
    print(results)
