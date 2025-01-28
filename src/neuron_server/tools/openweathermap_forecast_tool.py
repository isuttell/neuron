import asyncio

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.config import config
from neuron_server.logger import logger


@cache_response(ttl=60 * 10)
async def get_openweathermap_forecast(lat: float, lon: float) -> str:
    async with aiohttp.ClientSession() as session:
        url = "https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&exclude={exclude}&appid={api_key}".format(
            lat=lat,
            lon=lon,
            exclude=",".join(["minutely"]),
            api_key=config.openweather_api_key,
        )
        logger.debug(f"GET <{url}>")
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()


class OpenWeatherMapForecastToolArgs(BaseModel):
    lat: float = Field(description="Latitude")
    lon: float = Field(description="Longitude")


class OpenWeatherMapForecastTool(BaseTool):
    name: str = "openweathermap_forecast"
    description: str = (
        """
Provides real-time weather, 48-hour hourly forecasts, 8-day daily forecasts, and government-issued weather alerts for any location using latitude and longitude from OpenWeatherMap.org. Data is updated every 10 minutes""".strip()
    )

    args_schema: type[OpenWeatherMapForecastToolArgs] = OpenWeatherMapForecastToolArgs

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        lat: float,
        lon: float,
    ) -> str:
        if not config.openweather_api_key or len(config.openweather_api_key) == 0:
            return "No OpenWeatherMap API key found"

        try:
            return await get_openweathermap_forecast(lat, lon)
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error fetching forecast: {str(e)}"
