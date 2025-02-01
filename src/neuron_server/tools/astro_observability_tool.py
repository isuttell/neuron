import argparse
import os
from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import pandas as pd
from astroplan import (
    AirmassConstraint,
    AltitudeConstraint,
    AtNightConstraint,
    FixedTarget,
    Observer,
    is_observable,
    observability_table,
    time_grid_from_range,
)
from astroplan.plots import dark_style_sheet, plot_airmass, plot_parallactic, plot_sky
from astropy import units as u
from astropy.coordinates import EarthLocation, SkyCoord
from astropy.table import Table
from astropy.time import Time
from langchain.tools import BaseTool
from matplotlib import cm
from pydantic import BaseModel, Field

from neuron_server.config import config
from neuron_server.logger import logger


def plot_sky_plot(targets: list[FixedTarget], time: Time, observer: Observer) -> str:
    """Generate a sky plot for the given targets.

    Args:
        targets: List of astronomical targets
        time: Observation time range
        observer: Observer location

    Returns:
        URL of the generated plot image
    """
    cmap = cm.Set1
    ax = None
    for i, target in enumerate(targets):
        ax = plot_sky(
            target=target,
            observer=observer,
            time=time,
            style_kwargs={"color": cmap(float(i) / len(targets)), "label": target.name},
            ax=ax,
            style_sheet=dark_style_sheet,
        )
    assert ax is not None
    handles, labels = plt.gca().get_legend_handles_labels()
    unique_legend = dict(zip(labels, handles, strict=False))
    ax.legend(unique_legend.values(), unique_legend.keys(), loc="best")
    filename = f"ast_sky_{uuid4().hex}.png"
    file_path = os.path.abspath(os.path.join(config.static_folder, filename))
    plt.title(
        f"Sky Plot from {time[0].strftime('%Y-%m-%d')} "
        f"to {time[-1].strftime('%Y-%m-%d')}"
    )
    plt.savefig(file_path)
    plt.close()
    return f"<image>![Sky Plot]({config.static_content_url}/{filename})</image>"


def plot_airmass_plot(
    targets: list[FixedTarget], time: Time, observer: Observer
) -> str:
    """Generate an airmass plot for the given targets.

    Args:
        targets: List of astronomical targets
        time: Observation time range
        observer: Observer location

    Returns:
        URL of the generated plot image
    """
    ax = plot_airmass(
        targets=targets,
        observer=observer,
        time=time,
        style_sheet=dark_style_sheet,
        brightness_shading=True,
        use_local_tz=True,
    )
    ax.legend(loc="best")
    filename = f"ast_airmass_{uuid4().hex}.png"
    file_path = os.path.abspath(os.path.join(config.static_folder, filename))
    plt.savefig(file_path)
    plt.close()
    return f"<image>![Airmass Plot]({config.static_content_url}/{filename})</image>"


def plot_parallactic_plot(
    targets: list[FixedTarget], time: Time, observer: Observer
) -> str:
    """Generate a parallactic angle plot for the given targets.

    Args:
        targets: List of astronomical targets
        time: Observation time range
        observer: Observer location

    Returns:
        URL of the generated plot image
    """
    cmap = cm.Set1
    ax = None
    for i, target in enumerate(targets):
        ax = plot_parallactic(
            target=target,
            observer=observer,
            time=time,
            style_kwargs={"color": cmap(float(i) / len(targets)), "label": target.name},
            ax=ax,
            style_sheet=dark_style_sheet,
        )
    assert ax is not None
    ax.legend(loc="lower center")
    filename = f"apt_parallactic_{uuid4().hex}.png"
    file_path = os.path.abspath(os.path.join(config.static_folder, filename))
    plt.savefig(file_path)
    plt.close()
    return f"<image>![Parallactic Plot]({config.static_content_url}/{filename})</image>"


class Target(BaseModel):
    """Model representing an astronomical target.

    Attributes:
        name: Name of the target object
        ra: Right ascension in degrees
        dec: Declination in degrees
    """

    name: str = Field(description="Target name")
    ra: float = Field(description="Target right ascension in degrees")
    dec: float = Field(description="Target declination in degrees")


class AstroObservabilityToolArgs(BaseModel):
    """Arguments for the AstroObservabilityTool.

    Attributes:
        latitude: Observer latitude in degrees
        longitude: Observer longitude in degrees
        elevation: Observer elevation in meters
        start_time: Start of observation period (UTC)
        end_time: End of observation period (UTC)
        targets: List of astronomical targets to observe
        time_resolution: Time resolution in hours
    """

    latitude: float = Field(description="Observer latitude")
    longitude: float = Field(description="Observer longitude")
    elevation: float | None = Field(
        description="Observer elevation in meters", default=0
    )
    start_time: datetime = Field(
        description="Observation start time in UTC. Start of night."
    )
    end_time: datetime = Field(description="Observation end time in UTC. End of night.")
    targets: list[Target] = Field(
        description="A list of targets, each target must have a name and it's ra/dec"
        "coordinates in degrees"
    )
    time_resolution: float = Field(
        description="Time resolution in hours. The default is half an hour.",
        min=0.1,
        default=0.5,
    )


