from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
import arxiv
import os
from typing import Literal, List
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings


class ArxivTool(BaseTool):
    name: str = "arxiv"
    description: str = """
Searches arXiv for the latest research articles and downloads the PDFs for later inspection. The default action is to search, requires a query as described below, for articles and download the pdfs. If action is inspect, then id_list with the id of the article to inspect is required and query is a semantic search query to return relevant parts of the article. Source are critical so make sure to include short ids so that the original sources can be found.

**arXiv API Query Guide**

1. **Basic Query Structure**
   - Use `search_query` to target fields like `title`, `author`, `abstract`, and `comments` by adding a prefix (e.g., `au:del_maestro` for author Adrian Del Maestro).
   - For filtering by specific article IDs, use `id_list` instead of `search_query=id:xxx` to handle versions.

2. **Field Prefixes**
   - Common prefixes include:
     - `ti`: Title
     - `au`: Author
     - `abs`: Abstract
     - `co`: Comment
     - `jr`: Journal Reference
     - `cat`: Category
     - `all`: All fields

3. **Boolean Operators**
   - Combine fields with `AND`, `OR`, and `ANDNOT`:
     - Example: `au:del_maestro+AND+ti:checkerboard`
   - Use `ANDNOT` for exclusion (e.g., `au:del_maestro+ANDNOT+ti:checkerboard`).

4. **Grouping & Phrases**
   - Group expressions using `%28` for `(` and `%29` for `)`, and use `%22` to wrap phrases.
   - Example: `au:del_maestro+ANDNOT+%28ti:checkerboard+OR+ti:Pyrochore%29`
    """

    def _run(
        self,
        id_list: List[str] | None = None,
        query: str = "",
        action: Literal["search", "inspect"] = "search",
        max_results: int = 10,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
        sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending,
    ) -> str:
        try:
            if isinstance(sort_by, str):
                sort_by = arxiv.SortCriterion[sort_by]
            if isinstance(sort_order, str):
                sort_order = arxiv.SortOrder[sort_order]
            if action == "inspect" and (id_list is None or len(id_list) != 1):
                raise ValueError(
                    "id_list of one article is required for inspect action"
                )
            elif action == "search" and query.strip() == "":
                raise ValueError("query is required for search action")

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
Summary: {result.summary}
Comment: {result.comment}
Links: {", ".join([link.href for link in result.links])}
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
                if action == "inspect":
                    embeddings = OpenAIEmbeddings()
                    vectorstore: FAISS | None = None
                    if os.path.exists(article_directory + "/index.faiss"):
                        logger.debug(
                            f"Loading existing vectorstore from {article_directory}"
                        )
                        vectorstore = FAISS.load_local(article_directory, embeddings)
                    else:
                        loader = PyMuPDFLoader(pdf_full_path)
                        docs = loader.load()
                        text_splitter = CharacterTextSplitter(
                            chunk_size=1000, chunk_overlap=100
                        )
                        texts = text_splitter.split_documents(docs)
                        vectorstore = FAISS.from_documents(texts, embeddings)
                        vectorstore.save_local(article_directory)
                    assert vectorstore is not None
                    results = vectorstore.similarity_search(
                        query,
                        k=max_results,
                    )
                    result = "\n\n-----\n\n".join(
                        [text.page_content for text in results]
                    ).strip()
                    return f"""
{articles[0]}

Search Results:
{result if len(result) > 0 else "No results found"}
                    """
            return "\n\n".join(articles)
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
