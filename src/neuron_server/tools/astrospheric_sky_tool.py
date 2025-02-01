import asyncio
from typing import Any

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.config import config
from neuron_server.logger import logger


@cache_response(ttl=60 * 60 * 24)
async def get_astrospheric_objects(
    latitude: float, longitude: float, mssinceepoch: int
) -> str:
    async with aiohttp.ClientSession() as session:
        url = "https://astrosphericpublicaccess.azurewebsites.net/api/GetSky_V1"
        logger.debug(f"POST <{url}>")
        async with session.post(
            url,
            json={
                "Latitude": latitude,
                "Longitude": longitude,
                "MSSinceEpoch": mssinceepoch,
                "APIKey": config.astrospheric_api_key,
            },
        ) as response:
            response.raise_for_status()
            return (await response.text(encoding="utf-8")).strip()


class AstrosphericSkyToolArgs(BaseModel):
    latitude: float = Field(description="Latitude")
    longitude: float = Field(description="Longitude")
    mssinceepoch: int = Field(
        description=(
            "Milliseconds since epoch in UTC. Round times to the nearest hour "
            "to improve caching"
        )
    )


class AstrosphericSkyTool(BaseTool):
    name: str = "astrospheric_sky"
    description: str = (
        "Provided a Latitude, Longitude, and time (in UTC), this function will "
        "return the current locations of the planets and stars currently above "
        "the horizon. The star database includes stars under a brightness "
        "magnitude 5 (the lower the number the brighter the object). Sun and "
        "Moon information will always be included, even if their position is "
        "below the horizon. Use this tool to answer questions about the night sky."
    ).strip()

    args_schema: type[AstrosphericSkyToolArgs] = AstrosphericSkyToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(self, latitude: float, longitude: float, mssinceepoch: int) -> str:
        if not config.astrospheric_api_key or len(config.astrospheric_api_key) == 0:
            return "Astrospheric API key is not set"
        try:
            return await get_astrospheric_objects(
                latitude=latitude, longitude=longitude, mssinceepoch=mssinceepoch
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error fetching astronomy sky: {str(e)}"
