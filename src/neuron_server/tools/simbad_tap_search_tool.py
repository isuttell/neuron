import argparse
import time

from langchain.tools import BaseTool
from pandas import DataFrame
from pydantic import BaseModel, Field
from pyvo.dal import DALResults, TAPService

from neuron_server.logger import logger


class SimbadTapSearchToolArgs(BaseModel):
    tap_query: str = Field(
        description="An Astronomical Data Query Language (ADQL) query to run against a Simbad TAP service. Available tables for joins are flux, allfluxes, otypers, ident, basic, mesVar, mesVelocities, mesDistance, mesDiameter, mesPM, mesRot, mesSpt, mesPlx, mesFe_H, mesIUE, mesHerschel, mesXMM, and mesISO"
    )


class SimbadTapSearchTool(BaseTool):
    name: str = "simbad_tap_search"
    description: str = (
        """
This tool queries a Simbad TAP service for astronomical objects and returns the results as a markdown table. Use this for general queries to find astronomical objects.
""".strip()
    )

    args_schema: type[SimbadTapSearchToolArgs] = SimbadTapSearchToolArgs

    simbad_service: str = "http://simbad.u-strasbg.fr/simbad/sim-tap"

    def _run(
        self,
        tap_query: str,
    ) -> str:
        try:
            logger.debug(f"simbad_tap_search.tap_query:\n{tap_query}")
            start_time = time.perf_counter()
            tap_service = TAPService(self.simbad_service)
            query_results: DALResults = tap_service.search(tap_query)
            duration = time.perf_counter() - start_time
            assert isinstance(query_results, DALResults)
            logger.debug(f"Found {len(query_results)} results - {duration:.2f}s")
            df: DataFrame = query_results.to_table().to_pandas()
            return f"""
    # Simbad Search Results

    Found {len(query_results)} objects. Search took {duration:.2f} seconds.

    ## Results

    {df.to_markdown() if df.size > 0 else 'No results found'}
    """.strip()
        except Exception as e:
            logger.error(e)
            raise e


def main():
    parser = argparse.ArgumentParser(description="Astro Tool CLI")
    parser.add_argument(type=str, help="Query")
    args = parser.parse_args()

    tool = SimbadSearchTool()
    result = tool._run(query=args.query)
    print(result)


if __name__ == "__main__":
    main()
