from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
import arxiv
import os
from typing import List


class ArxivTool(BaseTool):
    name: str = "arxiv"
    description: str = (
        """
This tool searches arXiv for research articles, and retrieves summaries. Embed short IDs in text responses to reference original sources.

**arXiv API Query Guide**

1. **Query Structure**
   - Use `search_query` with prefixes (e.g., `au:del_maestro` for author Adrian Del Maestro) to target fields like `title`, `author`, `abstract`, and `comments`.
   - For specific IDs, use `id_list` instead of `search_query=id:xxx` to handle article versions.

2. **Field Prefixes**
   - Prefixes include:
     - `ti`: Title
     - `au`: Author
     - `abs`: Abstract
     - `co`: Comment
     - `jr`: Journal Reference
     - `cat`: Category
     - `all`: All fields

3. **Boolean Operators**
   - Combine fields with `AND`, `OR`, and `ANDNOT`, e.g., `au:del_maestro+AND+ti:checkerboard`.
   - Use `ANDNOT` for exclusions.

4. **Grouping & Phrases**
   - Group with `%28` and `%29`, and wrap phrases with `%22`.
   - Example: `au:del_maestro+ANDNOT+%28ti:checkerboard+OR+ti:Pyrochore%29`.
    """.strip()
    )

    def _run(
        self,
        query: str = "",
        id_list: List[str] | None = None,
        max_results: int = 10,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
        sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending,
    ) -> str:
        try:
            if isinstance(sort_by, str):
                sort_by = arxiv.SortCriterion(sort_by)
            if isinstance(sort_order, str):
                sort_order = arxiv.SortOrder(sort_order)
            if not query and not id_list:
                raise ValueError("query or id_list is required")
            logger.debug(f"Searching arXiv with: query={query}, id_list={id_list}")
            # Construct the default API client.
            client = arxiv.Client()
            search = arxiv.Search(
                query=query if id_list is None or len(id_list) == 0 else "",
                id_list=id_list or [],
                max_results=max_results,
                sort_by=sort_by,
                sort_order=sort_order,
            )
            articles = []
            for result in client.results(search):
                article_directory = (
                    f"{config.static_folder}/arxiv/{result.get_short_id()}"
                )
                if not os.path.exists(article_directory):
                    os.makedirs(article_directory)
                articles.append(
                    f"""
Title: {result.title}
Short ID: {result.get_short_id()}
Link: {result.entry_id}
Authors: {", ".join([author.name for author in result.authors])}
Published: {result.published}
Primary Category: {result.primary_category}
Categories: {", ".join(result.categories)}
Comment: {result.comment}
Links: {", ".join([link.href for link in result.links])}

Summary:
{result.summary}
""".strip()
                )
                pdf_filename = result._get_default_filename()
                pdf_full_path = f"{article_directory}/{pdf_filename}"
                if not os.path.exists(pdf_full_path):
                    logger.debug(
                        f"Downloading PDF for {result.title} to {pdf_full_path}"
                    )
                    result.download_pdf(
                        dirpath=article_directory, filename=pdf_filename
                    )

            return "\n\n--------------\n\n".join(articles)
        except Exception as e:
            logger.exception(e)
            return f"arXiv error: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Search arXiv for research articles.")
    parser.add_argument(
        "--id",
        type=str,
        default=None,
        help="The ID of the article to inspect.",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="The search query for arXiv.",
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["search", "inspect"],
        default="search",
        help="The action to perform: search or inspect.",
    )
    parser.add_argument(
        "--sort_by",
        type=str,
        choices=["submittedDate", "relevance", "updatedDate"],
        default="submittedDate",
        help="Sort the results by submitted date, relevance, or updated date.",
    )
    parser.add_argument(
        "--max_results",
        type=int,
        default=5,
        help="The maximum number of results to return.",
    )
    args = parser.parse_args()

    tool = ArxivTool()
    results = tool._run(
        id_list=[args.id] if args.id else None,
        query=args.query,
        action=args.action,
        sort_by=(
            arxiv.SortCriterion.SubmittedDate
            if args.sort_by == "submittedDate"
            else (
                arxiv.SortCriterion.Relevance
                if args.sort_by == "relevance"
                else arxiv.SortCriterion.UpdatedDate
            )
        ),
        max_results=args.max_results,
    )
    print(results)
