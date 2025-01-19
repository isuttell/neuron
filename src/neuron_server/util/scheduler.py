import redis.asyncio as redis
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal, Any, Callable, Awaitable
from dataclasses import dataclass
import pytz
import logging

logger = logging.getLogger(__name__)


@dataclass
class RecurringPattern:
    """Defines a recurring schedule pattern"""

    interval: int
    unit: Literal["seconds", "minutes", "hours", "days", "weeks", "months"]
    time_of_day: Optional[str] = (
        None  # HH:MM:SS or HH:MM format for daily/weekly/monthly
    )
    day_of_week: Optional[int] = None  # 0-6 for weekly (0 is Monday)
    day_of_month: Optional[int] = None  # 1-31 for monthly


from typing import TypedDict, Optional


class ScheduledEvent(TypedDict):
    event_id: str
    event_data: Dict[str, Any]
    scheduled_time: str
    created_at: str
    recurring_pattern: Optional[RecurringPattern]
    time_remaining_seconds: int


class AsyncRedisEventScheduler:

    on_event: Callable[[str, ScheduledEvent], Awaitable[None]]

    def __init__(
        self,
        timezone: str = "UTC",
        host: str = "localhost",
        port: int = 6379,
        db: int = 2,
        password: str = None,
    ):
        """Initialize the scheduler with a specific timezone."""
        self.db = db
        self.redis_client = redis.Redis(host=host, port=port, db=db, password=password)
        self.timezone = pytz.timezone(timezone)

        # Keys for storing event metadata
        self.metadata_prefix = "event_metadata:"
        self.active_events_set = "active_events"
        self.recurring_events_set = "recurring_events"

    def _calculate_next_occurrence(
        self, pattern: RecurringPattern, last_run: Optional[datetime] = None
    ) -> datetime:
        """Calculate the next occurrence based on the recurring pattern."""
        now = datetime.now(self.timezone)

        # Ensure last_run is in the correct timezone
        if last_run:
            if last_run.tzinfo is None:
                last_run = self.timezone.localize(last_run)
            else:
                last_run = last_run.astimezone(self.timezone)

        base_time = last_run if last_run else now

        if pattern.time_of_day:
            # Support both HH:MM:SS and HH:MM formats
            time_parts = pattern.time_of_day.split(":")
            if len(time_parts) == 3:
                hour, minute, second = map(int, time_parts)
            elif len(time_parts) == 2:
                hour, minute = map(int, time_parts)
                second = base_time.second
            else:
                raise ValueError("time_of_day must be in HH:MM:SS or HH:MM format")
        else:
            hour, minute, second = base_time.hour, base_time.minute, base_time.second

        next_time = base_time

        if pattern.unit == "seconds":
            next_time = base_time + timedelta(seconds=pattern.interval)

        elif pattern.unit == "minutes":
            next_time = base_time + timedelta(minutes=pattern.interval)

        elif pattern.unit == "hours":
            next_time = base_time + timedelta(hours=pattern.interval)

        elif pattern.unit == "days":
            next_time = base_time + timedelta(days=pattern.interval)
            next_time = next_time.replace(hour=hour, minute=minute, second=second)

        elif pattern.unit == "weeks":
            if pattern.day_of_week is not None:
                # Calculate days until next occurrence
                current_dow = base_time.weekday()
                days_ahead = pattern.day_of_week - current_dow
                if days_ahead <= 0:
                    days_ahead += 7 * pattern.interval
                else:
                    days_ahead += 7 * (pattern.interval - 1)
                next_time = base_time + timedelta(days=days_ahead)
                next_time = next_time.replace(hour=hour, minute=minute, second=second)

        elif pattern.unit == "months":
            # Add months by calculating the target month
            year = base_time.year
            month = base_time.month + pattern.interval

            # Adjust year if needed
            year += (month - 1) // 12
            month = ((month - 1) % 12) + 1

            # Use the specified day of month or current day
            day = pattern.day_of_month or base_time.day

            # Handle month length issues
            while True:
                try:
                    next_time = base_time.replace(
                        year=year,
                        month=month,
                        day=day,
                        hour=hour,
                        minute=minute,
                        second=second,
                    )
                    break
                except ValueError:
                    # If day is invalid (e.g., 31st in a 30-day month), try previous day
                    day -= 1

        # Ensure we don't return a time in the past
        if next_time <= now:
            return self._calculate_next_occurrence(pattern, next_time)

        return next_time

    async def schedule_event(
        self,
        event_id: str,
        event_data: dict,
        trigger_time: Optional[datetime] = None,
        recurring_pattern: Optional[RecurringPattern] = None,
    ) -> bool:
        """Schedule an event with optional trigger_time and recurring pattern."""
        logger.debug(f"Scheduling event: {event_id}")

        if recurring_pattern and trigger_time is None:
            # Calculate the next occurrence based on pattern
            trigger_time = self._calculate_next_occurrence(recurring_pattern)
        elif trigger_time is None:
            raise ValueError("trigger_time is required for non-recurring events")

        # Handle timezone conversion
        if trigger_time.tzinfo is None:
            # If naive datetime, localize it to scheduler timezone
            trigger_time = self.timezone.localize(trigger_time)

        # Calculate TTL in seconds
        now = datetime.now(self.timezone)
        ttl = int((trigger_time - now).total_seconds())
        logger.debug(f"Prompt will be executed in {ttl} seconds")
        if ttl < 0:
            raise ValueError("Cannot schedule events in the past")

        # Create metadata
        metadata: ScheduledEvent = {
            "event_id": event_id,
            "event_data": event_data,
            "scheduled_time": trigger_time.astimezone(self.timezone).isoformat(
                timespec="seconds"
            ),
            "created_at": datetime.now(self.timezone)
            .astimezone(self.timezone)
            .isoformat(timespec="seconds"),
            "recurring_pattern": (
                recurring_pattern.__dict__ if recurring_pattern else None
            ),
        }

        # Store event metadata and set up Redis keys
        metadata_key = f"{self.metadata_prefix}{event_id}"
        event_key = f"event:{event_id}"
        await self.redis_client.set(metadata_key, json.dumps(metadata))
        await self.redis_client.setex(event_key, ttl, json.dumps(event_data))
        await self.redis_client.sadd(self.active_events_set, event_id)

        if recurring_pattern:
            await self.redis_client.sadd(self.recurring_events_set, event_id)

    async def _schedule_next_occurrence(self, event_id: str, metadata: dict):
        """Schedule the next occurrence of a recurring event."""
        try:
            if not metadata.get("recurring_pattern"):
                return

            pattern = RecurringPattern(**metadata["recurring_pattern"])
            last_run = datetime.fromisoformat(metadata["scheduled_time"])
            next_time = self._calculate_next_occurrence(pattern, last_run)

            # Schedule the next occurrence with the same event_id
            await self.schedule_event(
                event_id, metadata["event_data"], next_time, pattern
            )

        except Exception as e:
            logger.error(f"Error scheduling next occurrence: {str(e)}")

    async def update_event(
        self,
        event_id: str,
        new_data: dict = None,
        new_trigger_time: datetime = None,
        new_recurring_pattern: Optional[RecurringPattern] = None,
    ) -> bool:
        """Update an existing event's data, trigger time, and/or recurring pattern."""
        metadata_key = f"{self.metadata_prefix}{event_id}"
        event_key = f"event:{event_id}"

        # Check if event exists
        if not await self.redis_client.exists(metadata_key):
            raise ValueError(f"Event {event_id} does not exist")

        # Get current metadata
        current_metadata: ScheduledEvent = json.loads(
            await self.redis_client.get(metadata_key)
        )

        # Update event data if provided
        if new_data is not None:
            current_metadata["event_data"].update(new_data)

        # Update trigger time if provided
        if new_trigger_time is not None:
            if new_trigger_time.tzinfo is None:
                new_trigger_time = self.timezone.localize(new_trigger_time)
            ttl = int((new_trigger_time - datetime.now(self.timezone)).total_seconds())
            if ttl < 0:
                raise ValueError("Cannot schedule events in the past")

            current_metadata["scheduled_time"] = new_trigger_time.isoformat(
                timespec="seconds"
            )

            # Update expiration
            await self.redis_client.delete(event_key)
            await self.redis_client.setex(
                event_key, ttl, json.dumps(current_metadata["event_data"])
            )

        # Update recurring pattern if provided
        if new_recurring_pattern is not None:
            if new_recurring_pattern:
                # Validate the pattern
                await self.redis_client.sadd(self.recurring_events_set, event_id)
            else:
                await self.redis_client.srem(self.recurring_events_set, event_id)
            current_metadata["recurring_pattern"] = (
                new_recurring_pattern.__dict__ if new_recurring_pattern else None
            )

        # Save updated metadata
        await self.redis_client.set(metadata_key, json.dumps(current_metadata))

    async def delete_event(self, event_id: str) -> bool:
        """Delete a scheduled event."""
        try:
            # Remove all traces of the event
            await self.redis_client.delete(f"event:{event_id}")
            await self.redis_client.delete(f"{self.metadata_prefix}{event_id}")
            await self.redis_client.srem(self.active_events_set, event_id)
            await self.redis_client.srem(self.recurring_events_set, event_id)
            return True

        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            return False

    async def get_event(self, event_id: str) -> Optional[Dict]:
        """Get details of a specific event."""
        try:
            metadata = await self.redis_client.get(f"{self.metadata_prefix}{event_id}")
            if metadata:
                return json.loads(metadata)
            return None
        except Exception as e:
            logger.error(f"Error retrieving event: {str(e)}")
            return None

    async def list_events(
        self, pattern: str = "*", filters: Dict[str, Any] = None
    ) -> List[ScheduledEvent]:
        """
        List all scheduled events with optional filtering.

        Args:
            pattern: str - Filter event IDs by this pattern
            filters: Dict - Filter events by metadata key-value pairs
                    e.g., {"user_id": "123", "event_type": "backup"}
        """
        try:
            events = []
            event_ids = await self.redis_client.smembers(self.active_events_set)

            for event_id in event_ids:
                event_id = event_id.decode("utf-8")
                if pattern != "*" and pattern not in event_id:
                    continue

                metadata = await self.get_event(event_id)
                if metadata:
                    # Apply filters if provided
                    if filters:
                        matches_all_filters = True
                        for key, value in filters.items():
                            # Check both top-level metadata and nested event_data
                            if (
                                key not in metadata
                                and key not in metadata["event_data"]
                            ):
                                matches_all_filters = False
                                break

                            metadata_value = metadata.get(key) or metadata[
                                "event_data"
                            ].get(key)
                            if metadata_value != value:
                                matches_all_filters = False
                                break

                        if not matches_all_filters:
                            continue

                    scheduled_time = datetime.fromisoformat(metadata["scheduled_time"])
                    metadata["time_remaining_seconds"] = (
                        scheduled_time - datetime.now(self.timezone)
                    ).total_seconds()
                    events.append(metadata)

            return events

        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            return []

    async def start(self):
        """Start the scheduler."""
        # Enable keyspace notifications BEFORE creating the pubsub connection
        await self.redis_client.config_set("notify-keyspace-events", "Ex")

        # Start the event listener
        asyncio.create_task(self._listen_for_events())
        logger.debug("Scheduler started successfully")

    async def _listen_for_events(self):
        pubsub = self.redis_client.pubsub()
        # Add timeout to subscription
        await pubsub.psubscribe(f"__keyevent@{self.db}__:expired")
        """Listen for expired events."""
        async for message in pubsub.listen():
            if message["type"] == "pmessage":
                expired_key = message["data"].decode("utf-8")
                if expired_key.startswith("event:"):
                    await self._handle_expired_event(expired_key)

    async def _handle_expired_event(self, event_key: str):
        """Handle an expired (triggered) event."""
        event_id = event_key.split(":")[1]
        logger.debug(f"Event Expired: {event_id}")
        # Get event metadata before cleanup
        event = await self.get_event(event_id)

        if event:
            logger.debug(f"Event triggered: {event_id}")
            # Handle recurring events
            if event.get("recurring_pattern"):
                await self._schedule_next_occurrence(event_id, event)
            else:
                # Clean up non-recurring event
                await self.delete_event(event_id)
            if not callable(self.on_event):
                raise ValueError("on_event is not a callable")
            try:
                if asyncio.iscoroutinefunction(self.on_event):
                    await self.on_event(event_id, event["event_data"])
                else:
                    self.on_event(event_id, event["event_data"])
            except Exception as e:
                logger.error(f"Error handling event: {str(e)}", exc_info=True)


