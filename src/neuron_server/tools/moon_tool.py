import argparse
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from astroplan import (
    time_grid_from_range,
)
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, get_body, get_sun
from astropy.time import Time
from langchain.tools import BaseTool
from pydantic import BaseModel, Field


class MoonToolArgs(BaseModel):
    latitude: float = Field(description="Observer latitude")
    longitude: float = Field(description="Observer longitude")
    elevation: float | None = Field(
        description="Observer elevation in meters", default=0
    )
    start_time: datetime = Field(description="Start time")
    end_time: datetime = Field(description="End time")
    time_resolution: float = Field(description="Time resolution in hours", default=0.5)


class MoonTool(BaseTool):
    name: str = "moon"
    description: str = (
        """
This tool provides data about the Moon at a specified location and times to help with planning astrophotography sessions.  It outputs the following in a markdown table:

Time: Observation time
Altitude (°): Moon's altitude above the horizon
Azimuth (°): Direction of the Moon along the horizon
RA (°): Right Ascension of the Moon
Dec (°): Declination of the Moon
Phase Angle: Angle indicating the Moon's phase
Illumination: Percentage of the Moon's surface illuminated
""".strip()
    )

    args_schema: type[MoonToolArgs] = MoonToolArgs

    def _run(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        elevation: float = 0,
        time_resolution: float = 0.5,
    ) -> str:
        start_time = start_time.replace(second=0, microsecond=0)
        end_time = end_time.replace(second=0, microsecond=0)
        location = EarthLocation(
            lat=latitude * u.deg, lon=longitude * u.deg, height=elevation * u.m
        )
        time_range = (
            time_grid_from_range(
                Time([start_time, end_time], location=location),
                time_resolution=time_resolution * u.hour,
            )
            if start_time != end_time
            else Time([start_time], location=location)
        )
        results: list[dict[str, Any]] = []
        for t in time_range:
            time = Time(t, location=location)
            sun = get_sun(time)
            moon = get_body("moon", time=time, location=location)
            altaz = moon.transform_to(AltAz(obstime=time, location=location))
            ra_dec = moon.transform_to("icrs")
            ra = ra_dec.ra.degree
            dec = ra_dec.dec.degree
            elongation = sun.separation(moon)
            moon_phase = np.arctan2(
                sun.distance * np.sin(elongation),
                moon.distance - sun.distance * np.cos(elongation),
            )
            moon_illumination = (1 + np.cos(moon_phase)) / 2
            results.append(
                {
                    "Object": "Moon",
                    "Time": time.datetime.replace(
                        microsecond=0, second=0, tzinfo=ZoneInfo("UTC")
                    )
                    .astimezone(ZoneInfo("America/Los_Angeles"))
                    .isoformat(),
                    "Altitude (°)": round(altaz.alt.degree, 2),
                    "Azimuth (°)": round(altaz.az.degree, 2),
                    "RA (°)": round(ra, 7),
                    "Dec (°)": round(dec, 7),
                    "Phase Angle (°)": round(np.degrees(moon_phase), 2),
                    "Illumination %": round(moon_illumination * 100, 2),
                }
            )
        if len(results) == 0:
            return f"No results found for the given time range: {start_time.isoformat()} to {end_time.isoformat()}"
        df = pd.DataFrame(results)
        return df.to_markdown(index=False)


def main():
    parser = argparse.ArgumentParser(description="Astro Tool CLI")
    parser.add_argument(
        "--latitude",
        type=float,
        help="Observer latitude",
        default=32.84,
    )
    parser.add_argument(
        "--longitude", type=float, help="Observer longitude", default=-117.1
    )
    parser.add_argument("--elevation", type=float, help="Observer elevation", default=0)
    parser.add_argument(
        "--start_time",
        type=str,
        help="Start time in ISO format (YYYY-MM-DDTHH:MM:SS)",
        default="2024-11-24T12:00:00",
    )
    parser.add_argument(
        "--end_time",
        type=str,
        help="End time in ISO format (YYYY-MM-DDTHH:MM:SS)",
        default="2024-11-24T12:00:00",
    )

    args = parser.parse_args()

    try:
        start_time = datetime.fromisoformat(args.start_time)
        end_time = datetime.fromisoformat(args.end_time)
    except ValueError:
        print(
            "Invalid observation time format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)."
        )
        return

    tool = MoonTool()
    result = tool._run(
        args.latitude, args.longitude, start_time, end_time, args.elevation
    )
    print(result)


if __name__ == "__main__":
    main()
