from langchain.tools import BaseTool
from typing import Type, Optional, List, Dict, Tuple
from pydantic import BaseModel, Field
from datetime import datetime
import argparse
from astropy.coordinates import EarthLocation, SkyCoord
from astropy import units as u
from astropy.time import Time
from zoneinfo import ZoneInfo
from astroplan import AltitudeConstraint, AirmassConstraint, AtNightConstraint
from astroplan import Observer, FixedTarget
from astropy.time import Time
from astroplan import (
    time_grid_from_range,
    observability_table,
    is_observable,
)
from astropy.table import Table
from astroplan.plots import plot_sky, plot_airmass, plot_parallactic
from matplotlib import cm
import matplotlib.pyplot as plt
from uuid import uuid4
from neuron_server.config import config
from neuron_server.logger import logger
import matplotlib
from astroplan.plots import dark_style_sheet
import pandas as pd

matplotlib.use("Agg")


def plot_sky_plot(targets: List[FixedTarget], time: Time, observer: Observer) -> str:
    cmap = cm.Set1
    ax = None
    for i, target in enumerate(targets):
        ax = plot_sky(
            target=target,
            observer=observer,
            time=time,
            style_kwargs=dict(color=cmap(float(i) / len(targets)), label=target.name),
            ax=ax,
            style_sheet=dark_style_sheet,
        )
    assert ax is not None
    handles, labels = plt.gca().get_legend_handles_labels()
    unique_legend = dict(zip(labels, handles))
    ax.legend(unique_legend.values(), unique_legend.keys(), loc="best")
    filename = f"ast_sky_{uuid4().hex}.png"
    file_path = f"{config.static_folder}/images/{filename}"
    plt.title(f"Sky Plot from {time[0].strftime('%Y-%m-%d')}")
    plt.savefig(file_path)
    plt.close()
    url = f"{config.static_content_url}/images/{filename}"
    return f"![Sky Plot]({url})"


def plot_airmass_plot(
    targets: List[FixedTarget], time: Time, observer: Observer
) -> str:

    ax = plot_airmass(
        targets=targets,
        observer=observer,
        time=time,
        style_sheet=dark_style_sheet,
        # brightness_shading=True,
        use_local_tz=True,
    )
    ax.legend(loc="best")
    filename = f"ast_airmass_{uuid4().hex}.png"
    file_path = f"{config.static_folder}/images/{filename}"
    plt.savefig(file_path)
    plt.close()
    url = f"{config.static_content_url}/images/{filename}"
    return f"![Airmass Plot]({url})"


def plot_parallactic_plot(
    targets: List[FixedTarget], time: Time, observer: Observer
) -> str:
    cmap = cm.Set1
    ax = None
    for i, target in enumerate(targets):
        ax = plot_parallactic(
            target=target,
            observer=observer,
            time=time,
            style_kwargs=dict(color=cmap(float(i) / len(targets)), label=target.name),
            ax=ax,
            style_sheet=dark_style_sheet,
        )
    assert ax is not None
    ax.legend(loc="lower center")
    filename = f"apt_parallactic_{uuid4().hex}.png"
    file_path = f"{config.static_folder}/images/{filename}"
    plt.savefig(file_path)
    plt.close()
    url = f"{config.static_content_url}/images/{filename}"
    return f"![Parallactic Plot]({url})"


class Target(BaseModel):
    name: str = Field(description="Target name")
    ra: float = Field(
        description="Target right ascension in degrees. High precision is recommended."
    )
    dec: float = Field(
        description="Target declination in degrees. High precision is recommended."
    )


class AstroObservabilityToolArgs(BaseModel):
    latitude: float = Field(description="Observer latitude")
    longitude: float = Field(description="Observer longitude")
    elevation: Optional[float] = Field(
        description="Observer elevation in meters", default=0
    )
    start_time: datetime = Field(description="Observation start time in UTC")
    end_time: datetime = Field(description="Observation end time in UTC")
    targets: List[Target] = Field(
        description="A list of targets, each target must have a name and it's ra/dec coordinates in degrees"
    )
    time_resolution: float = Field(
        description="Time resolution in hours", min=0.166666666, default=0.5
    )


class AstroObservabilityTool(BaseTool):
    name: str = "astro_observability"
    description: str = (
        """
This tool accepts a list of targets and plots the observability of the targets over a given time period at a specific location. Start and end times should typically cover a full night. It returns times when the object becomes observable, and plots of the sky and airmass.
""".strip()
    )

    args_schema: Type[AstroObservabilityToolArgs] = AstroObservabilityToolArgs

    def _run(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
        targets: List[Target],
        elevation: float = 0,
        time_resolution: float = 0.5,
    ) -> str:
        try:
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
            changes: Dict[str, List[Tuple[Time, bool]]] = {}
            for i, time in enumerate(time_grid):
                for target in sky_targets:
                    if not target.name in changes:
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
                            "time": time.to_datetime(timezone=observer.timezone)
                            .replace(microsecond=0)
                            .isoformat(),
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

- Start Time: {start_time.replace(microsecond=0).isoformat()}
- End Time: {end_time.replace(microsecond=0).isoformat()}
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
            logger.exception(e)
            return f"Error: {str(e)}"


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
        print(
            "Invalid observation time format. Please use ISO format (YYYY-MM-DDTHH:MM:SS)."
        )
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