# Usage example
async def main():
    logging.basicConfig(level=logging.DEBUG)
    # Initialize scheduler with your timezone
    scheduler = AsyncRedisEventScheduler(timezone="America/Los_Angeles")

    scheduler.on_event = lambda event_id, metadata: logger.warning(
        f"Triggered event: {event_id}"
    )

    # Start the scheduler
    await scheduler.start()

    # Schedule event once
    await scheduler.schedule_event(
        "remind_user",
        {"action": "remind", "target": "user"},
        datetime.now() + timedelta(seconds=10),
        recurring_pattern=None,
    )

    # Schedule event every 30 seconds
    await scheduler.schedule_event(
        "health_check",
        {"action": "check_status", "target": "api"},
        datetime.now() + timedelta(seconds=5),  # First occurrence in 5 seconds
        recurring_pattern=RecurringPattern(interval=30, unit="seconds"),
    )

    # Schedule daily event with precise time including seconds
    await scheduler.schedule_event(
        "daily_backup",
        {"action": "backup", "target": "database"},
        recurring_pattern=RecurringPattern(
            interval=1, unit="days", time_of_day="08:00:30"  # Daily at 8:00:30 AM
        ),
    )

    # List all events
    events = await scheduler.list_events()
    for event in events:
        logger.info(f"Event: {event['event_id']}")
        logger.info(f"Scheduled: {event['scheduled_time']}")
        logger.info(f"Recurring: {event['recurring_pattern']}")

    # Keep the script running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
