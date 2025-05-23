import asyncio
import json
from datetime import UTC, datetime
from typing import Any

import aiohttp
from langchain.tools import BaseTool
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from neuron_server.cache import cache_response
from neuron_server.logger import logger


# Define input schema with optional custom instructions
class HD2GalacticWarReportToolArgs(BaseModel):
    custom_instructions: str = ""


@cache_response(ttl=60 * 5)
async def get_campaigns() -> list[dict[str, Any]]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/campaign"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()


@cache_response(ttl=60 * 5)
async def get_news() -> list[dict[str, Any]]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/news"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()


@cache_response(ttl=60 * 60 * 24)
async def get_planets() -> dict[str, dict[str, Any]]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/planets"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()


@cache_response(ttl=60 * 5)
async def get_major_orders() -> list[dict[str, Any]]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/major-orders"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()


@cache_response(ttl=60 * 5)
async def get_war_status() -> dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/status"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()

class HD2GalacticWarReportTool(BaseTool):
    name: str = "hd2_galactic_war_report"
    args_schema: type[HD2GalacticWarReportToolArgs] = HD2GalacticWarReportToolArgs
    description: str = """
Gets a focused status report on the in-universe Helldivers 2 Galactic War. Returns a
concise markdown report covering current major orders, active factions, key objectives,
breaking news, and overall war status. The report is dynamically generated from live
API data and focuses only on relevant information for strategic decision making.
""".strip()

    def _run(self) -> str:
        # This tool is async only, raise error or implement sync logic if needed
        raise NotImplementedError("Use async invoke for this tool")

    async def _arun(
        self,
        config: RunnableConfig,
        custom_instructions: str = "",
    ) -> str:
        try:
            # Fetch all data from the APIs
            war_status = await get_war_status()
            planets = await get_planets()
            campaigns = await get_campaigns()
            major_orders = await get_major_orders()
            news = await get_news()

            # Compile the raw data
            timestamp = datetime.now(UTC).isoformat(timespec="seconds")
            report_data = {
                "timestamp": timestamp,
                "war_status": war_status,
                "planets": planets,
                "campaigns": campaigns,
                "major_orders": major_orders,
                "news": news
            }

            # Create prompt template for generating focused markdown report
            system_prompt = """You are an expert military intelligence analyst
for Super Earth in the Helldivers 2 universe. Always stay in character and
in universe.

Create a concise, official military status report in markdown format based on
the provided API data.

Focus on:
- Current major orders and their progress
- Active factions and key battlefronts
- Critical objectives and strategic priorities
- Significant events
- Overall war status assessment

Use military terminology and in-universe language (Helldivers, Super Earth, etc.).
Keep it concise and focus on actionable intelligence.

Data interpretation notes:
- Health values: Lower = closer to completion for humans
- regenPerSecond: Enemy reinforcement rate (0-5=easy, 6-10=moderate,
  11-15=hard, 16+=extreme)
- Campaign percentages are what players see in-game
- Defense missions = holding territory, Liberation missions = taking territory"""

            human_prompt = (
                "Generate a Helldivers 2 Galactic War Report based on this data:"
                "\n\n{json_data}"
            )

            # Add custom instructions to human prompt if provided
            if custom_instructions.strip():
                human_prompt = (
                    f"SPECIAL REQUEST: {custom_instructions.strip()}\n\n"
                    + human_prompt
                )

            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", human_prompt)
            ])

            # Get LLM instance
            from neuron_server.models.provider_model import ProviderModelModel
            llm = await ProviderModelModel.get_active_llm()

            # Create the chain with string output parser
            chain = prompt | llm | StrOutputParser()

            # Generate the report
            json_data = json.dumps(report_data, indent=2)
            return await chain.ainvoke({"json_data": json_data}, config=config)

        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error generating HD2 Galactic War Report: {str(e)}"


async def main() -> None:
    tool = HD2GalacticWarReportTool()
    print(
        await tool.ainvoke(input={}, config={"configurable": {"personality_id": "1"}})
    )


if __name__ == "__main__":
    asyncio.run(main())
