from langchain.tools import BaseTool
from neuron_server.config import config
from neuron_server.logger import logger
import arxiv
import os
from neuron_server.util.pdf import summarize_pages, summarize_document
from langchain_anthropic import ChatAnthropic

model = ChatAnthropic(
    model="claude-3-5-sonnet-20241022",
    temperature=0.3,
    max_tokens=4096,
)


class ArxivSummaryTool(BaseTool):
    name: str = "arxiv_summary"
    description: str = (
        """
This tool summarizes research articles by their arXiv short IDs. This generates a detailed summary page by page so it can take a while the first time it is run but afterwards it saves the result to a file. The force_resummarize flag can be used to force the tool to re-summarize the article even if the summary already exists if there is a problem.
""".strip()
    )

    def _run(self, id: str, force_resummarize: bool = False) -> str:
        try:

            logger.debug(f"Searching arXiv with: id_list=[{id}]")
            # Construct the default API client.
            client = arxiv.Client()
            search = arxiv.Search(
                id_list=[id],
            )
            article = next(client.results(search), None)
            if not article:
                return "No article found"
            article_directory = f"{config.static_folder}/arxiv/{article.get_short_id()}"
            if not os.path.exists(article_directory):
                os.makedirs(article_directory)

            metadata = f"""
| Field              | Description |
|--------------------|-|
| Title              | {article.title} |
| Short ID           | {article.get_short_id()} |
| Link               | {article.entry_id} |
| Authors            | {", ".join([author.name for author in article.authors])} |
| Published          | {article.published} |
| Primary Category   | {article.primary_category} |
| Categories         | {", ".join(article.categories)} |
| Comment            | {article.comment} |
| Links              | {", ".join([link.href for link in article.links])} |
| Summary            | {article.summary} |
""".strip()

            pdf_filename = article._get_default_filename()
            pdf_full_path = f"{article_directory}/{pdf_filename}"
            if not os.path.exists(pdf_full_path):
                logger.debug(f"Downloading PDF for {article.title} to {pdf_full_path}")
                article.download_pdf(dirpath=article_directory, filename=pdf_filename)

            summary_file_path = os.path.join(
                article_directory, f"{article.get_short_id()}_summary.md"
            )

            if not force_resummarize and os.path.exists(summary_file_path):
                with open(summary_file_path, "r") as file:
                    return f"Summary already exists:\n{file.read()}"

            page_summaries = summarize_pages(model, pdf_full_path)
            summary = summarize_document(model, metadata, page_summaries)

            page_summaries = "\n\n".join(
                f"## Page {i+1} Summary:\n{result}\n\n"
                for i, result in enumerate(page_summaries)
            )
            report = f"# {article.title}\n\n## arxiv metadata\n\n{metadata}\n\n## AI Summary:\n{summary}\n\n{page_summaries}"
            with open(summary_file_path, "w", encoding="utf-8") as file:
                file.write(report)
            logger.debug(f"Summary saved to {summary_file_path}")
            return report
        except Exception as e:
            logger.exception(e)
            return f"Failed to summarize article: {str(e)}"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Search arXiv for research articles.")
    parser.add_argument(
        "id",
        type=str,
        help="The ID of the article to inspect.",
    )
    args = parser.parse_args()

    tool = ArxivSummaryTool()
    results = tool._run(
        id=args.id,
    )
    print(results)
