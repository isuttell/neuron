import json
from typing import Any, Literal

from langchain.tools import BaseTool
from langchain_community.tools.tavily_search import TavilySearchResults
from pydantic import BaseModel, Field

from neuron_server.logger import logger


class TavilySearchToolArgs(BaseModel):
    query: str = Field(
        description="The search query to execute. Natural language question or terms."
    )
    topic: Literal["general", "news", "finance"] = Field(
        description="The topic category for the search.", default="general"
    )
    time_range: Literal["day", "week", "month", "year"] | None = Field(
        description="Time range filter.", default=None
    )
    include_domains: list[str] | None = Field(
        description="List of specific domains to include in the search results",
        default=None,
    )
    exclude_domains: list[str] | None = Field(
        description="List of specific domains to exclude from the search results",
        default=None,
    )
    max_results: int = Field(
        description="Maximum number of search results to return", default=5, ge=1, le=20
    )
    search_depth: Literal["basic", "advanced"] = Field(
        description="Search depth. 'basic' for quick, 'advanced' for comprehensive",
        default="basic",
    )
    include_answer: bool = Field(
        description="Whether to include a direct answer to the query", default=False
    )
    include_raw_content: bool = Field(
        description="Whether to include cleaned HTML content from search results",
        default=False,
    )


class TavilySearchTool(BaseTool):
    name: str = "tavily_search"
    description: str = """
Advanced web search tool powered by Tavily that allows configurable search parameters.
Use this tool to search the web with specific filtering options like topic category,
time range, included/excluded domains, and result formatting preferences.

Features:
- Topic-specific search (general, news, finance)
- Time range filtering (day, week, month, year)
- Domain inclusion/exclusion
- Configurable result depth and formatting
- Optional direct answer inclusion
""".strip()
    args_schema: type[TavilySearchToolArgs] = TavilySearchToolArgs

    def _run(self, **kwargs: Any) -> str:
        """Synchronous implementation that delegates to async version."""
        import asyncio

        return asyncio.run(self._arun(**kwargs))

    async def _arun(self, **kwargs: Any) -> str:
        # Extract parameters from kwargs
        query = kwargs.get("query")
        topic = kwargs.get("topic", "general")
        time_range = kwargs.get("time_range")
        include_domains = kwargs.get("include_domains")
        exclude_domains = kwargs.get("exclude_domains")
        max_results = kwargs.get("max_results", 5)
        search_depth = kwargs.get("search_depth", "basic")
        include_answer = kwargs.get("include_answer", False)
        include_raw_content = kwargs.get("include_raw_content", False)

        try:
            logger.debug(
                f"Tavily search with: query='{query}', topic='{topic}', "
                f"time_range='{time_range}', max_results={max_results}, "
                f"search_depth='{search_depth}'"
            )

            # Initialize TavilySearchResults with configurable parameters
            # Filter out None values to avoid validation errors
            tavily_params = {
                "max_results": max_results,
                "search_depth": search_depth,
                "topic": topic,
                "include_answer": include_answer,
                "include_raw_content": include_raw_content,
            }

            if time_range:
                tavily_params["time_range"] = time_range
            if include_domains:
                tavily_params["include_domains"] = include_domains
            if exclude_domains:
                tavily_params["exclude_domains"] = exclude_domains

            tavily_tool = TavilySearchResults(**tavily_params)

            # Execute the search with dynamic parameters
            results = await tavily_tool.ainvoke(
                {
                    "query": query,
                }
            )

            # Return raw JSON results
            return json.dumps(results, indent=2)

        except Exception as e:
            logger.error(f"Tavily search error: {e}", exc_info=True)
            return f"Search error: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Search the web using Tavily with configurable options."
    )
    parser.add_argument(
        "--query", type=str, required=True, help="The search query to execute."
    )
    parser.add_argument(
        "--topic",
        type=str,
        choices=["general", "news", "finance"],
        default="general",
        help="Topic category for the search.",
    )
    parser.add_argument(
        "--time-range",
        type=str,
        choices=["day", "week", "month", "year"],
        help="Time range to filter results.",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Maximum number of results to return.",
    )
    parser.add_argument(
        "--search-depth",
        type=str,
        choices=["basic", "advanced"],
        default="basic",
        help="Search depth level.",
    )
    parser.add_argument(
        "--include-answer",
        action="store_true",
        help="Include direct answer to the query.",
    )

    args = parser.parse_args()

    tool = TavilySearchTool()
    results = tool._run(
        query=args.query,
        topic=args.topic,
        time_range=args.time_range,
        max_results=args.max_results,
        search_depth=args.search_depth,
        include_answer=args.include_answer,
    )
    print(results)
