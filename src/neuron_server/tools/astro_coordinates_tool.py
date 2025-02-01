import argparse
from datetime import UTC, datetime

from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, SkyCoord
from astropy.time import Time
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.logger import logger


class AstroCoordinatesToolArgs(BaseModel):
    latitude: float = Field(description="Observer latitude")
    longitude: float = Field(description="Observer longitude")
    elevation: float | None = Field(
        description="Observer elevation in meters", default=0
    )
    time: datetime = Field(description="Observation time in UTC")


class AstroCoordinatesTool(BaseTool):
    name: str = "astro_coordinates"
    description: str = """
This tool returns the RA/Dec coordinates of the sky zenith at a given location and time.
""".strip()

    args_schema: type[AstroCoordinatesToolArgs] = AstroCoordinatesToolArgs

    def _run(
        self,
        latitude: float,
        longitude: float,
        time: datetime,
        elevation: float = 0,
    ) -> str:
        try:
            obstime = Time(time.astimezone(UTC), format="datetime", scale="utc")
            location = EarthLocation(
                lat=latitude * u.deg, lon=longitude * u.deg, height=elevation * u.m
            )
            altaz_frame = AltAz(obstime=obstime, location=location)
            zenith = SkyCoord(alt=90 * u.deg, az=0 * u.deg, frame=altaz_frame)
            ra_dec = zenith.transform_to("icrs")
            ra = ra_dec.ra.degree
            dec = ra_dec.dec.degree
            return f"""
The zenith RA/Dec coordinates of {latitude} latitude, {longitude} longitude at
{time.replace(microsecond=0).isoformat()} are:
RA: {round(ra, 7)} deg
Dec: {round(dec, 7)} deg
 """.strip()
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error: {str(e)}"


def main() -> None:
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
        "--time",
        type=str,
        help="Time in ISO format (YYYY-MM-DDTHH:MM:SS)",
        default="2024-12-06T20:45:00Z",
    )

    args = parser.parse_args()

    tool = AstroCoordinatesTool()
    result = tool._run(
        latitude=args.latitude,
        longitude=args.longitude,
        time=datetime.fromisoformat(args.time),
    )
    print(result)


if __name__ == "__main__":
    main()

# 75.25
# +32.7
