import os
from uuid import uuid4

from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from starplot import OpticPlot
from starplot.callables import color_by_bv
from starplot.optics import Camera
from starplot.styles import PlotStyle, extensions

from neuron_server.config import config
from neuron_server.logger import logger


class StarplotOpticToolArgs(BaseModel):
    target_name: str = Field(description="The name of the target object")
    latitude: float = Field(description="The latitude of the observer")
    longitude: float = Field(description="The longitude of the observer")
    time: datetime = Field(description="The UTC time of the observation")
    ra: float = Field(description="The right ascension of the target object in degrees")
    dec: float = Field(description="The declination of the target object in degrees")
    sensor_height: float = Field(description="The height of the camera sensor (mm)")
    sensor_width: float = Field(description="The width of the camera sensor (mm)")
    lens_focal_length: float = Field(
        description="The focal length of the camera lens (mm)"
    )
    rotation: float | None = Field(
        description="The angle (degrees) to rotate the camera", default=0
    )
    star_mag: float | None = Field(
        description="The magnitude of stars to plot", default=15
    )
    dso_mag: float | None = Field(
        description="The magnitude of DSOs to plot", default=15
    )


class StarplotOpticTool(BaseTool):
    name: str = "starplot_optic"
    description: str = (
        """
Generates an optic plot to visualize the given target through a camera lens. This is a slow tool. It requires precise coordinates. Ensure magnitudes are set to the appropriate so the target is visible.
""".strip()
    )

    args_schema: type[StarplotOpticToolArgs] = StarplotOpticToolArgs

    def _run(
        self,
        target_name: str,
        latitude: float,
        longitude: float,
        time: datetime,
        ra: float,
        dec: float,
        sensor_height: float,
        sensor_width: float,
        lens_focal_length: float,
        rotation: float | None = 0,
        star_mag: float | None = 15,
        dso_mag: float | None = 22,
    ) -> str:
        try:
            style = PlotStyle().extend(
                extensions.GRAYSCALE_DARK,
                extensions.OPTIC,
            )
            p = OpticPlot(
                ra=ra,
                dec=dec,
                lat=latitude,
                lon=longitude,
                dt=time,
                optic=Camera(
                    sensor_height=sensor_height,
                    sensor_width=sensor_width,
                    lens_focal_length=lens_focal_length,
                    rotation=rotation,
                ),
                style=style,
                raise_on_below_horizon=False,
            )
            p.stars(mag=star_mag, color_fn=color_by_bv, bayer_labels=True)
            p.dsos(mag=dso_mag, true_size=True)
            p.marker(
                ra=ra,
                dec=dec,
                label=target_name,
                style={
                    "marker": {
                        "size": 28,
                        "symbol": "circle",
                        "edge_color": "#cccccc",
                        "alpha": 0.3,
                    },
                    "label": {
                        "font_size": 12,
                        "font_weight": "bold",
                        "font_color": "#FFFFFF",
                        "font_alpha": 0.8,
                    },
                },
            )
            filename = f"ast_starplot_optic_{uuid4().hex}.png"
            file_path = os.path.abspath(os.path.join(config.static_folder, filename))
            url = config.static_content_url + "/" + filename
            p.export(file_path, padding=0, transparent=True)
            return f"<image>![Optic Plot]({url})</image>"
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error generating optic starplot: {str(e)}"


if __name__ == "__main__":
    tool = StarplotOpticTool()
    print(
        tool.invoke(
            {
                "latitude": 32.84,
                "longitude": -117.1860,
                "time": datetime.now().astimezone(),
                "target_name": "Orion",
                "ra": 5.583,
                "dec": -5.383,
                "sensor_height": 15.6,
                "sensor_width": 23.6,
                "lens_focal_length": 880,
                "rotation": 0,
            }
        )
    )
