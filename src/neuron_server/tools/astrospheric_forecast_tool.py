import asyncio
from typing import Any

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.config import config
from neuron_server.logger import logger


@cache_response(ttl=60 * 60 * 6)
async def get_astrospheric_forecast(latitude: float, longitude: float) -> str:
    async with aiohttp.ClientSession() as session:
        url = (
            "https://astrosphericpublicaccess.azurewebsites.net/api/GetForecastData_V1"
        )
        logger.debug(f"POST <{url}>")
        async with session.post(
            url,
            json={
                "Latitude": latitude,
                "Longitude": longitude,
                "APIKey": config.astrospheric_api_key,
            },
        ) as response:
            response.raise_for_status()
            return await response.text()


class AstrosphericForecastToolArgs(BaseModel):
    latitude: float = Field(description="Latitude")
    longitude: float = Field(description="Longitude")


class AstrosphericForecastTool(BaseTool):
    name: str = "astrospheric_forecast"
    description: str = (
        "This tool provides an 81-hour astronomical forecast using Astrospheric's API, "
        "updating every 6 hours. It evaluates key observing conditions including cloud "
        "cover (0-100%, where 0% is clear), atmospheric transparency, and seeing "
        "conditions. The transparency index (0-27+) indicates overall atmospheric "
        "clarity, with lower numbers being better: 0-5 excellent, 6-9 above average, "
        "10-13 average, 14-23 below average, 24-27 poor, >27 cloudy. The seeing index "
        "(0-5) measures atmospheric stability affecting image steadiness: 0 cloudy, "
        "1 poor, 2 below average, 3 average, 4 above average, 5 excellent. Additional "
        "parameters include temperature, dew point, wind velocity, and direction. Use "
        "this tool to identify optimal viewing windows when transparency and seeing "
        "conditions are favorable (lower transparency numbers, higher seeing numbers) "
        "and cloud cover is minimal."
    ).strip()

    args_schema: type[AstrosphericForecastToolArgs] = AstrosphericForecastToolArgs

    def _run(self, *args: Any, **kwargs: Any) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        latitude: float,
        longitude: float,
    ) -> str:
        if not config.astrospheric_api_key or len(config.astrospheric_api_key) == 0:
            return "Astrospheric API key is not set"
        try:
            return await get_astrospheric_forecast(
                latitude=latitude, longitude=longitude
            )
        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error fetching astronomy forecast: {str(e)}"
