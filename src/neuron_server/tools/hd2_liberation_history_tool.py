import asyncio
from datetime import UTC, datetime
from statistics import mean
from typing import Any

import aiohttp
from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from neuron_server.cache import cache_response
from neuron_server.logger import logger


class LiberationEntry(BaseModel):
    """Model for a single liberation history entry."""

    timestamp: int = Field(description="Unix timestamp of the entry")
    health: int = Field(description="Current health value")
    players: int = Field(description="Number of active players")
    defense: bool = Field(
        default=False, description="Whether this is a defense mission"
    )
    percentage: float = Field(description="Liberation progress percentage")

    @classmethod
    def from_api_response(cls, data: dict) -> "LiberationEntry":
        """Create a LiberationEntry from API response data."""
        # Convert ISO timestamp to Unix timestamp
        created_at = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        timestamp = int(created_at.timestamp())

        # Calculate percentage (inverted since 100% health = 0% liberation)
        percentage = (
            (1 - data["current_health"] / data["max_health"]) * 100
            if data["max_health"] > 0
            else 0
        )

        return cls(
            timestamp=timestamp,
            health=data["current_health"],
            players=data["player_count"],
            defense=False,  # API doesn't provide this info
            percentage=percentage,
        )

    class Config:
        populate_by_name = True


@cache_response(ttl=60 * 5)
async def get_liberation_history(planet_index: int) -> list[LiberationEntry]:
    """Fetch liberation history data with caching."""
    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=10)
    ) as session:
        url = f"https://helldiverstrainingmanual.com/api/v1/war/history/{planet_index}"
        logger.debug(f"GET {url}")
        async with session.get(url) as response:
            response.raise_for_status()
            data: list[dict[str, Any]] = await response.json()
            return [LiberationEntry.from_api_response(entry) for entry in data]


