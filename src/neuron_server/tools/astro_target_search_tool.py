import argparse
import math
import time
from typing import Literal

from langchain.tools import BaseTool
from pandas import DataFrame
from pydantic import BaseModel, Field
from pyvo.dal import DALResults, TAPService

from neuron_server.logger import logger


class AstroTargetSearchToolArgs(BaseModel):
    ra: float = Field(description="RA in degrees")
    dec: float = Field(description="Dec in degrees")
    radius: float = Field(
        description="Radius to search within in degrees of the RA/Dec",
        default=45,
        ge=10,
        le=90,
    )
    limit: int | None = Field(
        50, description="The max number of items to return", ge=0, le=500
    )
    min_flux: float | None = Field(
        6.0,
        description=(
            "The inclusive minimum relative magnitude (astronomy) to return. "
            "Values larger than 6 are too dim for the naked human eye."
        ),
        le=35,  # JWST limit
        ge=-28,  # SUN limit
    )
    max_flux: float | None = Field(
        22.0,
        description=(
            "The inclusive maximum relative magnitude (astronomy) to return. "
            "Values greater than 22 are too dim for the capabilities of the "
            "imaging telescope."
        ),
        le=35,  # JWST limit
        ge=-28,  # SUN limit
    )
    otypes: list[str] = Field(
        description=(
            "The types of objects to return. If only one item is provided then "
            "it will also include all of it's descendants, e.g. 'G' will "
            "include galaxies, 'AGN', etc. '*' will include all stars. 'GNe' "
            "will include all nebulae. Any valid Simbad object type can be "
            "provided, e.g, Cld, GNe, RNe, MoC, DNe, glb, CGb, HVC, SNR, "
            "SN*, QSO, Bla, AGN, EmG, H2G, SBG, bCG, BH, G, *, Ce*, ISM, "
            "Cl*, EmO."
        ),
    )
    order_by: (
        Literal["nbref", "min_flux", "galdim_majaxis", "galdim_minaxis"] | None
    ) = Field(
        "nbref",
        description=(
            "The fields to order the results by. 'nbref' is the number of "
            "references, 'min_flux' is the minimum flux, 'galdim_majaxis' is "
            "the major axis, and 'galdim_minaxis' is the minor axis."
        ),
    )
    order_direction: Literal["ASC", "DESC"] | None = Field(
        "DESC",
        description="The direction to order the results by",
    )


"""
| otype | Description                       |
|-------|-----------------------------------|
| GNe   | Nebula                            |
| RNe   | Reflection Nebula                 |
| MoC   | Molecular Cloud                   |
| DNe   | Dark Cloud (nebula)               |
| glb   | Globule (low-mass dark cloud)     |
| CGb   | Cometary Globule / Pillar         |
| HVC   | High-velocity Cloud               |
| SNR   | SuperNova Remnant                 |
| SN*   | Supernova                         |
| QSO   | Quasar                            |
| Bla   | Blazar                            |
| AGN   | Active Galactic Nucleus           |
| EmG   | Emission-line galaxy              |
| H2G   | HII Galaxy                        |
| SBG   | Starburst Galaxy                  |
| bCG   | Blue Compact Galaxy               |
| BH    | Black Hole                        |
| G     | Galaxy                            |
| *     | Star                              |
| Ce*   | Cepheid                           |
| ISM   | Interstellar Medium               |
| Cl*   | Cluster of Stars                  |
| EmO   | Emission Object                   |
"""


