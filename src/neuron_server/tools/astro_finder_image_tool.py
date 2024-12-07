from langchain.tools import BaseTool
from typing import Type, List
from pydantic import BaseModel, Field
import argparse
from astropy.coordinates import SkyCoord
from astropy import units as u
from astroplan import FixedTarget
from astroplan.plots import plot_finder_image
import matplotlib.pyplot as plt
from neuron_server.config import config
from neuron_server.logger import logger
import matplotlib
from astroplan.plots import dark_style_sheet
from uuid import uuid4

matplotlib.use("Agg")


class Target(BaseModel):
    name: str = Field(description="Object name")
    ra: float = Field(
        description="Target right ascension in degrees. High precision is recommended."
    )
    dec: float = Field(
        description="Target declination in degrees. High precision is recommended."
    )


class AstroFinderImageToolArgs(BaseModel):
    targets: List[Target] = Field(
        description="A list of targets, each target must have a name and it's ra/dec coordinates in degrees. High precision is recommended."
    )
    fov_radius: float = Field(
        description="The field of view radius in arcminutes. Take into account the camera's FOV and the target's size. Defaults to 10.",
        default=10,
    )


def create_finder_images(targets: List[FixedTarget], fov_radius: float = 10) -> str:
    matplotlib.rcdefaults()
    matplotlib.rcParams.update(dark_style_sheet)
    images = []
    for target in targets:
        filename = f"ast_finder_image_{uuid4().hex}.png"
        file_path = f"{config.static_folder}/images/{filename}"
        url = f"{config.static_content_url}/images/{filename}"
        plot_finder_image(
            target=target,
            reticle=True,
            grid=True,
            fov_radius=fov_radius * u.arcmin,
        )
        plt.savefig(file_path)
        plt.close()
        images.append(f"![{target.name} Finder Image]({url})")
    matplotlib.rcdefaults()
    return "\n".join(images)


class AstroFinderImageTool(BaseTool):
    name: str = "astro_finder_image"
    description: str = (
        """
This tool accepts a list of targets and plots finder images for each target. These are used to help identify objects in the sky when looking through a telescope.
""".strip()
    )

    args_schema: Type[AstroFinderImageToolArgs] = AstroFinderImageToolArgs

    def _run(
        self,
        targets: List[Target],
        fov_radius: float = 10,
    ) -> str:
        try:
            sky_targets = [
                FixedTarget(
                    coord=SkyCoord(ra=target.ra * u.deg, dec=target.dec * u.deg),
                    name=target.name,
                )
                for target in targets
            ]
            return create_finder_images(targets=sky_targets, fov_radius=fov_radius)
        except Exception as e:
            logger.exception(e)
            return f"Error: {str(e)}"


def main():
    parser = argparse.ArgumentParser(description="Astro Tool CLI")
    parser.add_argument(
        "--name",
        type=str,
        help="Target name",
        default="M31",
    )
    parser.add_argument(
        "--ra",
        type=float,
        help="Target right ascension in degrees",
        default=10.68458,
    )
    parser.add_argument(
        "--dec", type=float, help="Target declination in degrees", default=41.26917
    )

    args = parser.parse_args()

    tool = AstroFinderImageTool()
    result = tool._run(
        targets=[
            Target(name=args.name, ra=args.ra, dec=args.dec),
        ]
    )
    print(result)


if __name__ == "__main__":
    main()
