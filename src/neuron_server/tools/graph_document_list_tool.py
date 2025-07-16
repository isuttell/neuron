"""Tool for listing documents in the Neo4j knowledge graph database.

This module provides a LangChain tool for listing documents stored in the Neo4j
knowledge graph, with filtering by personality_id for proper permission control.
"""

import asyncio
from typing import Any, Optional

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.graph.connection import get_graph
from neuron_server.logger import logger


class GraphDocumentListToolArgs(BaseModel):
    """Arguments for the Neo4j graph document list tool."""

    search: Optional[str] = Field(
        default=None,
        description="Optional search pattern to filter documents by name or source",
    )
    limit: int = Field(
        default=10,
        description="Maximum number of documents to return (default: 10)",
        ge=1,
        le=100,
    )


class GraphDocumentListTool(BaseTool):
    """Tool for listing documents in the knowledge graph database.

    This tool provides access to list documents stored in the knowledge graph,
    filtered by personality_id for proper permission control. It supports
    optional search filtering and pagination.
    """

    name: str = "graph_document_list_tool"
    description: str = """
This tool lists documents stored in the knowledge graph database.
Documents are automatically filtered by personality for permission control.

Features:
- Lists documents with metadata (id, name, source, updated_at)
- Optional search filtering by document name or source
- Pagination support with configurable limit
- Results sorted by updated_at (most recent first)
- Automatic permission filtering by personality_id

Example usage:
- List all documents: no parameters needed
- Search for documents: use search parameter with a pattern
- Limit results: use limit parameter (default: 10, max: 100)
""".strip()
    args_schema: type[GraphDocumentListToolArgs] = GraphDocumentListToolArgs

    def _run(
        self,
        config: RunnableConfig,
        search: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """List documents synchronously."""
        return asyncio.run(self._arun(config, search, limit))

    async def _arun(
        self,
        config: RunnableConfig,
        search: Optional[str] = None,
        limit: int = 10,
    ) -> str:
        """List documents asynchronously.

        Args:
            config: Runnable configuration containing personality_id
            search: Optional search pattern for document name or source
            limit: Maximum number of documents to return

        Returns:
            A formatted string containing the document list or error message
        """
        try:
            # Extract personality_id from config
            personality_id = config["configurable"].get("personality_id")
            if not personality_id:
                return """
<document_list_result>
    <status>error</status>
    <error_message>Missing personality_id in configuration</error_message>
</document_list_result>
""".strip()

            # Build the Cypher query
            query = """
MATCH (d:Document)
WHERE d.personality_id = $personality_id
"""
            params: dict[str, Any] = {"personality_id": personality_id}

            # Add search filter if provided
            if search:
                query += " AND (d.name CONTAINS $search OR d.source CONTAINS $search)"
                params["search"] = search

            # Add ordering and limit
            query += """
RETURN d.id, d.name, d.source, d.updated_at
ORDER BY d.updated_at DESC
LIMIT $limit
"""
            params["limit"] = limit

            # Log the query for debugging
            logger.debug(f"Listing documents with query: {query}")
            logger.debug(f"Query parameters: {params}")

            # Execute the query
            results = get_graph().query(query, params=params)

            # Format the results
            if not results:
                return """
<document_list_result>
    <status>success</status>
    <message>No documents found</message>
    <count>0</count>
</document_list_result>
""".strip()

            # Format results in XML-style for better LLM parsing
            documents_xml = []
            for doc in results:
                doc_xml = f"""
        <document>
            <id>{doc.get("d.id") or "N/A"}</id>
            <name>{doc.get("d.name") or "N/A"}</name>
            <source>{doc.get("d.source") or "N/A"}</source>
            <updated_at>{doc.get("d.updated_at") or "N/A"}</updated_at>
        </document>""".strip()
                documents_xml.append(doc_xml)

            documents_str = "\n        ".join(documents_xml)

            return f"""
<document_list_result>
    <status>success</status>
    <count>{len(results)}</count>
    <search_filter>{search or "None"}</search_filter>
    <documents>
        {documents_str}
    </documents>
</document_list_result>
""".strip()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error listing documents: {error_msg}")
            return f"""
<document_list_result>
    <status>error</status>
    <error_message>{error_msg}</error_message>
</document_list_result>
""".strip()


if __name__ == "__main__":
    # Example usage
    tool = GraphDocumentListTool()

    # Example: List all documents
    config = {"configurable": {"personality_id": "test_personality_id"}}
    result = tool._run(config=config)
    print("List all documents:")
    print(result)
    print("\n" + "=" * 50 + "\n")

    # Example: Search for documents
    result = tool._run(config=config, search="test")
    print("Search for documents containing 'test':")
    print(result)
