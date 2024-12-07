from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from skyfield.api import load, wgs84, Star, utc
from skyfield.data import hipparcos
from datetime import datetime
import argparse
from astroquery.simbad import Simbad

# Load ephemeris data
eph = load("de421.bsp")

# Load Hipparcos star catalog
with load.open(hipparcos.URL) as f:
    hipparcos_data = hipparcos.load_dataframe(f)
    hipparcos_data = hipparcos_data[hipparcos_data["magnitude"] <= 4]


class SkyFieldToolArgs(BaseModel):
    latitude: float = Field(description="Observer latitude")
    longitude: float = Field(description="Observer longitude")
    elevation_m: float = Field(description="Observer elevation in meters", default=0)
    observation_time: datetime = Field(description="Observation time in UTC")
    limit: int = Field(description="The max number of stars to return", default=5)


class SkyFieldTool(BaseTool):
    name: str = "skyfield"
    description: str = (
        """
Returns a list of visible stars from the observer's location and time sorted by magnitude with an altitude greater than 18° using Simbad. Returns precise ra/dec coordinates for each star. The observation time is critical for this tool and must be accurate
""".strip()
    )

    args_schema: Type[SkyFieldToolArgs] = SkyFieldToolArgs

    def _run(
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
            if alt.degrees < 18:
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

        visible_stars_table = "| Simbad MAIN_ID | Hipparcos ID | Altitude° | Azimuth° | Magnitude | RA° | Dec° |\n"
        visible_stars_table += "|------|---------------|---------------|--------------|-----------|--------|---------|\n"
        visible_stars_table += "\n".join(
            [
                f"| {star.get('Name', 'Unknown')} | {star['Hipparcos ID']} | {str(round(star['Altitude (°)'], 0))} | {str(round(star['Azimuth (°)'], 0))} | {str(round(star['Magnitude'], 6))} | {str(round(star['RA (°)'], 6))} | {str(round(star['Dec (°)'], 6))} |"
                for star in visible_stars
            ]
        )
        return f"""
Brightest stars visible at {observation_time.strftime("%Y-%m-%d %H:%M:%S %Z")} at {latitude}°N, {longitude}°E:

{visible_stars_table}
        """.strip()


def main():
    parser = argparse.ArgumentParser(description="SkyField Tool CLI")
    parser.add_argument(
        "--latitude",
        type=float,
        help="Observer latitude",
        default=32.84,
    )
    parser.add_argument(
        "--longitude", type=float, help="Observer longitude", default=-117.1
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
    except ValueError:
        print(
            "Invalid observation time format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)."
        )
        return

    tool = SkyFieldTool()
    result = tool._run(args.latitude, args.longitude, observation_time)
    print(result)


if __name__ == "__main__":
    main()