class AstroTargetSearchTool(BaseTool):
    name: str = "astro_target_search"
    description: str = (
        "Queries Simbad astronomical database to find celestial objects within "
        "a specified sky region. Returns detailed data for stars and deep space "
        "objects (DSOs) including coordinates (RA/Dec), brightness (flux), "
        "morphological classification, angular dimensions, and current position "
        "(altitude/azimuth). Supports various astronomical targets like emission "
        "nebulae (GNe), galaxies (G), Stars (*), and more. Essential for "
        "planning astrophotography sessions by identifying suitable targets and "
        "their observational characteristics. Results include key parameters "
        "such sky coordinates, brightness, and angular size needed for when "
        "determining the target to observe. Results sorted by reference count "
        "and flux. It is recommended to run this tool multiple times a night "
        "with different coordinates based on the prime shooting times to "
        "determine the best targets through out the night. The observability "
        "tool can confirm the best target."
    ).strip()

    args_schema: type[AstroTargetSearchToolArgs] = AstroTargetSearchToolArgs

    simbad_service: str = "http://simbad.u-strasbg.fr/simbad/sim-tap"

    def _run(  # noqa: PLR0913
        self,
        ra: float,
        dec: float,
        otypes: list[str],
        limit: int = 50,
        min_flux: float | None = 6.0,
        max_flux: float | None = 22.0,
        radius: float = 60,
        order_by: Literal["nbref", "min_flux", "galdim_majaxis", "galdim_minaxis"]
        | None = "nbref",
        order_direction: Literal["ASC", "DESC"] | None = "DESC",
    ) -> str:
        try:
            assert len(otypes) > 0, "otypes must be provided"
            otypes_str = ", ".join([f"'{otype}'" for otype in otypes])
            otype_query = (
                f"basic.otype = '{otypes[0]}..'"
                if len(otypes) == 1
                else f"basic.otype IN ({otypes_str})"
            )
            query = f"""
    SELECT TOP {limit}
        basic.main_id,
        basic.nbref,
        basic.otype,
        basic.morph_type,
        basic.galdim_majaxis,
        basic.galdim_majaxis_prec,
        basic.galdim_minaxis,
        basic.galdim_minaxis_prec,
        basic.sp_type,
        basic.ra,
        basic.ra_prec,
        basic.dec,
        basic.dec_prec,
        MIN(flux.flux) AS min_flux,
        MAX(flux.flux) AS max_flux,
        AVG(flux.flux) AS avg_flux,
        basic.update_date
    FROM basic
    LEFT JOIN flux ON basic.oid = flux.oidref
    WHERE
        {otype_query}
        AND CONTAINS(POINT('ICRS', RA, DEC), CIRCLE('ICRS', {ra}, {dec}, {radius})) = 1
        AND (
            (
                flux.flux <= {float(max_flux)}
                AND flux.flux >= {float(min_flux)}
            )
            OR flux.flux IS NULL
        )
        AND basic.nbref > 2
    GROUP BY
        basic.main_id, basic.nbref, basic.otype, basic.morph_type,
        basic.galdim_majaxis, basic.galdim_majaxis_prec, basic.galdim_minaxis,
        basic.galdim_minaxis_prec, basic.sp_type, basic.ra, basic.dec,
        basic.ra_prec, basic.dec_prec, basic.update_date
    ORDER BY {order_by} {order_direction}
            """.strip()
            # Execute the query
            logger.debug(
                f"Querying simbad for {otypes_str} objects within {radius} degrees "
                f"of {ra} {dec}..."
            )
            start_time = time.perf_counter()
            tap_service = TAPService(self.simbad_service)

            query_results: DALResults = tap_service.search(query)
            duration = time.perf_counter() - start_time
            assert isinstance(query_results, DALResults)
            logger.debug(f"Found {len(query_results)} results - {duration:.2f}s")
            # Convert the results to a pandas DataFrame for easy formatting
            # and return the results as a markdown table
            df = DataFrame(
                [
                    {
                        "Simbad ID (main_id)": row["main_id"],
                        "References": row["nbref"],
                        "Object Type": row["otype"],
                        "Morphology": row.get("morph_type"),
                        "Angular Size Major Axis (arcmin)": (
                            round(row["galdim_majaxis"], row["galdim_majaxis_prec"])
                            if row.get("galdim_majaxis")
                            and not math.isnan(row["galdim_majaxis"])
                            else None
                        ),
                        "Angular Size Minor Axis (arcmin)": (
                            round(row["galdim_minaxis"], row["galdim_minaxis_prec"])
                            if row.get("galdim_minaxis")
                            and not math.isnan(row["galdim_minaxis"])
                            else None
                        ),
                        "Spectral Type (sp_type)": row.get("sp_type"),
                        "Flux": (
                            round(row["min_flux"], 6) if row.get("min_flux") else None
                        ),
                        "RA°": round(row["ra"], row["ra_prec"]),
                        "DEC°": round(row["dec"], row["dec_prec"]),
                        "Update Date": row["update_date"],
                    }
                    for row in query_results
                ]
            )
            return f"""
    # Simbad Search Results

    Found {len(query_results)} {otypes_str} objects with flux between
    {min_flux} and {max_flux} within a {radius} degree radius.
    Search took {duration:.2f} seconds.

    ## Results

    {df.to_markdown() if df.size > 0 else "No results found"}
    """.strip()
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e


def main() -> None:
    parser = argparse.ArgumentParser(description="Astro Tool CLI")
    parser.add_argument("--ra", type=float, help="RA", default=10.684708333333333)
    parser.add_argument("--dec", type=float, help="Dec", default=41.268750000000004)
    parser.add_argument("--radius", type=float, help="Radius in degrees", default=10)
    parser.add_argument("--otype", type=str, help="Object type", default="HII")
    args = parser.parse_args()

    tool = AstroTargetSearchTool()
    result = tool._run(
        ra=args.ra, dec=args.dec, radius=args.radius, otypes=[args.otype]
    )
    print(result)


if __name__ == "__main__":
    main()
