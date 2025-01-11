from langchain.tools import BaseTool
from typing import Type, Optional
from neuron_server.config import config
import aiohttp
import asyncio
from neuron_server.logger import logger
from neuron_server.cache import cache_response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, TypedDict
from datetime import datetime, timezone
from neuron_server.graph import process_document
from langchain_core.runnables import RunnableConfig


class Biome(BaseModel):
    slug: str
    description: str


class Campaign(BaseModel):
    planetIndex: int
    name: str
    faction: str
    players: int
    health: int
    maxHealth: int
    percentage: float
    defense: bool
    biome: Optional[Biome] = None
    expireDateTime: Optional[float] = None


@cache_response(ttl=60 * 1)
async def get_campaigns() -> List[Campaign]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/campaign"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            rows: List[Dict[str, Any]] = await response.json()
            return [Campaign(**row) for row in rows]


class News(BaseModel):
    id: int
    published: int
    type: int
    tagIds: List[str]
    message: str


@cache_response(ttl=60 * 1)
async def get_news() -> List[News]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/news"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            rows: List[Dict[str, Any]] = await response.json()
            return [News(**row) for row in rows]


class Environmentals(BaseModel):
    name: str
    description: str


class Planet(BaseModel):
    name: str
    sector: str
    biome: Optional[Biome] = None
    environmentals: List[Environmentals]


@cache_response(ttl=60 * 60 * 24)
async def get_planets() -> Dict[str, Planet]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/planets"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            data: Dict[str, Dict[str, Any]] = await response.json()
            results = {}
            for id, row in data.items():
                results[id] = Planet(**row)
            return results


class Task(BaseModel):
    type: int
    values: List[int]
    valueTypes: List[int]


class Reward(BaseModel):
    type: int
    id32: int
    amount: int


class Setting(BaseModel):
    type: int
    overrideTitle: str
    overrideBrief: str
    taskDescription: str
    tasks: List[Task]
    rewards: List[Reward]
    reward: Reward
    flags: int


class MajorOrder(BaseModel):
    id32: int
    progress: List[int]
    expiresIn: int
    setting: Setting


class MajorOrdersResponse(BaseModel):
    major_orders: List[MajorOrder]


@cache_response(ttl=60 * 1)
async def get_major_orders() -> List[MajorOrder]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/major-orders"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            rows: List[Dict[str, Any]] = await response.json()
            return [MajorOrder(**row) for row in rows]


class GlobalEvent(TypedDict):
    eventId: int
    title: str
    message: str


class SpaceStation(TypedDict):
    id32: int
    planetIndex: int
    activeEffectIds: List[int] = []
    currentElectionEndWarTime: int
    flags: int


class Coordinates(BaseModel):
    x: float
    y: float


class PlanetStatus(TypedDict):
    index: int
    owner: int
    health: int
    regenPerSecond: float
    players: int
    position: Coordinates


class PlanetAttack(TypedDict):
    source: int
    target: int


class WarStatus(TypedDict):
    time: int
    warId: int
    globalEvents: List[GlobalEvent]
    spaceStations: List[SpaceStation]
    planetStatus: List[PlanetStatus]
    planetAttacks: List[PlanetAttack]
    layoutVersion: int


@cache_response(ttl=60 * 1)
async def get_war_status() -> WarStatus:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/status"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()


def format_campaigns(
    campaigns: List[Campaign], planet_statuses: List[PlanetStatus]
) -> str:
    if len(campaigns) == 0:
        return "No active campaigns"

    headers = "| Planet | Index | Faction | Players | Health | Health Regen Per Second | Percentage | Mission Type |\n|--------|--------|--------|--------|--------------------|--------|--------|"
    campaign_rows = "\n".join(
        [
            f"| {campaign.name} | {campaign.planetIndex} | {campaign.faction} | {campaign.players} | {campaign.health} | {round(planet_statuses[campaign.planetIndex]['regenPerSecond'], 2)} | {round(campaign.percentage, 2)}% | {'Defense' if campaign.defense else 'Liberate'} |"
            for campaign in campaigns
        ]
    )
    return f"""
{headers}
{campaign_rows}
* Health is an abstract representation of the campaign's progress. It is not the actual health of the planet.
** Health regen is how fast the enemy is retaking the planet aka reenforcement rate. 0-5 is low and means retaking the planet is easier, 6-10 is moderate meaning it's  harder to liberate and represents a balanced challenge, 11-15 is high regeneration and require significant and sustained effort to liberate, 16-20+ is extremely challenging. Talk about it using in universe terms.
*** Only percentages are shown in game so this is the only value that should be shown to the user.""".strip()


