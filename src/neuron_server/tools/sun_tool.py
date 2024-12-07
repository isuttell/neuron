from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import argparse
from astropy.coordinates import EarthLocation, AltAz
from astropy import units as u
from astropy.time import Time
from astropy.coordinates import get_sun
import numpy as np
from zoneinfo import ZoneInfo
import pandas as pd
from astroplan import (
    time_grid_from_range,
    is_observable,
)
from typing import List, Dict, Any


class SunToolArgs(BaseModel):
    latitude: float = Field(description="Observer latitude")
    longitude: float = Field(description="Observer longitude")
    elevation: Optional[float] = Field(
        description="Observer elevation in meters", default=0
    )
    start_time: datetime = Field(description="Start time")
    end_time: datetime = Field(description="End time")
    time_resolution: float = Field(description="Time resolution in hours", default=0.5)


class SunTool(BaseTool):
    name: str = "sun"
    description: str = (
        """
This tool provides data about the Sun at a specified location and times to help with planning astrophotography sessions.  It outputs the following in a markdown table:

Time: Time of observation
Altitude (°): Sun's altitude above the horizon
Azimuth (°): Direction of the Sun along the horizon
RA (°): Right Ascension of the Sun
Dec (°): Declination of the Sun
""".strip()
    )

    args_schema: Type[SunToolArgs] = SunToolArgs

    def _run(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        time_resolution: float = 0.5,
        elevation: float = 0,
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
        results: List[Dict[str, Any]] = []
        for t in time_range:
            time = Time(t, location=location)
            sun = get_sun(time)
            altaz = sun.transform_to(AltAz(obstime=time, location=location))
            ra_dec = sun.transform_to("icrs")
            ra = ra_dec.ra.degree
            dec = ra_dec.dec.degree
            results.append(
                {
                    "Object": "Sun",
                    "Time": time.datetime.replace(
                        microsecond=0, second=0, tzinfo=ZoneInfo("UTC")
                    )
                    .astimezone(ZoneInfo("America/Los_Angeles"))
                    .isoformat(),
                    "Altitude (°)": round(altaz.alt.degree, 2),
                    "Azimuth (°)": round(altaz.az.degree, 2),
                    "RA (°)": round(ra, 7),
                    "Dec (°)": round(dec, 7),
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
    parser.add_argument(
        "--start_time",
        type=str,
        help="Observation time in ISO format (YYYY-MM-DDTHH:MM:SS)",
        default="2024-11-30T17:35:09Z",
    )
    parser.add_argument(
        "--end_time",
        type=str,
        help="End time in ISO format (YYYY-MM-DDTHH:MM:SS)",
        default="2024-12-01T17:35:09Z",
    )
    parser.add_argument(
        "--time_resolution",
        type=float,
        help="Time resolution in hours",
        default=1,
    )
    parser.add_argument(
        "--elevation",
        type=float,
        help="Observer elevation in meters",
        default=0,
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

    tool = SunTool()
    result = tool._run(
        args.latitude, args.longitude, start_time, end_time, args.time_resolution
    )
    print(result)


if __name__ == "__main__":
    main()
