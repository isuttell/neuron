import asyncio
from datetime import UTC, datetime
from typing import Any  # Removed Type

import aiohttp
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.graph.document import DocumentMetadata, process_document
from neuron_server.logger import logger


# Define an empty input schema for tools that don't take arguments
class HD2GalacticWarReportToolArgs(BaseModel):
    pass


class Biome(BaseModel):
    slug: str
    description: str


class Campaign(BaseModel):
    planet_index: int = Field(alias="planetIndex")
    name: str
    faction: str
    players: int
    health: int
    max_health: int = Field(alias="maxHealth")
    percentage: float
    defense: bool
    biome: Biome | None = None
    expire_date_time: float | None = Field(alias="expireDateTime", default=None)

    class Config:
        populate_by_name = True


@cache_response(ttl=60 * 1)
async def get_campaigns() -> list[Campaign]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/campaign"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            rows: list[dict[str, Any]] = await response.json()
            return [Campaign(**row) for row in rows]


class News(BaseModel):
    id: int
    published: int
    type: int
    tag_ids: list[str] = Field(alias="tagIds")
    message: str

    class Config:
        populate_by_name = True


@cache_response(ttl=60 * 1)
async def get_news() -> list[News]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/news"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            rows: list[dict[str, Any]] = await response.json()
            return [News(**row) for row in rows]


class Environmentals(BaseModel):
    name: str
    description: str


class Planet(BaseModel):
    name: str
    sector: str
    biome: Biome | None = None
    environmentals: list[Environmentals]


@cache_response(ttl=60 * 60 * 24)
async def get_planets() -> dict[str, Planet]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/planets"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            data: dict[str, dict[str, Any]] = await response.json()
            results = {}
            for planet_id, row in data.items():
                results[planet_id] = Planet(**row)
            return results


class Task(BaseModel):
    type: int
    values: list[int]
    value_types: list[int] = Field(alias="valueTypes")


class Reward(BaseModel):
    type: int
    id32: int
    amount: int


class Setting(BaseModel):
    type: int
    override_title: str = Field(alias="overrideTitle")
    override_brief: str = Field(alias="overrideBrief")
    task_description: str = Field(alias="taskDescription")
    tasks: list[Task]
    rewards: list[Reward]
    reward: Reward
    flags: int

    class Config:
        populate_by_name = True


class MajorOrder(BaseModel):
    id32: int
    progress: list[int]
    expires_in: int = Field(alias="expiresIn")
    setting: Setting

    class Config:
        populate_by_name = True


class MajorOrdersResponse(BaseModel):
    major_orders: list[MajorOrder]


@cache_response(ttl=60 * 1)
async def get_major_orders() -> list[MajorOrder]:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/major-orders"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            rows: list[dict[str, Any]] = await response.json()
            return [MajorOrder(**row) for row in rows]


class GlobalEvent(BaseModel):
    event_id: int = Field(alias="eventId")
    title: str
    message: str

    class Config:
        populate_by_name = True


class SpaceStation(BaseModel):
    id32: int
    planet_index: int = Field(alias="planetIndex")
    active_effect_ids: list[int] = Field(alias="activeEffectIds", default=[])
    current_election_end_war_time: int = Field(alias="currentElectionEndWarTime")
    flags: int

    class Config:
        populate_by_name = True


class Coordinates(BaseModel):
    x: float
    y: float


class PlanetStatus(BaseModel):
    index: int
    owner: int
    health: int
    regen_per_second: float = Field(alias="regenPerSecond")
    players: int
    position: Coordinates

    class Config:
        populate_by_name = True


class PlanetAttack(BaseModel):
    source: int
    target: int

    class Config:
        populate_by_name = True


class WarStatus(BaseModel):
    time: int
    war_id: int = Field(alias="warId")
    global_events: list[GlobalEvent] = Field(alias="globalEvents")
    space_stations: list[SpaceStation] = Field(alias="spaceStations")
    planet_status: list[PlanetStatus] = Field(alias="planetStatus")
    planet_attacks: list[PlanetAttack] = Field(alias="planetAttacks")
    layout_version: int | None = Field(alias="layoutVersion")

    class Config:
        populate_by_name = True


@cache_response(ttl=60 * 1)
async def get_war_status() -> WarStatus:
    async with aiohttp.ClientSession() as session:
        url = "https://helldiverstrainingmanual.com/api/v1/war/status"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            return WarStatus(**data)


def format_campaigns(
    campaigns: list[Campaign], planet_statuses: list[PlanetStatus]
) -> str:
    if len(campaigns) == 0:
        return "No active campaigns"

    headers = (
        "| Planet | Index | Faction | Players | Health | Health Regen Per Second | "
        "Percentage | Mission Type |\n"
        "|--------|--------|--------|--------|--------------------|--------|--------|"
    )

    def format_campaign_row(campaign: Campaign) -> str:
        regen = round(planet_statuses[campaign.planet_index].regen_per_second, 2)
        percentage = round(campaign.percentage, 2)
        mission_type = "Defense" if campaign.defense else "Liberate"
        return (
            f"| {campaign.name} | {campaign.planet_index} | {campaign.faction} | "
            f"{campaign.players} | {campaign.health} | {regen} | "
            f"{percentage}% | {mission_type} |"
        )

    campaign_rows = "\n".join(format_campaign_row(campaign) for campaign in campaigns)
    return f"""
{headers}
{campaign_rows}
* Health is an abstract representation of the campaign's progress. It is not the actual
  health of the planet.
** Health regen is how fast the enemy is retaking the planet aka reenforcement rate.
   0-5 is low and means retaking the planet is easier, 6-10 is moderate meaning it's
   harder to liberate and represents a balanced challenge, 11-15 is high regeneration
   and require significant and sustained effort to liberate, 16-20+ is extremely
   challenging. Talk about it using in universe terms.
*** Only percentages are shown in game so this is the only value that should be shown
    to the user.""".strip()


