import redis.asyncio as redis
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal, Any
from dataclasses import dataclass
import pytz
import logging
from abc import ABC, abstractmethod

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


class AsyncRedisEventScheduler(ABC):

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 2,
        password: str = None,
    ):
        """Initialize the scheduler with UTC timezone for internal storage."""
        self.db = db
        self.redis_client = redis.Redis(host=host, port=port, db=db, password=password)
        self.timezone = pytz.timezone("UTC")  # Always use UTC internally

        # Keys for storing event metadata
        self.metadata_prefix = "event_metadata:"
        self.active_events_set = "active_events"
        self.recurring_events_set = "recurring_events"

    @abstractmethod
    def on_event(
        self,
        event_id: str,
        event_data: Dict[str, Any],
    ) -> None:
        """Event handler for triggered events."""
        raise NotImplementedError("on_event must be implemented")

    def _calculate_next_occurrence(
        self, pattern: RecurringPattern, last_run: Optional[datetime] = None
    ) -> datetime:
        """Calculate the next occurrence based on the recurring pattern."""
        now = datetime.now(self.timezone)
        # Ensure last_run is in UTC
        if last_run and last_run.tzinfo is None:
            last_run = self.timezone.localize(last_run)
        elif last_run and last_run.tzinfo != self.timezone:
            last_run = last_run.astimezone(self.timezone)

        base_time = last_run if last_run else now

        # Parse time_of_day if provided (interpreted as UTC time)
        if pattern.time_of_day:
            # Support both HH:MM:SS and HH:MM formats
            time_parts = pattern.time_of_day.split(":")
            if len(time_parts) == 3:
                hour, minute, second = map(int, time_parts)
            elif len(time_parts) == 2:
                hour, minute = map(int, time_parts)
                second = 0
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
            # Always work in UTC
            today = now.replace(hour=hour, minute=minute, second=second, microsecond=0)

            if today <= now:
                # If specified time has already passed today, start from tomorrow
                next_time = (now + timedelta(days=1)).replace(
                    hour=hour, minute=minute, second=second, microsecond=0
                )
                # Then add any additional interval days
                if pattern.interval > 1:
                    next_time += timedelta(days=pattern.interval - 1)
            else:
                # If time hasn't passed today, this is our next occurrence
                next_time = today

            logger.debug(
                f"Calculated next daily occurrence: {next_time.isoformat()} UTC "
                f"(time_of_day={pattern.time_of_day}, interval={pattern.interval})"
            )

        elif pattern.unit == "weeks":
            if pattern.day_of_week is not None:
                current_dow = base_time.weekday()
                days_ahead = pattern.day_of_week - current_dow

                if days_ahead <= 0:
                    # If target day is today or already passed this week,
                    # move to next week
                    days_ahead += 7

                # Calculate the next occurrence
                next_time = (base_time + timedelta(days=days_ahead)).replace(
                    hour=hour, minute=minute, second=second
                )

                # If the calculated time has passed, add interval weeks
                if next_time <= now:
                    next_time += timedelta(weeks=pattern.interval)

        elif pattern.unit == "months":
            # Try current month first
            current_day = pattern.day_of_month or base_time.day
            year = base_time.year
            month = base_time.month

            # First try to create a date for the target day in current month
            try:
                candidate_time = base_time.replace(
                    day=current_day, hour=hour, minute=minute, second=second
                )

                if candidate_time <= now:
                    # Move to next interval if time has passed
                    month += pattern.interval
                    # Adjust year if needed
                    year += (month - 1) // 12
                    month = ((month - 1) % 12) + 1

                    # Try to create the date for next month
                    while True:
                        try:
                            next_time = base_time.replace(
                                year=year,
                                month=month,
                                day=current_day,
                                hour=hour,
                                minute=minute,
                                second=second,
                            )
                            break
                        except ValueError:
                            # If day is invalid (e.g., 31st in a 30-day month), try previous day
                            current_day -= 1
                else:
                    next_time = candidate_time

            except ValueError:
                # Handle invalid dates (e.g., Feb 31)
                current_day -= 1
                next_time = self._calculate_next_occurrence(pattern, base_time)

        # Final check to ensure we never return a time less than 30 seconds in the future
        # otherwise the system might not be able to schedule the event
        min_future_time = now + timedelta(seconds=30)
        if next_time < min_future_time:
            if pattern.unit in ["seconds", "minutes", "hours"]:
                next_time = now + timedelta(**{pattern.unit: pattern.interval})
            else:
                # For longer intervals, try calculating from the next day
                next_time = self._calculate_next_occurrence(
                    pattern, now + timedelta(days=1)
                )

            # Additional check to enforce minimum future time
            if next_time < min_future_time:
                logger.warning(
                    f"Next occurrence time {next_time} is less than 30 seconds in the future. Adjusting to now + 30 seconds."
                )
                next_time = min_future_time

        return next_time

    async def schedule_event(
        self,
        event_id: str,
        event_data: dict,
        trigger_time: Optional[datetime] = None,
        recurring_pattern: Optional[RecurringPattern] = None,
    ):
        """Schedule an event with optional trigger_time and recurring pattern."""
        logger.debug(f"Scheduling event {event_id}")

        if recurring_pattern and trigger_time is None:
            # Calculate the next occurrence based on pattern
            trigger_time = self._calculate_next_occurrence(recurring_pattern)
        elif trigger_time is None:
            raise ValueError("trigger_time is required for non-recurring events")

        # Handle timezone conversion - ensure UTC
        if trigger_time.tzinfo is None:
            # No timezone info - treat as UTC
            logger.debug("Interpreting naive datetime as UTC")
            trigger_time = pytz.UTC.localize(trigger_time)
        elif trigger_time.tzinfo != pytz.UTC:
            # Convert other timezones to UTC
            logger.debug(f"Converting time from {trigger_time.tzinfo} to UTC")
            trigger_time = trigger_time.astimezone(pytz.UTC)

        # Calculate TTL in seconds using UTC time
        now = datetime.now(pytz.UTC)
        ttl = int((trigger_time - now).total_seconds())
        logger.debug(
            f"Event will be executed in {ttl} seconds (trigger_time={trigger_time.isoformat()})"
        )
        if ttl <= 0:
            raise ValueError("Cannot schedule events in the past")

        # Create metadata - store everything in UTC
        metadata: ScheduledEvent = {
            "event_id": event_id,
            "event_data": event_data,
            "scheduled_time": trigger_time.isoformat(timespec="seconds"),
            "created_at": datetime.now(self.timezone).isoformat(timespec="seconds"),
            "recurring_pattern": (
                recurring_pattern.__dict__ if recurring_pattern else None
            ),
        }

        try:
            # Store event metadata and set up Redis keys
            metadata_key = f"{self.metadata_prefix}{event_id}"
            event_key = f"event:{event_id}"
            await self.redis_client.set(metadata_key, json.dumps(metadata))
            await self.redis_client.setex(event_key, ttl, json.dumps(event_data))
            await self.redis_client.sadd(self.active_events_set, event_id)

            if recurring_pattern:
                await self.redis_client.sadd(self.recurring_events_set, event_id)

        except redis.RedisError as e:
            logger.error(f"Redis error while scheduling event: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error scheduling event: {str(e)}")
            raise

    async def _schedule_next_occurrence(self, event_id: str, metadata: dict):
        """Schedule the next occurrence of a recurring event."""
        if not metadata.get("recurring_pattern"):
            return

        pattern = RecurringPattern(**metadata["recurring_pattern"])
        last_run = datetime.fromisoformat(metadata["scheduled_time"])
        next_time = self._calculate_next_occurrence(pattern, last_run)

        # Schedule the next occurrence with the same event_id
        await self.schedule_event(event_id, metadata["event_data"], next_time, pattern)

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

        async with self.redis_client.pipeline() as pipe:
            # Watch the keys we're going to modify
            await pipe.watch(metadata_key, event_key)

            # Check if event exists
            if not await pipe.exists(metadata_key):
                raise ValueError(f"Event {event_id} does not exist")

            # Get current metadata
            current_metadata = json.loads(await pipe.get(metadata_key))

            pipe.multi()  # Start transaction

            # Update logic here...
            if new_data is not None:
                current_metadata["event_data"].update(new_data)

            # Handle recurring pattern update
            if new_recurring_pattern is not None:
                if new_recurring_pattern:
                    await pipe.sadd(self.recurring_events_set, event_id)
                    # Recalculate next occurrence based on new pattern
                    next_time = self._calculate_next_occurrence(new_recurring_pattern)
                    current_metadata["scheduled_time"] = next_time.isoformat(
                        timespec="seconds"
                    )
                    new_trigger_time = next_time

                else:
                    await pipe.srem(self.recurring_events_set, event_id)
                current_metadata["recurring_pattern"] = (
                    new_recurring_pattern.__dict__ if new_recurring_pattern else None
                )

            # Update trigger time if provided or if it was recalculated from pattern
            if new_trigger_time is not None:
                # Handle timezone conversion - ensure UTC
                if new_trigger_time.tzinfo is None:
                    # No timezone info - treat as UTC
                    logger.debug("Interpreting naive datetime as UTC")
                    new_trigger_time = pytz.UTC.localize(new_trigger_time)
                elif new_trigger_time.tzinfo != pytz.UTC:
                    # Convert other timezones to UTC
                    logger.debug(
                        f"Converting time from {new_trigger_time.tzinfo} to UTC"
                    )
                    new_trigger_time = new_trigger_time.astimezone(pytz.UTC)

                ttl = int((new_trigger_time - datetime.now(pytz.UTC)).total_seconds())
                logger.debug(
                    f"Updated trigger time to {new_trigger_time.isoformat()} UTC"
                )
                if ttl < 0:
                    raise ValueError("Cannot schedule events in the past")

                current_metadata["scheduled_time"] = new_trigger_time.isoformat(
                    timespec="seconds"
                )

                # Update expiration
                await pipe.delete(event_key)
                await pipe.setex(
                    event_key, ttl, json.dumps(current_metadata["event_data"])
                )
            elif current_metadata.get("recurring_pattern"):
                # Recalculate next occurrence for existing recurring pattern
                pattern = RecurringPattern(**current_metadata["recurring_pattern"])
                next_time = self._calculate_next_occurrence(pattern)
                current_metadata["scheduled_time"] = next_time.isoformat(
                    timespec="seconds"
                )

                ttl = int((next_time - datetime.now(self.timezone)).total_seconds())
                await pipe.delete(event_key)
                await pipe.setex(
                    event_key, ttl, json.dumps(current_metadata["event_data"])
                )

            # Save updated metadata
            await pipe.set(metadata_key, json.dumps(current_metadata))

            await pipe.execute()

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
        """Get details of a specific event. All times are in UTC."""
        try:
            metadata = await self.redis_client.get(f"{self.metadata_prefix}{event_id}")
            if metadata:
                event_data = json.loads(metadata)
                # Times are already in UTC, return as-is
                return event_data
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
                    event_key = f"event:{event_id}"
                    metadata["time_remaining_seconds"] = await self.redis_client.ttl(
                        event_key
                    )
                    events.append(metadata)

            return events

        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            return []

    async def start(self):
        """Start the scheduler."""
        try:
            # Enable keyspace notifications BEFORE creating the pubsub connection
            await self.redis_client.config_set("notify-keyspace-events", "Ex")

            # Start the event listener
            self._listener_task = asyncio.create_task(self._listen_for_events())
            logger.debug("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise

    async def stop(self):
        """Stop the scheduler and cleanup resources."""
        if hasattr(self, "_listener_task"):
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        await self.redis_client.close()

    async def _listen_for_events(self):
        try:
            pubsub = self.redis_client.pubsub()
            await pubsub.psubscribe(f"__keyevent@{self.db}__:expired")

            async for message in pubsub.listen():
                if message["type"] == "pmessage":
                    expired_key = message["data"].decode("utf-8")
                    if expired_key.startswith("event:"):
                        await self._handle_expired_event(expired_key)
        finally:
            await pubsub.close()

    async def _handle_expired_event(self, event_key: str):
        """Handle an expired (triggered) event."""
        event_id = event_key.split(":")[1]
        try:
            logger.debug(
                f"Event {event_id} expired at {datetime.now(self.timezone).isoformat()} UTC"
            )
            event = await self.get_event(event_id)
            if not event:
                logger.warning(f"Event {event_id} not found")
                return

            if not self.on_event:
                logger.error("No event handler configured")
                return

            if not callable(self.on_event):
                raise ValueError("on_event is not a callable")

            try:
                if asyncio.iscoroutinefunction(self.on_event):
                    await self.on_event(event_id, event["event_data"])
                else:
                    self.on_event(event_id, event["event_data"])
            except Exception as e:
                logger.error(f"Error in event handler: {str(e)}", exc_info=True)

        except Exception as e:
            logger.error(f"Error handling expired event: {str(e)}", exc_info=True)
        finally:
            try:
                if event and event.get("recurring_pattern"):
                    await self._schedule_next_occurrence(event_id, event)
                else:
                    await self.delete_event(event_id)
            except Exception as e:
                logger.error(f"Error in event cleanup: {str(e)}", exc_info=True)


# Usage example
async def main():
    logging.basicConfig(level=logging.DEBUG)
    scheduler = AsyncRedisEventScheduler()  # No timezone needed, uses UTC internally

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
        logger.info(f"Scheduled: {event['scheduled_time']} UTC")
        logger.info(f"Recurring: {event['recurring_pattern']}")

    # Keep the script running
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