def calculate_trends(entries: list[LiberationEntry]) -> dict[str, Any]:
    """Calculate various trends from the liberation history data."""
    if not entries:
        return {
            "peak_players": 0,
            "peak_time": None,
            "avg_players": 0,
            "player_trend": "No data",
            "liberation_rate": 0,
            "peak_activity_period": "No data",
        }

    # Sort entries by timestamp for calculations
    sorted_entries = sorted(entries, key=lambda x: x.timestamp)

    # Player statistics
    players = [entry.players for entry in entries]
    peak_players = max(players)
    peak_entry = next(entry for entry in entries if entry.players == peak_players)
    peak_time = datetime.fromtimestamp(peak_entry.timestamp, UTC)
    avg_players = round(mean(players), 1)

    # Calculate player trend
    first_quarter = mean(players[: len(players) // 4])
    last_quarter = mean(players[-len(players) // 4 :])
    if last_quarter > first_quarter * 1.1:
        trend = "increasing"
    elif last_quarter < first_quarter * 0.9:
        trend = "decreasing"
    else:
        trend = "stable"

    # Calculate liberation rate (percentage change per hour)
    min_entries_for_rate = 2
    if len(sorted_entries) >= min_entries_for_rate:
        time_diff = sorted_entries[-1].timestamp - sorted_entries[0].timestamp
        percentage_diff = sorted_entries[0].percentage - sorted_entries[-1].percentage
        hours_diff = time_diff / 3600
        liberation_rate = (
            round(percentage_diff / hours_diff, 2) if hours_diff > 0 else 0
        )
    else:
        liberation_rate = 0

    # Find peak activity period
    hour_counts = {}
    for entry in entries:
        hour = datetime.fromtimestamp(entry.timestamp, UTC).hour
        hour_counts[hour] = hour_counts.get(hour, 0) + entry.players

    peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0]
    peak_period = f"{peak_hour:02d}:00-{(peak_hour + 1) % 24:02d}:00 UTC"

    return {
        "peak_players": peak_players,
        "peak_time": peak_time,
        "avg_players": avg_players,
        "player_trend": trend,
        "liberation_rate": liberation_rate,
        "peak_activity_period": peak_period,
    }


def format_history_table(entries: list[LiberationEntry]) -> str:
    """Format the history entries into a markdown table."""
    if not entries:
        return "No history data available"

    headers = (
        "| Time (UTC) | Health | Players | Defense | Progress |\n"
        "|------------|---------|----------|----------|------------|"
    )

    def format_entry(entry: LiberationEntry) -> str:
        timestamp = datetime.fromtimestamp(entry.timestamp, UTC)
        mission_type = "Defense" if entry.defense else "Liberation"
        return (
            f"| {timestamp.strftime('%Y-%m-%d %H:%M')} | {entry.health:,} | "
            f"{entry.players} | {mission_type} | {entry.percentage:.2f}% |"
        )

    rows = "\n".join(
        format_entry(entry)
        for entry in sorted(entries, key=lambda x: x.timestamp, reverse=True)[:24]
    )  # Show last 2 hours (24 entries at 5-minute intervals)

    return f"{headers}\n{rows}"


class HD2LiberationHistoryToolArgs(BaseModel):
    """Arguments for the HD2 Liberation History Tool."""

    planet_index: int = Field(
        description=(
            "The index of the planet to get the liberation history for. "
            "Found in the galactic war report."
        )
    )


class HD2LiberationHistoryTool(BaseTool):
    name: str = "hd2_liberation_history"
    description: str = (
        "Provides the detailed liberation history of a given planet. Returns the "
        "liberation status in 5 minutes intervals (with some variance). Status is "
        "only recorded when planet is active during a campaign. Ordered from newest "
        "to latest, limited to 288 results (24 hours). Use it to calculate the time "
        "until a planet is liberated."
    )
    args_schema: type[HD2LiberationHistoryToolArgs] = HD2LiberationHistoryToolArgs

    def _run(self, planet_index: int) -> str:
        return asyncio.run(self._arun(planet_index))

    async def _arun(self, planet_index: int) -> str:
        try:
            assert planet_index > 0, "Planet index must be greater than 0"
            entries = await get_liberation_history(planet_index)

            if not entries:
                return "No liberation history available for this planet."

            trends = calculate_trends(entries)
            latest = max(entries, key=lambda x: x.timestamp)
            timestamp = datetime.now(UTC).isoformat(timespec="seconds")

            return f"""
# Planet Liberation History Report for {timestamp}

## Current Status
- Health: {latest.health:,}
- Players: {latest.players}
- Liberation Progress: {latest.percentage:.2f}%
- Mission Type: {"Defense" if latest.defense else "Liberation"}

## Analysis
- Peak Players: {trends["peak_players"]}
  Time: {trends["peak_time"].strftime("%Y-%m-%d %H:%M UTC")}
- Average Players: {trends["avg_players"]}
- Player Count Trend: {trends["player_trend"].title()}
- Liberation Rate: {trends["liberation_rate"]}% per hour
- Peak Activity Period: {trends["peak_activity_period"]}

## Recent History (Last 2 Hours)
{format_history_table(entries)}

Note: Data is updated every 5 minutes when the planet is active in a campaign.
* Health represents the campaign's abstract progress value
* Defense indicates if this was a defensive mission
* Progress shows the liberation percentage
""".strip()

        except aiohttp.ClientError as e:
            logger.error(f"HTTP error fetching liberation history: {e}", exc_info=True)
            return f"Error fetching liberation history: {str(e)}"
        except Exception as e:
            logger.error(f"Error processing liberation history: {e}", exc_info=True)
            return f"Error processing liberation history: {str(e)}"


async def main() -> None:
    """Test function for direct script execution."""
    tool = HD2LiberationHistoryTool()
    print(await tool.ainvoke({"planet_index": 162}))


if __name__ == "__main__":
    asyncio.run(main())