class AstroObservabilityTool(BaseTool):
    """Tool for calculating astronomical object observability.

    This tool calculates when astronomical objects are observable from a given location
    and time period. It provides visualizations including sky plots, airmass plots,
    and observability tables.
    """

    name: str = "astro_observability"
    description: str = """
This tool accepts a list of targets and plots the observability of the targets over a
given night time period at a specific location. Start and end times should always
cover a full night. It returns times when the object becomes observable, and plots
of the sky and airmass.  Use this to determine if an object is observable at a
specific time.
""".strip()

    args_schema: type[AstroObservabilityToolArgs] = AstroObservabilityToolArgs

    def _run(  # noqa: PLR0913
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        targets: list[Target],
        elevation: float = 0,
        time_resolution: float = 0.5,
    ) -> str:
        """Calculate observability for given targets.

        Args:
            latitude: Observer latitude in degrees
            longitude: Observer longitude in degrees
            start_time: Start of observation period
            end_time: End of observation period
            targets: List of targets to observe
            elevation: Observer elevation in meters
            time_resolution: Time resolution in hours

        Returns:
            A formatted string containing observability results and plots
        """
        try:
            start_time = start_time.astimezone()
            end_time = end_time.astimezone()
            logger.debug(
                "Calculating observability for %s on %s to %s...",
                ", ".join(t.name for t in targets),
                start_time.isoformat(timespec="minutes"),
                end_time.isoformat(timespec="minutes"),
            )
            min_altitude: float = 18
            airmass_constraint: float = 3.0
            constraints = [
                AltitudeConstraint(min_altitude * u.deg),
                AirmassConstraint(max=airmass_constraint),
                AtNightConstraint.twilight_astronomical(),
            ]
            observer = Observer(
                location=EarthLocation(
                    lat=latitude * u.deg, lon=longitude * u.deg, height=elevation * u.m
                ),
                timezone=ZoneInfo("America/Los_Angeles"),
            )
            sky_targets = [
                FixedTarget(
                    coord=SkyCoord(ra=target.ra * u.deg, dec=target.dec * u.deg),
                    name=target.name,
                )
                for target in targets
            ]
            time_range = Time([start_time, end_time], location=observer.location)
            time_grid = time_grid_from_range(
                time_range=time_range, time_resolution=time_resolution * u.hour
            )
            changes: dict[str, list[tuple[Time, bool]]] = {}
            for i, time in enumerate(time_grid):
                for target in sky_targets:
                    if target.name not in changes:
                        changes[target.name] = []
                    observable = is_observable(
                        constraints=constraints,
                        observer=observer,
                        targets=[target],
                        times=time,
                    )
                    if (
                        not changes[target.name]
                        or changes[target.name][-1][1] != observable[0]
                        or i == len(time_grid) - 1
                    ):
                        changes[target.name].append((time, observable[0]))

            # Collect all rows in a list
            rows = []
            for target_name, target_changes in changes.items():
                for time, observable in target_changes:
                    rows.append(
                        {
                            "target": target_name,
                            "time": time.to_datetime(
                                timezone=observer.timezone
                            ).isoformat(timespec="minutes"),
                            "observable": observable,
                        }
                    )

            # Create a DataFrame from the list of rows
            observability_df = pd.DataFrame(rows)

            table: Table = observability_table(
                constraints=constraints,
                observer=observer,
                targets=sky_targets,
                times=time_grid,
            )
            local_time = time_grid.to_datetime(timezone=observer.timezone)
            return f"""
# Observability Results

## Constraints:

- Start Time: {start_time.isoformat(timespec="minutes")}
- End Time: {end_time.isoformat(timespec="minutes")}
- Minimum Altitude: {min_altitude} degrees
- Maximum Airmass: {airmass_constraint}
- Twilight Astronomical
- Time Resolution: {time_resolution} hours

## Overview

{table.to_pandas().to_markdown(index=False)}

## Observability Details

{observability_df.to_markdown(index=False)}

## Plots

{plot_sky_plot(targets=sky_targets, time=local_time, observer=observer)}
{plot_airmass_plot(targets=sky_targets, time=local_time, observer=observer)}
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
        "--start_time",
        type=str,
        help="Observation time in ISO format (YYYY-MM-DDTHH:MM:SS)",
        default="2024-11-29T17:35:09Z",
    )

    parser.add_argument(
        "--end_time",
        type=str,
        help="Observation time in ISO format (YYYY-MM-DDTHH:MM:SS)",
        default="2024-11-30T17:35:09Z",
    )

    args = parser.parse_args()

    try:
        start_time = datetime.fromisoformat(args.start_time)
        end_time = datetime.fromisoformat(args.end_time)
    except ValueError:
        print("Invalid time format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)")
        return

    tool = AstroObservabilityTool()
    result = tool._run(
        latitude=args.latitude,
        longitude=args.longitude,
        start_time=start_time,
        end_time=end_time,
        targets=[
            Target(name="M31 (Andromeda)", ra=10.68458, dec=41.26917),
            Target(name="Fake Target", ra=15.68458, dec=11.26917),
        ],
    )
    print(result)


if __name__ == "__main__":
    main()
