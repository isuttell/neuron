from langchain.tools import BaseTool
from typing import List, Type, Literal
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import starplot as sp
from datetime import datetime
from zoneinfo import ZoneInfo
from uuid import uuid4
from neuron_server.config import config
from typing import Optional
from starplot import MapPlot, Projection, DSO, Star


class Marker(BaseModel):
    name: str
    ra: float
    dec: float


class StarplotToolArgs(BaseModel):
    latitude: Optional[float] = Field(description="The latitude of the observer")
    longitude: Optional[float] = Field(description="The longitude of the observer")
    time: Optional[datetime] = Field(description="The local time of the observation")
    ra_min: Optional[float] = Field(
        description="The minimum right ascension of the plot", default=0
    )
    ra_max: Optional[float] = Field(
        description="The maximum right ascension of the plot", default=24
    )
    dec_min: Optional[float] = Field(
        description="The minimum declination of the plot", default=-90
    )
    dec_max: Optional[float] = Field(
        description="The maximum declination of the plot", default=90
    )
    projection: Literal["zenith", "mercator"] = Field(
        description="The projection of the plot", default="zenith"
    )
    min_star_mag: float = Field(
        description="The minimum magnitude of stars to plot", default=4
    )
    max_dso_mag: float = Field(
        description="The maximum magnitude of DSOs to plot", default=8
    )
    markers: Optional[List[Marker]] = Field(
        description="The markers to plot on the map", default=None
    )


class StarplotTool(BaseTool):
    name: str = "starplot"
    description: str = (
        """
Generate a star plot for the given parameters. Zenith is the default projection and requires a latitude and longitude. Mercator does not require a latitude and longitude. Use mercator to zoom in on a specific area. Can optionally add markers to the plot.
""".strip()
    )

    args_schema: Type[StarplotToolArgs] = StarplotToolArgs

    def _run(
        self,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        time: Optional[datetime] = None,
        ra_min: float = 0,
        ra_max: float = 24,
        dec_min: float = -90,
        dec_max: float = 90,
        projection: Literal["zenith", "mercator"] = "zenith",
        min_star_mag: float = 4,
        max_dso_mag: float = 8,
        markers: Optional[List[Marker]] = None,
    ) -> str:
        try:
            time = time.replace(tzinfo=ZoneInfo("America/Los_Angeles"))
            style = sp.styles.PlotStyle().extend(
                sp.styles.extensions.GRAYSCALE_DARK,
                sp.styles.extensions.MAP,
            )
            style.star.label.font_size = 4
            plot = sp.MapPlot(
                projection=(
                    sp.Projection.ZENITH
                    if projection.lower() == "zenith"
                    else sp.Projection.MILLER
                ),
                ra_min=ra_min,
                ra_max=ra_max,
                dec_min=dec_min,
                dec_max=dec_max,
                lon=longitude,
                lat=latitude,
                dt=time,
                style=style,
                resolution=3600,
            )
            plot.stars(mag=min_star_mag, bayer_labels=True)
            plot.nebula(mag=max_dso_mag, true_size=True)
            plot.ecliptic(style={"line": {"style": "dashed"}})
            plot.celestial_equator()
            plot.milky_way()
            if markers:
                for marker in markers:
                    plot.marker(
                        ra=marker.ra,
                        dec=marker.dec,
                        label=marker.name,
                        style={
                            "marker": {
                                "size": 28,
                                "symbol": "circle",
                                "fill": "full",
                                "color": "#ed7eed",
                                "edge_color": "#e0c1e0",
                                "alpha": 0.4,
                            },
                            "label": {
                                "font_size": 12,
                                "font_weight": "bold",
                                "font_color": "#c83cc8",
                                "font_alpha": 0.8,
                            },
                        },
                    )
            filename = f"ast_starplot_{uuid4().hex}.png"
            file_path = f"{config.static_folder}/images/{filename}"
            url = f"{config.static_content_url}/images/{filename}"
            plot.export(file_path, padding=0)
            return f"![Starplot]({url})"
        except Exception as e:
            logger.exception(e)
            return f"Error generating starplot: {str(e)}"


if __name__ == "__main__":
    tool = StarplotTool()
    print(
        tool.invoke(
            {
                "latitude": 33.363484,
                "longitude": -116.836394,
                "time": datetime.now(),
                # "projection": "mercator",
                "markers": [
                    Marker(name="Mount Palomar", ra=123.45, dec=67.89),
                ],
            }
        )
    )
