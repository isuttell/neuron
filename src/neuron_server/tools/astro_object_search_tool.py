from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
import argparse
import pyvo
from neuron_server.cache import cache_response
from datetime import datetime
import asyncio
import pandas as pd
from neuron_server.logger import logger

tap_service = pyvo.dal.TAPService("http://simbad.u-strasbg.fr/simbad/sim-tap")


class AstroObjectSearchToolArgs(BaseModel):
    main_id: str = Field(
        description="The exact object identifier to search for, e.g. 'M31', 'M 42', 'NGC 2247', 'alf Lyr', 'alf CMa'"
    )


def get_basic_object_details(query: str) -> pyvo.dal.DALResults:
    return tap_service.search(
        f"""
SELECT
    basic.*
FROM basic
WHERE main_id = '{query}'
    """.strip()
    )


def get_object_distances(query: str) -> pyvo.dal.DALResults:
    return tap_service.search(
        f"""
SELECT
    basic.main_id,
    mesDistance.*
FROM basic
JOIN mesDistance ON basic.oid = mesDistance.oidref
WHERE main_id = '{query}'
    """.strip()
    )


def get_object_diameter(query: str) -> pyvo.dal.DALResults:
    return tap_service.search(
        f"""
SELECT
    basic.main_id,
    mesDiameter.*
FROM basic
JOIN mesDiameter ON basic.oid = mesDiameter.oidref
WHERE main_id = '{query}'
    """.strip()
    )


def get_object_velocities(query: str) -> pyvo.dal.DALResults:
    return tap_service.search(
        f"""
SELECT
    basic.main_id,
    mesVelocities.*
FROM basic
JOIN mesVelocities ON basic.oid = mesVelocities.oidref
WHERE main_id = '{query}'
    """.strip()
    )


def get_object_variance(query: str) -> pyvo.dal.DALResults:
    return tap_service.search(
        f"""
SELECT
    basic.main_id,
    mesVar.*
FROM basic
JOIN mesVar ON basic.oid = mesVar.oidref
WHERE main_id = '{query}'
    """.strip()
    )


def get_object_flux(query: str) -> pyvo.dal.DALResults:
    return tap_service.search(
        f"""
SELECT
    basic.main_id,
    flux.*
FROM basic
JOIN flux ON basic.oid = flux.oidref
WHERE main_id = '{query}'
    """.strip()
    )


def get_object_identifiers(query: str) -> pyvo.dal.DALResults:
    return tap_service.search(
        f"""
SELECT
    basic.main_id,
    ident.id AS related_ids
FROM basic
JOIN ident ON basic.oid = ident.oidref
WHERE main_id = '{query}'
    """.strip()
    )


@cache_response(ttl=60 * 60)
async def search_object(
    main_id: str,
) -> str:
    basic_object_details = get_basic_object_details(main_id)
    if len(basic_object_details) == 0:
        raise Exception(f'No object found with that identifier "{main_id}"')
    object_details: pd.DataFrame = basic_object_details.to_table().to_pandas()
    object_distances: pd.DataFrame = (
        get_object_distances(main_id).to_table().to_pandas()
    )
    object_diameter: pd.DataFrame = get_object_diameter(main_id).to_table().to_pandas()
    object_flux: pd.DataFrame = (
        get_object_flux(main_id)
        .to_table()
        .to_pandas()
        .apply(
            lambda col: (
                col.fillna(0) if col.dtype.kind in "biufc" else col.fillna("N/A")
            )
        )
    )
    object_identifiers: pd.DataFrame = (
        get_object_identifiers(main_id).to_table().to_pandas()
    )
    return f"""
# Results for "{main_id}" at {datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")}

{object_details.to_markdown(index=False)}

## Distances

{object_distances.to_markdown(index=False) if len(object_distances) > 0 else "No distance data found"}

## Diameter

{object_diameter.to_markdown(index=False) if len(object_diameter) > 0 else "No diameter data found"}

## Flux

{object_flux.to_markdown(index=False) if len(object_flux) > 0 else "No flux data found"}

## Related Identifiers

{object_identifiers.to_markdown(index=False) if len(object_identifiers) > 0 else "No related identifiers found"}
""".strip()


class AstroObjectSearchTool(BaseTool):
    name: str = "astro_object_search"
    description: str = (
        """
This tool provides detailed information about an astronomical target specified by it's main identifier from Simbad. It returns the following information:

1. Basic Object Details: Retrieves basic details about the object using the provided identifier such as the object type, precise ra/dec coordinates, redshift (rvz_redshift), parallax (rvz_parallax), angular size, and other details.
2. Distances: Retrieves distance measurements related to the object.
3. Diameter: Retrieves diameter measurements of the object.
4. Flux: Retrieves flux measurements of the object.
5. Related Identifiers: Retrieves related identifiers for the object.

Always use this tool to answer questions about an astronomical object.
""".strip()
    )

    args_schema: Type[AstroObjectSearchToolArgs] = AstroObjectSearchToolArgs

    def _run(
        self,
        main_id: str,
    ) -> str:
        return asyncio.run(self._arun(main_id))

    async def _arun(
        self,
        main_id: str,
    ) -> str:
        try:
            logger.debug(f"Searching for object {main_id}")
            return await search_object(main_id)
        except Exception as e:
            return f"Error with Simbad object search: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description="Astro Tool CLI")
    parser.add_argument(
        "--main_id",
        type=str,
        help="The main identifier to search for",
        default="NGC 2247",
    )
    args = parser.parse_args()

    tool = AstroObjectSearchTool()
    result = tool._run(args.main_id)
    print(result)


if __name__ == "__main__":
    main()
