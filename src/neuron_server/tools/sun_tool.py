import argparse
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, NoReturn

import pandas as pd
from astroplan import time_grid_from_range
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, get_sun
from astropy.time import Time
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.logger import logger


@dataclass
class Location:
    """Location parameters for astronomical calculations."""

    latitude: float
    longitude: float
    elevation: float = 0

    def to_earth_location(self) -> EarthLocation:
        """Convert to astropy EarthLocation."""
        return EarthLocation(
            lat=self.latitude * u.deg,
            lon=self.longitude * u.deg,
            height=self.elevation * u.m,
        )


def get_sun_data(
    location: EarthLocation,
    start_time: Time,
    end_time: Time,
    time_resolution: float = 0.5,
) -> pd.DataFrame:
    """Get sun position data for a given location and time range."""
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
        altaz = sun.transform_to(AltAz(obstime=time, location=location))
        ra_dec = sun.transform_to("icrs")
        ra = ra_dec.ra.degree
        dec = ra_dec.dec.degree
        results.append(
            {
                "Object": "Sun",
                "Time": time.datetime.astimezone().isoformat(timespec="minutes"),
                "Altitude (°)": round(altaz.alt.degree, 2),
                "Azimuth (°)": round(altaz.az.degree, 2),
                "RA (°)": round(ra, 7),
                "Dec (°)": round(dec, 7),
            }
        )

    return pd.DataFrame(results)


def get_twilights(
    location: EarthLocation,
    start_time: datetime,
    end_time: datetime,
    time_resolution: float = 1,
) -> pd.DataFrame:
    """Get twilight times for a given location and time range."""
    results: list[dict[str, Any]] = []
    twilights = ["Astronomical", "Nautical", "Civil", ""]
    twilight_limits = [-18, -12, -6, 0]

    time_range = time_grid_from_range(
        Time([start_time, end_time], location=location),
        time_resolution=time_resolution * u.minute,
    )

    def get_sun_altitude(obstime: Time, location: EarthLocation) -> float:
        altaz_frame = AltAz(obstime=obstime, location=location)
        sun = get_sun(obstime).transform_to(altaz_frame)
        return sun.alt.deg

    now_position = get_sun_altitude(time_range[0], location)
    for i in range(len(time_range) - 1):
        next_position = get_sun_altitude(time_range[i + 1], location)
        name = None
        altitude = None
        twilight_time = None
        rising = False
        for j, limit in enumerate(twilight_limits):
            if (
                now_position < limit <= next_position
                or next_position < limit <= now_position
            ):
                name = twilights[j]
                altitude = round(now_position, 1)
                # Linear interpolation to find more accurate twilight time
                fraction = (limit - now_position) / (next_position - now_position)
                twilight_time = time_range[i] + fraction * (
                    time_range[i + 1] - time_range[i]
                )
                rising = now_position < limit <= next_position
                break
        now_position = next_position
        if name is not None and altitude is not None and twilight_time is not None:
            results.append(
                {
                    "Starts": f"{name} {'Dawn' if rising else 'Dusk'}",
                    "Altitude (°)": altitude,
                    "Time": twilight_time.datetime.astimezone().isoformat(
                        timespec="minutes"
                    ),
                }
            )

    return pd.DataFrame(results)


class SunToolArgs(BaseModel):
    latitude: float = Field(description="Observer latitude")
    longitude: float = Field(description="Observer longitude")
    elevation: float | None = Field(
        description="Observer elevation in meters", default=0
    )
    start_time: datetime = Field(description="Start time in UTC")
    end_time: datetime = Field(description="End time in UTC")
    time_resolution: float = Field(description="Time resolution in hours", default=1)


class SunTool(BaseTool):
    name: str = "sun"
    description: str = """
This tool provides data about the Sun at a specified location
and times to help with planning astrophotography sessions.
When selecting a time range by default choose an entire night
so you can capture the appropriate twilight data. Limit the
time range to a week.

It outputs the following position data:

Time: Time of observation
Altitude (°): Sun's altitude above the horizon
Azimuth (°): Direction of the Sun along the horizon
RA (°): Right Ascension of the Sun
Dec (°): Declination of the Sun

It also outputs twilight data following:

Name: Name of the twilight
Altitude: Altitude of the twilight
Time: Time of the twilight
""".strip()
    args_schema: type[SunToolArgs] = SunToolArgs

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return self._arun(*args, **kwargs)

    def _arun(  # noqa: PLR0913
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        time_resolution: float = 1,
        elevation: float = 0,
    ) -> str:
        try:
            location = Location(
                latitude=latitude,
                longitude=longitude,
                elevation=elevation,
            )
            return self._generate_report(
                location=location,
                start_time=start_time.astimezone(UTC),
                end_time=end_time.astimezone(UTC),
                time_resolution=time_resolution,
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            raise e

    def _generate_report(
        self,
        location: Location,
        start_time: datetime,
        end_time: datetime,
        time_resolution: float,
    ) -> str:
        """Generate sun position and twilight report."""
        earth_location = location.to_earth_location()

        sun_data = get_sun_data(
            location=earth_location,
            start_time=start_time,
            end_time=end_time,
            time_resolution=time_resolution,
        )

        twilights = get_twilights(
            location=earth_location,
            start_time=start_time,
            end_time=end_time,
        )

        return f"""# Sun Data

## Position

{sun_data.to_markdown(index=False) if len(sun_data) > 0 else "No sun data found"}

## Twilights

{twilights.to_markdown(index=False) if len(twilights) > 0 else "No twilights found"}
"""


def main() -> NoReturn:
    parser = argparse.ArgumentParser(description="Astro Tool CLI")
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
        "--start_time",
        type=str,
        help="Observation time (YYYY-MM-DDTHH:MM:SS)",
        default="2024-11-30T17:35:09Z",
    )
    parser.add_argument(
        "--end_time",
        type=str,
        help="End time (YYYY-MM-DDTHH:MM:SS)",
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
    except ValueError as e:
        print("Invalid time format. Use ISO format: YYYY-MM-DDTHH:MM:SS")
        raise SystemExit(1) from e

    tool = SunTool()
    result = tool._run(
        args.latitude,
        args.longitude,
        start_time,
        end_time,
        args.time_resolution,
    )
    print(result)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