def format_major_orders(
    major_orders: List[MajorOrder], planets: Dict[str, Planet]
) -> str:
    if len(major_orders) == 0:
        return "No major orders."

    return "\n".join(
        f"* {major_order.setting.overrideBrief}"
        + "".join(
            f"\n  - {planets[str(task.values[2])].name if str(task.values[2]) in planets else 'Unknown Planet'}{' (Completed)' if major_order.progress[index] == 1 else ''}"
            for index, task in enumerate(major_order.setting.tasks)
        )
        for major_order in major_orders
    )


def format_planet_attacks(
    planet_attacks: List[PlanetAttack], planets: Dict[str, Planet]
) -> str:
    if len(planet_attacks) == 0:
        return "No planet attacks"

    headers = "| Source | Target |\n|--------|--------|"
    planet_attack_rows = "\n".join(
        [
            f"| {planets[str(attack['source'])].name} | {planets[str(attack['target'])].name} |"
            for attack in planet_attacks
        ]
    )
    return f"{headers}\n{planet_attack_rows}\n* The target is being attacked by the source planet"


def format_environmentals(planet: Planet) -> str:
    return "<br />".join(
        [
            f"* {environmental.name}: {environmental.description}"
            for environmental in planet.environmentals
        ]
    )


def format_planet(planet: Planet) -> str:
    return f"| {planet.name} | {planet.sector} | {planet.biome.description if planet.biome else 'N/A'} | {format_environmentals(planet) if planet.environmentals else 'None'} |"


def format_planets(planets: List[Planet]) -> str:
    if len(planets) == 0:
        return "No planets"

    headers = (
        "| Planet | Sector | Biome | Hazards |\n|--------|--------|-------|---------|"
    )
    planet_rows = "\n".join(format_planet(planet) for planet in planets)
    return f"{headers}\n{planet_rows}"


def format_news(messages: List[News]) -> str:
    if len(messages) == 0:
        return "No news"

    headers = "| Message | Published |\n|--------|---------|"
    message_rows = "\n".join(
        [
            f"| {news.message} | {str(news.published)} |".replace("\n", "<br />")
            for news in messages
        ]
    )
    return f"{headers}\n{message_rows}"


def format_global_events(events: List[GlobalEvent]) -> str:
    if len(events) == 0:
        return "No global events"

    headers = "| Title | Message |\n|--------|---------|"
    event_rows = "\n".join(
        [
            f"| {event['title']} | {event['message']} |".replace("\n", "<br />")
            for event in events
            if len(event["message"]) > 0 and "message" in event
        ]
    )
    return f"{headers}\n{event_rows}"


class HD2GalacticWarReportTool(BaseTool):
    name: str = "hd2_galactic_war_report"
    description: str = (
        """
Get's the latest report on the in universe Hell Divers 2 Galactic War. Includes information on global events, latest major order, in-game news, and the current status of all active campaigns with details on the planet's health, health regen per second, and percentage of the mission completed. This should be considered the source of truth for the current state of the war. Updates every 5 minutes.
""".strip()
    )

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        config: RunnableConfig,
    ) -> str:
        try:
            war_status = await get_war_status()
            assert war_status["layoutVersion"] == 24
            planets = await get_planets()
            campaigns = await get_campaigns()
            major_orders = await get_major_orders()

            for global_event in war_status["globalEvents"]:
                text = f"Hell Divers 2:\nEvent ID: {global_event['eventId']}\n{global_event['title']}\n{global_event['message']}".strip()
                await process_document(
                    text=text,
                    document_id=f"global_event:{global_event['eventId']}",
                    config=config,
                )

            for major_order in major_orders:
                text = f"Hell Divers 2:\n{major_order.setting.overrideTitle}\nMajor Order ID: {major_order.id32}\n{major_order.setting.overrideBrief}\n{major_order.setting.taskDescription}".strip()
                await process_document(
                    text=text,
                    document_id=f"major_order:{major_order.id32}",
                    config=config,
                )

            active_planets: List[Planet] = list(
                map(
                    lambda campaign: planets[str(campaign.planetIndex)],
                    campaigns,
                )
            )

            return f"""
# Hell Divers 2 Galactic War Report for {datetime.now(timezone.utc).isoformat(timespec="seconds")}

Classified Top Secret

## War Status

War Time: {war_status["time"]}

{format_global_events(war_status["globalEvents"])}

## Major Orders

{format_major_orders(major_orders, planets)}

## Active Campaigns

{format_campaigns(campaigns, war_status["planetStatus"])}

## Planet Attacks

{format_planet_attacks(war_status["planetAttacks"], planets)}

## Planets

{format_planets(active_planets)}
        """.strip()

        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error getting HD2 Galactic War Report: {str(e)}"


async def main():
    tool = HD2GalacticWarReportTool()
    print(
        await tool.ainvoke(input={}, config={"configurable": {"personality_id": "1"}})
    )


if __name__ == "__main__":
    asyncio.run(main())
