"""Tool for executing Neo4j Cypher queries on the knowledge graph database.

This module provides a LangChain tool for executing Cypher queries against a Neo4j
database. It supports all standard Cypher operations including querying, creating,
updating, and deleting nodes and relationships.
"""

import asyncio
from typing import Any, Optional

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.graph.connection import graph
from neuron_server.logger import logger


class GraphQueryToolArgs(BaseModel):
    """Arguments for the Neo4j graph query tool."""

    query: str = Field(description="The Cypher query to execute on the Neo4j database")
    params: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional parameters for the query",
    )


class GraphQueryTool(BaseTool):
    """Tool for executing Neo4j Cypher queries on the knowledge graph database.

    This tool provides direct access to the Neo4j database for querying and managing
    documents, chunks, and atomic facts. It supports parameterized queries and handles
    complex relationships between nodes.
    """

    name: str = "graph_query_tool"
    description: str = """
This tool executes Neo4j Cypher queries on the knowledge graph database.
The graph schema is:

Nodes:
- Document:
  - id: string (indexed)
  - name: string (indexed)
  - source: string (indexed)
  - personality_id: string (indexed)
  - user_id: string (indexed)
  - updated_at: datetime

- Chunk:
  - id: string
  - text: string
  - personality_id: string (indexed)
  - document_id: string (indexed)
  - user_id: string (indexed)
  - index: integer
  - updated_at: datetime

- AtomicFact:
  - id: string (indexed)
  - text: string (indexed)

- KeyElement:
  - id: string (indexed)

Relationships:
- (Document)-[:HAS_CHUNK]->(Chunk)
- (Chunk)-[:HAS_FACT]->(AtomicFact)
- (AtomicFact)-[:RELATES_TO]->(KeyElement)
- (AtomicFact)-[:CONTRADICTS]->(AtomicFact)
- (AtomicFact)-[:SUPPORTS]->(AtomicFact)

Common queries:
1. Find document by name or id:
   MATCH (d:Document)
   WHERE d.name CONTAINS $name OR d.id = $id
   RETURN d.id, d.name, d.source, d.updated_at

2. Delete document and related nodes:
   MATCH (d:Document {id: $id})
   OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
   OPTIONAL MATCH (c)-[:HAS_FACT]->(f:AtomicFact)
   DETACH DELETE d, c, f

3. Get document chunks (Prefer using graph_question_tool to manage context better):
   MATCH (c:Chunk)<-[:HAS_CHUNK]-(d:Document {id: $id})
   RETURN c.text ORDER BY c.index

You can execute any valid Cypher query. Results are returned in a structured XML format.
""".strip()
    args_schema: type[GraphQueryToolArgs] = GraphQueryToolArgs

    def _run(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> str:
        """Execute a Neo4j Cypher query synchronously.

        Args:
            query: The Cypher query to execute
            params: Optional parameters for the query
            config: Optional runnable configuration

        Returns:
            A formatted string containing the query results or error message
        """
        return asyncio.run(self._arun(query, params))

    async def _arun(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> str:
        """Execute a Neo4j Cypher query asynchronously.

        Args:
            query: The Cypher query to execute
            params: Optional parameters for the query
            config: Optional runnable configuration

        Returns:
            A formatted string containing the query results or error message
        """
        try:
            # Validate and clean parameters
            clean_params = params or {}

            # Log the query for debugging
            logger.debug(f"Executing Neo4j query: {query}")
            if clean_params:
                logger.debug(f"Query parameters: {clean_params}")

            # Execute the query
            results = graph.query(query, params=clean_params)

            # Format the results
            if not results:
                return """
<query_result>
    <status>success</status>
    <message>Query executed successfully. No results returned.</message>
</query_result>
""".strip()

            if isinstance(results, list):
                # For queries that return multiple rows
                formatted_results = []
                for row in results:
                    if isinstance(row, dict):
                        formatted_results.append(row)
                    else:
                        formatted_results.append({"result": row})

                # Format results in XML-style for better LLM parsing
                rows_str = "\n        ".join(
                    [
                        "<row>"
                        + "".join([f"<{k}>{v}</{k}>" for k, v in row.items()])
                        + "</row>"
                        for row in formatted_results
                    ]
                )
                return f"""
<query_result>
    <status>success</status>
    <count>{len(formatted_results)}</count>
    <data>
        {rows_str}
    </data>
</query_result>
""".strip()

            # For queries that return a single value
            return f"""
<query_result>
    <status>success</status>
    <data>
        <value>{results}</value>
    </data>
</query_result>
""".strip()

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error executing Neo4j query: {error_msg}")
            return f"""
<query_result>
    <status>error</status>
    <error_message>{error_msg}</error_message>
</query_result>
""".strip()


if __name__ == "__main__":
    # Example usage
    tool = GraphQueryTool()

    # Example: Find all documents
    query = "MATCH (d:Document) RETURN d.id, d.name, d.source LIMIT 5"
    result = tool._run(query=query)
    print(result)