def format_major_orders(
    major_orders: list[MajorOrder], planets: dict[str, Planet]
) -> str:
    if len(major_orders) == 0:
        return "No major orders."

    result = []
    for major_order in major_orders:
        order_text = f"* {major_order.setting.override_brief}"
        for index, task in enumerate(major_order.setting.tasks):
            planet_id = str(task.values[2])
            planet_name = (
                planets[planet_id].name if planet_id in planets else "Unknown Planet"
            )
            completed = " (Completed)" if major_order.progress[index] == 1 else ""
            order_text += f"\n  - {planet_name}{completed}"
        result.append(order_text)
    return "\n".join(result)


def format_planet_attacks(
    planet_attacks: list[PlanetAttack], planets: dict[str, Planet]
) -> str:
    if len(planet_attacks) == 0:
        return "No planet attacks"

    headers = "| Source | Target |\n|--------|--------|"
    planet_attack_rows = "\n".join(
        [
            (
                f"| {planets[str(attack.source)].name} | "
                f"{planets[str(attack.target)].name} |"
            )
            for attack in planet_attacks
        ]
    )
    return (
        f"{headers}\n{planet_attack_rows}\n"
        "* The target is being attacked by the source planet"
    )


def format_environmentals(planet: Planet) -> str:
    return "<br />".join(
        [
            f"* {environmental.name}: {environmental.description}"
            for environmental in planet.environmentals
        ]
    )


def format_planet(planet: Planet) -> str:
    biome_desc = planet.biome.description if planet.biome else "N/A"
    envs = format_environmentals(planet) if planet.environmentals else "None"
    return f"| {planet.name} | {planet.sector} | {biome_desc} | {envs} |"


def format_planets(planets: list[Planet]) -> str:
    if len(planets) == 0:
        return "No planets"

    headers = (
        "| Planet | Sector | Biome | Hazards |\n|--------|--------|-------|---------|"
    )
    planet_rows = "\n".join(format_planet(planet) for planet in planets)
    return f"{headers}\n{planet_rows}"


def format_news(messages: list[News]) -> str:
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


def format_global_events(events: list[GlobalEvent]) -> str:
    if len(events) == 0:
        return "No global events"

    headers = "| Title | Message |\n|--------|---------|"
    event_rows = "\n".join(
        [
            f"| {event.title} | {event.message} |".replace("\n", "<br />")
            for event in events
            if len(event.message) > 0
        ]
    )
    return f"{headers}\n{event_rows}"


class HD2GalacticWarReportTool(BaseTool):
    name: str = "hd2_galactic_war_report"
    args_schema: type[HD2GalacticWarReportToolArgs] = (
        HD2GalacticWarReportToolArgs  # Changed Type to type
    )
    description: str = """
Get's the latest report on the in universe Hell Divers 2 Galactic War. Includes
information on global events, latest major order, in-game news, and the current status
of all active campaigns with details on the planet's health, health regen per second,
and percentage of the mission completed. This should be considered the source of truth
for the current state of the war. Updates every 5 minutes.
""".strip()

    # Removed *args, **kwargs as they caused schema issues and aren't needed
    def _run(self) -> str:
        # This tool is async only, raise error or implement sync logic if needed
        raise NotImplementedError("Use async invoke for this tool")

    async def _arun(
        self,
        config: RunnableConfig,
    ) -> str:
        try:
            war_status = await get_war_status()

            planets = await get_planets()
            campaigns = await get_campaigns()
            major_orders = await get_major_orders()

            for global_event in war_status.global_events:
                text = (
                    f"Hell Divers 2:\nEvent ID: {global_event.event_id}\n"
                    f"{global_event.title}\n{global_event.message}"
                ).strip()
                metadata = DocumentMetadata(
                    document_id=f"global_event:{global_event.event_id}",
                    personality_id=config["configurable"].get("personality_id"),
                )
                await process_document(text=text, config=config, metadata=metadata)

            for major_order in major_orders:
                text = (
                    f"Hell Divers 2:\n{major_order.setting.override_title}\n"
                    f"Major Order ID: {major_order.id32}\n"
                    f"{major_order.setting.override_brief}\n"
                    f"{major_order.setting.task_description}"
                ).strip()
                metadata = DocumentMetadata(
                    document_id=f"major_order:{major_order.id32}",
                    personality_id=config["configurable"].get("personality_id"),
                )
                await process_document(text=text, config=config, metadata=metadata)

            active_planets: list[Planet] = [
                planets[str(campaign.planet_index)] for campaign in campaigns
            ]

            timestamp = datetime.now(UTC).isoformat(timespec="seconds")
            return f"""
# Hell Divers 2 Galactic War Report for {timestamp}

Classified Top Secret

## War Status

War Time: {war_status.time}

{format_global_events(war_status.global_events)}

## Major Orders

{format_major_orders(major_orders, planets)}

## Active Campaigns

{format_campaigns(campaigns, war_status.planet_status)}

## Planet Attacks

{format_planet_attacks(war_status.planet_attacks, planets)}

## Planets

{format_planets(active_planets)}
        """.strip()

        except Exception as e:
            logger.error(e, exc_info=True)
            return f"Error getting HD2 Galactic War Report: {str(e)}"


async def main() -> None:
    tool = HD2GalacticWarReportTool()
    print(
        await tool.ainvoke(input={}, config={"configurable": {"personality_id": "1"}})
    )


if __name__ == "__main__":
    asyncio.run(main())
