"""Tool for deleting documents from the Neo4j knowledge graph database.

This module provides a LangChain tool for safely deleting documents and their
related nodes from the Neo4j knowledge graph, with permission validation by
personality_id.
"""

import asyncio
from typing import Any

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.graph.connection import get_graph
from neuron_server.logger import logger


class GraphDocumentDeleteToolArgs(BaseModel):
    """Arguments for the Neo4j graph document delete tool."""

    document_id: str = Field(
        description="The ID of the document to delete from the knowledge graph",
        min_length=1,
    )


class GraphDocumentDeleteTool(BaseTool):
    """Tool for deleting documents from the knowledge graph database.

    This tool provides safe deletion of documents and their related nodes
    (chunks and atomic facts) from the knowledge graph, with proper permission
    validation by personality_id.
    """

    name: str = "graph_document_delete_tool"
    description: str = """
This tool permanently deletes documents from the knowledge graph database.
Document deletion is restricted by personality.

Features:
- Deletes documents by ID with permission validation
- Cascades deletion to related chunks and atomic facts
- Verifies ownership via personality_id before deletion
- Returns confirmation with count of deleted nodes
- Safe error handling for non-existent or unauthorized documents

WARNING: This operation is irreversible. Once a document is deleted,
it cannot be recovered along with all its related chunks and atomic facts.

Usage:
- Provide the document_id of the document to delete
- The tool will verify the document belongs to the current personality
- If authorized, it will delete the document and all related nodes
""".strip()
    args_schema: type[GraphDocumentDeleteToolArgs] = GraphDocumentDeleteToolArgs

    def _run(
        self,
        document_id: str,
        config: RunnableConfig,
    ) -> str:
        """Delete document synchronously."""
        return asyncio.run(self._arun(document_id, config))

    async def _arun(
        self,
        document_id: str,
        config: RunnableConfig,
    ) -> str:
        """Delete document asynchronously.

        Args:
            document_id: The ID of the document to delete
            config: Runnable configuration containing personality_id

        Returns:
            A formatted string containing the deletion result or error message
        """
        try:
            # Extract personality_id from config
            personality_id = config["configurable"].get("personality_id")
            if not personality_id:
                return """
<document_delete_result>
    <status>error</status>
    <error_message>Missing personality_id in configuration</error_message>
</document_delete_result>
""".strip()

            # Validate and prepare parameters
            params: dict[str, Any] = {
                "document_id": document_id,
                "personality_id": personality_id,
            }

            # Log the deletion attempt
            logger.debug(f"Attempting to delete document: {document_id}")
            logger.debug(f"For personality: {personality_id}")

            # First, check if the document exists and belongs to the personality
            check_query = """
MATCH (d:Document {id: $document_id, personality_id: $personality_id})
RETURN d.id, d.name, d.source
"""

            check_results = get_graph().query(check_query, params=params)

            if not check_results:
                error_msg = (
                    f"Document not found or access denied. Document ID: {document_id}"
                )
                return f"""
<document_delete_result>
    <status>error</status>
    <error_message>{error_msg}</error_message>
</document_delete_result>
""".strip()

            # Get document info for confirmation
            doc_info = check_results[0]
            doc_name = doc_info.get("d.name", "N/A")
            doc_source = doc_info.get("d.source", "N/A")

            # Delete the document and count related nodes
            delete_query = """
MATCH (d:Document {id: $document_id, personality_id: $personality_id})
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
OPTIONAL MATCH (c)-[:HAS_FACT]->(f:AtomicFact)
WITH d, collect(DISTINCT c) as chunks, collect(DISTINCT f) as facts
WITH d, chunks, facts, size(chunks) as chunk_count, size(facts) as fact_count
DETACH DELETE d
FOREACH (chunk in chunks | DETACH DELETE chunk)
FOREACH (fact in facts | DETACH DELETE fact)
RETURN chunk_count, fact_count
"""

            delete_results = get_graph().query(delete_query, params=params)

            if not delete_results:
                return f"""
<document_delete_result>
    <status>error</status>
    <error_message>Failed to delete document: {document_id}</error_message>
</document_delete_result>
""".strip()

            # Get deletion counts
            result = delete_results[0]
            chunk_count = result.get("chunk_count", 0)
            fact_count = result.get("fact_count", 0)

            logger.info(
                f"Successfully deleted document {document_id} with {chunk_count} chunks"
                f" and {fact_count} facts"
            )

            return f"""
<document_delete_result>
    <status>success</status>
    <message>Document successfully deleted</message>
    <deleted_document>
        <id>{document_id}</id>
        <name>{doc_name or "N/A"}</name>
        <source>{doc_source or "N/A"}</source>
    </deleted_document>
    <deletion_summary>
        <documents_deleted>1</documents_deleted>
        <chunks_deleted>{chunk_count}</chunks_deleted>
        <facts_deleted>{fact_count}</facts_deleted>
        <total_nodes_deleted>{1 + chunk_count + fact_count}</total_nodes_deleted>
    </deletion_summary>
</document_delete_result>
""".strip()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error deleting document {document_id}: {error_msg}")
            return f"""
<document_delete_result>
    <status>error</status>
    <error_message>{error_msg}</error_message>
    <document_id>{document_id}</document_id>
</document_delete_result>
""".strip()


if __name__ == "__main__":
    # Example usage
    tool = GraphDocumentDeleteTool()

    # Example: Delete a document
    config = {"configurable": {"personality_id": "test_personality_id"}}

    # Note: This would actually delete a document if it exists
    # Be careful when running this in a real environment
    result = tool._run(document_id="test_document_id", config=config)
    print("Delete document result:")
    print(result)
