import asyncio

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.config import config
from neuron_server.logger import logger


@cache_response(ttl=60 * 10)
async def get_openweathermap_overview(lat: float, lon: float, date: str) -> str:
    async with aiohttp.ClientSession() as session:
        url = f"https://api.openweathermap.org/data/3.0/onecall/overview?lat={lat}&lon={lon}&date={date}&appid={config.openweather_api_key}"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()


class OpenWeatherMapOverviewToolArgs(BaseModel):
    lat: float = Field(description="Latitude")
    lon: float = Field(description="Longitude")
    date: str = Field(
        description="The date for the weather summary in YYYY-MM-DD format"
    )


class OpenWeatherMapOverviewTool(BaseTool):
    name: str = "openweathermap_overview"
    description: str = (
        """
Get a human-readable weather summary for today or tomorrow's forecast, utilizing OpenWeatherMap AI technologies. Use this for quick weather summaries. Data is updated every 10 minutes.
""".strip()
    )

    args_schema: type[OpenWeatherMapOverviewToolArgs] = OpenWeatherMapOverviewToolArgs

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        lat: float,
        lon: float,
        date: str,
    ) -> str:
        if not config.openweather_api_key or len(config.openweather_api_key) == 0:
            return "No OpenWeatherMap API key found"

        try:
            return await get_openweathermap_overview(lat, lon, date)
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error fetching forecast: {str(e)}"
