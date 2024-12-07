from langchain.tools import BaseTool
from typing import Type, Optional, List, Dict, Literal
from pydantic import BaseModel, Field
import argparse
from neuron_server.logger import logger
import pyvo
import math
import pandas as pd

tap_service = pyvo.dal.TAPService("http://simbad.u-strasbg.fr/simbad/sim-tap")


class AstroTargetSearchToolArgs(BaseModel):
    ra: float = Field(description="RA in degrees")
    dec: float = Field(description="Dec in degrees")
    radius: float = Field(
        description="Radius to search within in degrees of the RA/Dec. Min 10, Max 90"
    )
    limit: Optional[int] = Field(
        description="The max number of items to return", default=50
    )
    min_mag: Optional[float] = Field(
        description="The inclusive minimum relative magnitude (astronomy) to return. Values larger than 6 are too dim for the naked human eye.",
        default=6,
    )
    max_mag: Optional[float] = Field(
        description="The inclusive maximum relative magnitude (astronomy) to return. Values greater than 22 are too dim for the capabilities of the imaging telescope.",
        default=22,
    )
    otypes: Optional[List[str]] = (
        Field(
            description="The types of objects to return. Defaults astrophography targets. If only one item is provided then it will also include all of it's descendants, e.g. 'G' will include galaxies, 'AGN', etc. '*' will include all stars. 'GNe' will include all nebulae. Any valid Simbad object type can be provided, e.g, Cld, GNe, RNe, MoC, DNe, glb, CGb, HVC, SNR, SN*, QSO, Bla, AGN, EmG, H2G, SBG, bCG, BH, G, *, Ce*, ISM, Cl*, EmO".strip(),
            default=["GNe"],
        ),
    )
    order_by: Optional[
        Literal["nbref", "min_flux", "galdim_majaxis", "galdim_minaxis"]
    ] = (
        Field(
            description="The fields to order the results by. nbref is the number of references and means its a well known object or not. Defaults to 'nbref'. Valid fields are 'nbref', 'galdim_majaxis', 'galdim_minaxis', and 'min_flux'.",
            default="nbref",
        ),
    )
    order_direction: Optional[Literal["ASC", "DESC"]] = (
        Field(
            description="The direction to order the results by. Defaults to 'DESC'. Valid values are 'ASC' and 'DESC'.",
            default="DESC",
        ),
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
        """
Queries Simbad astronomical database to find celestial objects within a specified sky region. Returns detailed data for stars and deep space objects (DSOs) including coordinates (RA/Dec), brightness (flux), morphological classification, angular dimensions, and current position (altitude/azimuth). Supports various astronomical targets like emission nebulae (GNe), galaxies (G), Stars (*), and more. Essential for planning astrophotography sessions by identifying suitable targets and their observational characteristics. Results include key parameters such sky coordinates, brightness, and angular size needed for when determining the target to observe. Results sorted by reference count and flux. It is recommended to run this tool multiple times a night with different cooordinates based on the prime shooting times to determine the best targets through out the night. The observability tool can confirm the best target.
""".strip()
    )

    args_schema: Type[AstroTargetSearchToolArgs] = AstroTargetSearchToolArgs

    def _run(
        self,
        ra: float,
        dec: float,
        limit: int = 50,
        min_mag: Optional[float] = 6.0,
        max_mag: Optional[float] = 22.0,
        radius: float = 60,
        otypes: Optional[List[str]] = ["GNe"],
        order_by: Optional[
            Literal["nbref", "min_flux", "galdim_majaxis", "galdim_minaxis"]
        ] = "nbref",
        order_direction: Optional[Literal["ASC", "DESC"]] = "DESC",
    ) -> str:
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
            flux.flux <= {float(max_mag)}
            AND flux.flux >= {float(min_mag)}
        )
        OR flux.flux IS NULL
    )
    AND basic.nbref > 2
GROUP BY basic.main_id, basic.nbref, basic.otype, basic.morph_type, basic.galdim_majaxis, basic.galdim_majaxis_prec, basic.galdim_minaxis, basic.galdim_minaxis_prec, basic.sp_type, basic.ra, basic.dec, basic.ra_prec, basic.dec_prec, basic.update_date
ORDER BY {order_by} {order_direction}
        """.strip()
        # Execute the query
        logger.debug(f"Querying:\n{query}")
        query_results: pyvo.dal.DALResults = tap_service.search(query)

        results: List[Dict[str, str]] = []
        for row in query_results:
            morph_type = row["morph_type"] if row["morph_type"] else ""
            ra = str(round(row["ra"], row["ra_prec"]))
            dec = str(round(row["dec"], row["dec_prec"]))
            majaxis = (
                str(round(row["galdim_majaxis"], row["galdim_majaxis_prec"]))
                if row["galdim_majaxis"] and not math.isnan(row["galdim_majaxis"])
                else " "
            )
            minaxis = (
                str(round(row["galdim_minaxis"], row["galdim_minaxis_prec"]))
                if row["galdim_minaxis"] and not math.isnan(row["galdim_minaxis"])
                else ""
            )
            sp_type = row["sp_type"] if row["sp_type"] else ""
            flux = str(round(row["min_flux"], 6)) if row["min_flux"] else ""
            results.append(
                {
                    "main_id": row["main_id"],
                    "nbref": row["nbref"],
                    "Object Type": row["otype"],
                    "Morphology": morph_type,
                    "Angular Size Major Axis (arcmin)": majaxis,
                    "Angular Size Minor Axis (arcmin)": minaxis,
                    "Spectral Type": sp_type,
                    "Flux": flux,
                    "RA°": ra,
                    "DEC°": dec,
                    "Update Date": row["update_date"],
                }
            )
        df = pd.DataFrame(results)
        return f"""
Found {len(query_results)} {otypes_str} objects with magnitudes between {min_mag} and {max_mag} within a {radius} degree radius:

{df.to_markdown(index=False)}
""".strip()


def main():
    parser = argparse.ArgumentParser(description="Astro Tool CLI")
    parser.add_argument("--ra", type=float, help="RA", default=10.684708333333333)
    parser.add_argument("--dec", type=float, help="Dec", default=41.268750000000004)
    parser.add_argument("--radius", type=float, help="Radius in degrees", default=10)
    parser.add_argument("--otype", type=str, help="Object type", default="G")
    args = parser.parse_args()

    tool = AstroTargetSearchTool()
    result = tool._run(
        ra=args.ra, dec=args.dec, radius=args.radius, otypes=[args.otype]
    )
    print(result)


if __name__ == "__main__":
    main()
