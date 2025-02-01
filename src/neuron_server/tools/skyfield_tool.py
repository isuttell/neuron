import argparse
from datetime import datetime
from typing import Any, NoReturn

from astroquery.simbad import Simbad
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from skyfield.api import Star, load, utc, wgs84
from skyfield.data import hipparcos

# Constants
ALTITUDE_THRESHOLD = 18  # Minimum altitude in degrees for visibility
MAGNITUDE_THRESHOLD = 4  # Maximum magnitude for star brightness filter

# Load ephemeris data
eph = load("de421.bsp")

# Load Hipparcos star catalog
with load.open(hipparcos.URL) as f:
    hipparcos_data = hipparcos.load_dataframe(f)
    hipparcos_data = hipparcos_data[hipparcos_data["magnitude"] <= MAGNITUDE_THRESHOLD]


class SkyFieldToolArgs(BaseModel):
    latitude: float = Field(description="Observer latitude")
    longitude: float = Field(description="Observer longitude")
    elevation_m: float = Field(description="Observer elevation in meters", default=0)
    observation_time: datetime = Field(description="Observation time in UTC")
    limit: int = Field(description="The max number of stars to return", default=5)


class SkyFieldTool(BaseTool):
    name: str = "skyfield"
    description: str = (
        "Returns a list of visible stars from the observer's location and time "
        "sorted by magnitude with an altitude greater than 18° using Simbad. "
        "Returns precise ra/dec coordinates for each star. The observation time "
        "is critical for this tool and must be accurate."
    )

    args_schema: type[SkyFieldToolArgs] = SkyFieldToolArgs

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return self._arun(*args, **kwargs)

    def _arun(
        self,
        latitude: float,
        longitude: float,
        observation_time: datetime,
        elevation_m: float = 0,
        limit: int = 5,
    ) -> str:
        observer = eph["earth"] + wgs84.latlon(
            latitude, longitude, elevation_m=elevation_m
        )
        ts = load.timescale()
        obs_time = ts.utc(observation_time.replace(tzinfo=utc))
        visible_stars = []

        for hip_id, star_data in hipparcos_data.iterrows():
            star = Star.from_dataframe(star_data)
            astrometric = observer.at(obs_time).observe(star)
            alt, az, _ = astrometric.apparent().altaz()
            if alt.degrees < ALTITUDE_THRESHOLD:
                continue
            visible_stars.append(
                {
                    "Hipparcos ID": hip_id,
                    "Altitude (°)": alt.degrees,
                    "Azimuth (°)": az.degrees,
                    "Magnitude": star_data["magnitude"],
                    "RA (°)": star.ra,
                    "Dec (°)": star.dec,
                }
            )
        visible_stars = sorted(visible_stars, key=lambda x: x["Magnitude"])[:limit]

        for star in visible_stars:
            star["Name"] = Simbad.query_object(f"HIP{star['Hipparcos ID']}")["MAIN_ID"][
                0
            ]

        table_header = (
            "| Simbad MAIN_ID | Hipparcos ID | Altitude° | Azimuth° | "
            "Magnitude | RA° | Dec° |\n"
        )
        table_separator = (
            "|---------------|--------------|-----------|-----------|"
            "-----------|-----|-------|\n"
        )
        table_rows = []
        for star in visible_stars:
            table_rows.append(
                f"| {star.get('Name', 'Unknown')} "
                f"| {star['Hipparcos ID']} "
                f"| {str(round(star['Altitude (°)'], 0))} "
                f"| {str(round(star['Azimuth (°)'], 0))} "
                f"| {str(round(star['Magnitude'], 6))} "
                f"| {str(round(star['RA (°)'], 6))} "
                f"| {str(round(star['Dec (°)'], 6))} |"
            )

        visible_stars_table = table_header + table_separator + "\n".join(table_rows)

        return f"""# Brightest Stars Visible

Observation Time: {observation_time.astimezone().isoformat(timespec="minutes")}
Location: {latitude}°N, {longitude}°E

{visible_stars_table}
"""


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="SkyField Tool CLI")
    parser.add_argument(
        "--latitude",
        type=float,
        help="Observer latitude",
        default=32.84,
    )
    parser.add_argument(
        "--longitude",
        type=float,
        help="Observer longitude",
        default=-117.1,
    )
    parser.add_argument(
        "--observation_time",
        type=str,
        help="Observation time in ISO format (YYYY-MM-DDTHH:MM:SS)",
        default="2024-11-28T12:00:00",
    )

    args = parser.parse_args()

    try:
        observation_time = datetime.fromisoformat(args.observation_time)
    except ValueError as e:
        print(
            "Invalid observation time format. Please use ISO format "
            "(YYYY-MM-DDTHH:MM:SS)."
        )
        raise SystemExit(1) from e

    tool = SkyFieldTool()
    result = tool._run(args.latitude, args.longitude, observation_time)
    print(result)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
