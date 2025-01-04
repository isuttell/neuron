from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import asyncio
from neuron_server.vectorstores import document_store
from langchain_core.runnables import RunnableConfig
from langchain_core.documents import Document
import json


def format_document(doc: Document) -> str:
    return f"""
    <document>
        <document_content>{doc.page_content}</document_content>
        <document_metadata>{json.dumps(doc.metadata or {})}</document_metadata>
    </document>
""".strip()


class DocumentQueryToolArgs(BaseModel):
    query: str = Field(
        description="The semantic query to search for in the documents",
    )
    k: int = Field(
        description="The maximum number of documents to return", default=10, min=1
    )


class DocumentQueryTool(BaseTool):
    name: str = "query_documents"
    description: str = (
        "This tool allows you to query documents for information relevant to a question using a semantic search."
    )

    args_schema: Type[DocumentQueryToolArgs] = DocumentQueryToolArgs

    def _run(
        self,
        *args,
        **kwargs,
    ):
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        query: str,
        config: RunnableConfig,
        k: int = 10,
    ) -> str:
        assert "personality_id" in config["configurable"]
        # Always filter by personality
        doc_filter = {"personality_id": config["configurable"]["personality_id"]}
        docs = await document_store.asimilarity_search_with_relevance_scores(
            query,
            k=k,
            filter=doc_filter,
        )
        if len(docs) == 0:
            return "No documents found"

        return (
            "<documents>\n"
            + "\n".join([format_document(doc) for doc, _ in docs])
            + "\n</documents>"
        )
