import asyncio
import time

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.logger import logger


@cache_response(ttl=60 * 5)
async def get(url: str) -> str:
    start_time = time.perf_counter()
    status_code = None
    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=10)
        ) as session:
            async with session.get(url) as response:
                status_code = response.status
                return await response.text()
    finally:
        logger.debug(
            f"GET {url} - {time.perf_counter() - start_time:.2f}s - {status_code or '-1'}"
        )


class HD2LiberationHistoryToolArgs(BaseModel):
    planet_index: int = Field(
        description="The index of the planet to get the liberation history for. Found in the galactic war report."
    )


class HD2LiberationHistoryTool(BaseTool):
    name: str = "hd2_liberation_history"
    description: str = (
        "Provides the detailed liberation history of a given planet. Returns the liberation status in 5 minutes intervals (with some variance). Status is only recorded when planet is active during a campaign. Ordered from newest to latest, limited to 288 results (24 hours). Use it to calculate the time until a planet is liberated."
    )
    args_schema: type[HD2LiberationHistoryToolArgs] = HD2LiberationHistoryToolArgs

    def _run(self, planet_index: int) -> str:
        return asyncio.run(self._arun(planet_index))

    async def _arun(self, planet_index: int) -> str:
        assert planet_index > 0, "Planet index must be greater than 0"
        return await get(
            f"https://helldiverstrainingmanual.com/api/v1/war/history/{planet_index}"
        )
