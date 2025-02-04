import asyncio
import calendar
import json
import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal, TypedDict

import pytz
import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff

logger = logging.getLogger(__name__)

# Constants for Redis operations
REDIS_RETRY_ATTEMPTS = 3
REDIS_RETRY_DELAY = 0.1  # seconds
REDIS_OPERATION_TIMEOUT = 5.0  # seconds

# Time constants
MIN_FUTURE_SECONDS = 30
PROCESSING_LOCK_TIMEOUT = 300  # 5 minutes
RECONCILIATION_INTERVAL = 60  # seconds

# Time format constants
TIME_PARTS_FULL = 3  # HH:MM:SS
TIME_PARTS_SHORT = 2  # HH:MM

# Calendar constants
MAX_WEEKDAY = 6  # 0-6 for weekly (0 is Monday)
MAX_MONTHDAY = 31  # 1-31 for monthly

# Time validation constants
MAX_HOUR = 23  # 0-23 hours
MAX_MINUTE = 59  # 0-59 minutes
MAX_SECOND = 59  # 0-59 seconds


@dataclass
class TimeComponents:
    """Time components for scheduling."""

    hour: int
    minute: int
    second: int = 0


@dataclass
class RecurringPattern:
    """Defines a recurring schedule pattern"""

    interval: int
    unit: Literal["seconds", "minutes", "hours", "days", "weeks", "months"]
    time_of_day: str | None = None  # HH:MM:SS or HH:MM format for daily/weekly/monthly
    day_of_week: int | None = (
        None  # 0-6 for weekly (0 is Monday, matches calendar.MONDAY etc)
    )
    day_of_month: int | None = None  # 1-31 for monthly

    def __post_init__(self) -> None:
        """Validate pattern parameters after initialization."""
        if self.interval < 1:
            raise ValueError("Interval must be positive")

        if (
            self.unit == "weeks"
            and self.day_of_week is not None
            and not 0 <= self.day_of_week <= MAX_WEEKDAY
        ):
            raise ValueError("day_of_week must be between 0 and 6")

        if (
            self.unit == "months"
            and self.day_of_month is not None
            and not 1 <= self.day_of_month <= MAX_MONTHDAY
        ):
            raise ValueError("day_of_month must be between 1 and 31")

        if self.time_of_day is not None:
            # This will raise ValueError if format is invalid
            parse_time_of_day(self.time_of_day)


class ScheduledEvent(TypedDict):
    event_id: str
    event_data: dict[str, Any]
    scheduled_time: str
    created_at: str
    recurring_pattern: dict[str, Any] | None
    time_remaining_seconds: int


def parse_time_of_day(time_str: str) -> TimeComponents:
    """Parse time string in HH:MM:SS or HH:MM format."""
    time_parts = time_str.split(":")
    try:
        if len(time_parts) == TIME_PARTS_FULL:
            hour, minute, second = map(int, time_parts)
            if not (
                0 <= hour <= MAX_HOUR
                and 0 <= minute <= MAX_MINUTE
                and 0 <= second <= MAX_SECOND
            ):
                raise ValueError
            return TimeComponents(hour, minute, second)
        if len(time_parts) == TIME_PARTS_SHORT:
            hour, minute = map(int, time_parts)
            if not (0 <= hour <= MAX_HOUR and 0 <= minute <= MAX_MINUTE):
                raise ValueError
            return TimeComponents(hour, minute)
        raise ValueError
    except (ValueError, TypeError) as err:
        raise ValueError("time_of_day must be in HH:MM:SS or HH:MM format") from err


class AbstractAsyncRedisEventScheduler(ABC):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 2,
        password: str | None = None,
    ) -> None:
        """Initialize the scheduler with UTC timezone and Redis connection pool."""
        self.db = db
        self.timezone = pytz.UTC  # Always use UTC internally

        # Redis connection configuration with retries
        retry = Retry(ExponentialBackoff(cap=REDIS_RETRY_DELAY), REDIS_RETRY_ATTEMPTS)
        self.redis_pool = redis.ConnectionPool(
            host=host,
            port=port,
            db=db,
            password=password,
            retry=retry,
            decode_responses=True,
        )

        # Keys for storing event metadata
        self.metadata_prefix = "event_metadata:"
        self.active_events_set = "active_events"
        self.recurring_events_set = "recurring_events"
        self.processing_events_set = "processing_events"  # Track events being processed

        # Internal state
        self._running = False
        self._listener_task = None
        self._reconciliation_task = None

    @abstractmethod
    async def on_event(
        self,
        event_id: str,
        event_data: dict[str, Any],
    ) -> None:
        """Event handler for triggered events."""
        raise NotImplementedError("on_event must be implemented")

    @asynccontextmanager
    async def redis_client(self) -> AsyncGenerator[redis.Redis, None]:
        """Get a Redis client from the connection pool with automatic cleanup."""
        client = redis.Redis(connection_pool=self.redis_pool)
        try:
            yield client
        finally:
            await client.close()

    async def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Get details of a specific event. All times are in UTC."""
        try:
            async with self.redis_client() as client:
                metadata = await client.get(f"{self.metadata_prefix}{event_id}")
                if metadata:
                    return json.loads(metadata)
                return None
        except Exception as e:
            logger.error(f"Error retrieving event: {str(e)}")
            return None

    async def delete_event(self, event_id: str) -> bool:
        """Delete a scheduled event."""
        try:
            async with self.redis_client() as client:
                async with client.pipeline() as pipe:
                    await pipe.delete(f"event:{event_id}")
                    await pipe.delete(f"{self.metadata_prefix}{event_id}")
                    await pipe.srem(self.active_events_set, event_id)
                    await pipe.srem(self.recurring_events_set, event_id)
                    await pipe.execute()
                return True
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            return False

    def _matches_filters(self, event: dict[str, Any], filters: dict[str, Any]) -> bool:
        """Check if an event matches the given filters."""
        for key, value in filters.items():
            # Handle nested keys in event_data
            if key in event.get("event_data", {}):
                if event["event_data"][key] != value:
                    return False
            elif key in event:
                if event[key] != value:
                    return False
            else:
                return False
        return True

    async def list_events(
        self, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """List all scheduled events matching the filters.

        Args:
            filters: Dictionary of filters to apply to event metadata
                    (e.g., {"user_id": "123"})

        Returns:
            List of event metadata dictionaries
        """
        try:
            async with self.redis_client() as client:
                # Get all active event IDs
                event_ids = await client.smembers(self.active_events_set)
                if not event_ids:
                    return []

                # Get metadata for all events
                metadata_keys = [
                    f"{self.metadata_prefix}{event_id}" for event_id in event_ids
                ]
                metadata_values = await client.mget(metadata_keys)

                # Parse metadata and apply filters
                events = []
                for metadata_str in metadata_values:
                    if not metadata_str:
                        continue

                    try:
                        event = json.loads(metadata_str)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse event metadata: {str(e)}")
                        continue

                    # Apply filters if provided
                    if filters and not self._matches_filters(event, filters):
                        continue

                    events.append(event)

                return events

        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            return []

    async def schedule_event(
        self,
        event_id: str,
        event_data: dict[str, Any],
        trigger_time: datetime | None = None,
        recurring_pattern: RecurringPattern | None = None,
    ) -> None:
        """Schedule an event with optional trigger_time and recurring pattern."""
        logger.debug(f"Scheduling event {event_id}")

        if recurring_pattern and trigger_time is None:
            trigger_time = self._calculate_next_occurrence(recurring_pattern)
        elif trigger_time is None:
            raise ValueError("trigger_time is required for non-recurring events")

        # Handle timezone conversion - ensure UTC
        if trigger_time.tzinfo is None:
            trigger_time = self.timezone.localize(trigger_time)
        elif trigger_time.tzinfo != self.timezone:
            trigger_time = trigger_time.astimezone(self.timezone)

        # Calculate TTL in seconds using UTC time
        now = datetime.now(self.timezone)
        time_diff = trigger_time - now
        ttl = int(time_diff.total_seconds())

        # Log scheduling details
        logger.debug(
            f"Event will be executed in {ttl} seconds "
            f"(trigger_time={trigger_time.isoformat()}, now={now.isoformat()})"
        )

        if ttl <= 0:
            msg = (
                "Cannot schedule events in the past: "
                f"trigger_time={trigger_time.isoformat()}, "
                f"now={now.isoformat()}, "
                f"diff={time_diff}"
            )
            logger.error(msg)
            raise ValueError("Cannot schedule events in the past")

        try:
            metadata: ScheduledEvent = {
                "event_id": event_id,
                "event_data": event_data,
                "scheduled_time": trigger_time.isoformat(timespec="seconds"),
                "created_at": now.isoformat(timespec="seconds"),
                "recurring_pattern": (
                    recurring_pattern.__dict__ if recurring_pattern else None
                ),
                "time_remaining_seconds": ttl,
            }

            async with self.redis_client() as client:
                metadata_key = f"{self.metadata_prefix}{event_id}"
                event_key = f"event:{event_id}"

                async with client.pipeline() as pipe:
                    await pipe.set(metadata_key, json.dumps(metadata))
                    await pipe.setex(event_key, ttl, json.dumps(event_data))
                    await pipe.sadd(self.active_events_set, event_id)
                    if recurring_pattern:
                        await pipe.sadd(self.recurring_events_set, event_id)
                    await pipe.execute()

        except redis.RedisError as e:
            logger.error(f"Redis error while scheduling event: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error scheduling event: {str(e)}")
            raise

    async def start(self) -> None:
        """Start the scheduler and background tasks."""
        if self._running:
            return

        try:
            async with self.redis_client() as client:
                await client.config_set("notify-keyspace-events", "KEx")
                self._running = True
                self._listener_task = asyncio.create_task(self._listen_for_events())
                self._reconciliation_task = asyncio.create_task(
                    self._reconcile_events()
                )
                logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {str(e)}")
            raise

    async def stop(self) -> None:
        """Stop the scheduler and cleanup resources."""
        self._running = False

        tasks = []
        if self._listener_task:
            self._listener_task.cancel()
            tasks.append(self._listener_task)

        if self._reconciliation_task:
            self._reconciliation_task.cancel()
            tasks.append(self._reconciliation_task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Clear connection pool
        await self.redis_pool.disconnect()

    async def _listen_for_events(self) -> None:
        """Listen for Redis keyspace events with automatic reconnection."""
        while self._running:
            try:
                async with self.redis_client() as client:
                    pubsub = client.pubsub()
                    await pubsub.psubscribe(f"__keyevent@{self.db}__:expired")

                    async for message in pubsub.listen():
                        if not self._running:
                            break

                        if message["type"] == "pmessage":
                            expired_key = message["data"]
                            if expired_key.startswith("event:"):
                                event_id = expired_key.split(":", 1)[1]
                                asyncio.create_task(
                                    self._process_expired_event(event_id)
                                )

            except Exception as e:
                if self._running:
                    logger.error(f"Event listener error: {str(e)}")
                    await asyncio.sleep(1)  # Prevent rapid reconnection attempts

    async def _process_expired_event(self, event_id: str) -> None:
        """Process an expired event with proper locking and error handling."""
        async with self.redis_client() as client:
            # Add expiration to processing lock
            lock_key = f"{self.processing_events_set}:{event_id}"
            if not await client.set(lock_key, "1", ex=PROCESSING_LOCK_TIMEOUT, nx=True):
                logger.warning(f"Event {event_id} is already being processed")
                return

            try:
                now = datetime.now(self.timezone)
                logger.debug(f"Processing event {event_id} at {now.isoformat()} UTC")

                event = await self.get_event(event_id)
                if not event:
                    logger.warning(f"Event {event_id} not found")
                    return

                try:
                    await self.on_event(event_id, event["event_data"])
                except Exception as e:
                    logger.error(f"Error in event handler: {str(e)}", exc_info=True)
                    return

                if event.get("recurring_pattern"):
                    await self._schedule_next_occurrence(event_id, event)
                else:
                    await self.delete_event(event_id)

            except Exception as e:
                logger.error(
                    f"Error processing event {event_id}: {str(e)}", exc_info=True
                )
            finally:
                await client.delete(lock_key)

    async def _schedule_next_occurrence(
        self, event_id: str, metadata: dict[str, Any]
    ) -> None:
        """Schedule the next occurrence of a recurring event."""
        if not metadata.get("recurring_pattern"):
            return

        pattern = RecurringPattern(**metadata["recurring_pattern"])
        last_run = datetime.fromisoformat(metadata["scheduled_time"])
        next_time = self._calculate_next_occurrence(pattern, last_run)

        try:
            # Schedule new occurrence first, then clean up old one atomically
            async with self.redis_client() as client, client.pipeline() as pipe:
                # Schedule new occurrence
                metadata_key = f"{self.metadata_prefix}{event_id}"
                event_key = f"event:{event_id}"

                now = datetime.now(self.timezone)
                new_metadata = {
                    "event_id": event_id,
                    "event_data": metadata["event_data"],
                    "scheduled_time": next_time.isoformat(timespec="seconds"),
                    "created_at": now.isoformat(timespec="seconds"),
                    "recurring_pattern": metadata["recurring_pattern"],
                    "time_remaining_seconds": int((next_time - now).total_seconds()),
                }

                # Set new event data
                await pipe.set(metadata_key, json.dumps(new_metadata))
                await pipe.setex(
                    event_key,
                    new_metadata["time_remaining_seconds"],
                    json.dumps(metadata["event_data"]),
                )
                await pipe.sadd(self.active_events_set, event_id)
                await pipe.sadd(self.recurring_events_set, event_id)

                # Execute transaction
                await pipe.execute()

                logger.debug(
                    f"Scheduled next occurrence of event {event_id} "
                    f"at {next_time.isoformat()}"
                )
        except Exception as e:
            logger.error(
                f"Failed to schedule next occurrence of event {event_id}: {str(e)}"
            )
            raise

    async def _reconcile_events(self) -> None:
        """Periodically check for and clean up orphaned events."""
        while self._running:
            try:
                async with self.redis_client() as client:
                    active_events = await client.smembers(self.active_events_set)
                    processing_events = await client.smembers(
                        self.processing_events_set
                    )

                    for event_id in active_events:
                        if event_id in processing_events:
                            continue

                        event_key = f"event:{event_id}"
                        metadata_key = f"{self.metadata_prefix}{event_id}"

                        exists = await asyncio.gather(
                            client.exists(event_key), client.exists(metadata_key)
                        )

                        if not all(exists):
                            logger.warning(f"Found orphaned event: {event_id}")
                            await self.delete_event(event_id)

            except Exception as e:
                logger.error(f"Error in event reconciliation: {str(e)}")

            await asyncio.sleep(RECONCILIATION_INTERVAL)

    def _calculate_next_occurrence(
        self, pattern: RecurringPattern, last_run: datetime | None = None
    ) -> datetime:
        """Calculate the next occurrence based on the recurring pattern."""
        now = datetime.now(self.timezone)

        if last_run and last_run.tzinfo is None:
            last_run = self.timezone.localize(last_run)
        elif last_run and last_run.tzinfo != self.timezone:
            last_run = last_run.astimezone(self.timezone)

        base_time = last_run if last_run else now

        # Extract time components
        time_components = (
            parse_time_of_day(pattern.time_of_day)
            if pattern.time_of_day
            else TimeComponents(base_time.hour, base_time.minute, base_time.second)
        )

        next_time = self._calculate_next_time(pattern, base_time, time_components)

        # Ensure minimum future time
        min_future_time = now + timedelta(seconds=MIN_FUTURE_SECONDS)
        if next_time < min_future_time:
            if pattern.unit in ["seconds", "minutes", "hours"]:
                next_time = now + timedelta(**{pattern.unit: pattern.interval})
            else:
                next_time = self._calculate_next_occurrence(
                    pattern, now + timedelta(days=1)
                )

            if next_time < min_future_time:
                msg = (
                    f"Next occurrence time {next_time} is less than "
                    f"{MIN_FUTURE_SECONDS} seconds in the future. "
                    f"Adjusting to now + {MIN_FUTURE_SECONDS} seconds."
                )
                logger.warning(msg)
                next_time = min_future_time

        return next_time

    def _calculate_next_time(
        self,
        pattern: RecurringPattern,
        base_time: datetime,
        time_components: TimeComponents,
    ) -> datetime:
        """Helper method to calculate next time based on pattern."""
        if pattern.unit == "seconds":
            return base_time + timedelta(seconds=pattern.interval)
        if pattern.unit == "minutes":
            return base_time + timedelta(minutes=pattern.interval)
        if pattern.unit == "hours":
            return base_time + timedelta(hours=pattern.interval)
        if pattern.unit == "days":
            return self._calculate_daily_next_time(pattern, time_components, base_time)
        if pattern.unit == "weeks" and pattern.day_of_week is not None:
            return self._calculate_weekly_next_time(pattern, base_time, time_components)
        if pattern.unit == "months":
            return self._calculate_monthly_next_time(
                pattern, base_time, time_components
            )
        raise ValueError(f"Invalid pattern unit: {pattern.unit}")

    def _calculate_daily_next_time(
        self,
        pattern: RecurringPattern,
        time_components: TimeComponents,
        now: datetime,
    ) -> datetime:
        """Calculate next time for daily pattern."""
        today = now.replace(
            hour=time_components.hour,
            minute=time_components.minute,
            second=time_components.second,
            microsecond=0,
        )
        if today <= now:
            next_time = (now + timedelta(days=1)).replace(
                hour=time_components.hour,
                minute=time_components.minute,
                second=time_components.second,
                microsecond=0,
            )
            if pattern.interval > 1:
                next_time += timedelta(days=pattern.interval - 1)
            return next_time
        return today

    def _calculate_weekly_next_time(
        self,
        pattern: RecurringPattern,
        base_time: datetime,
        time_components: TimeComponents,
    ) -> datetime:
        """Calculate next time for weekly pattern."""
        current_dow = calendar.weekday(base_time.year, base_time.month, base_time.day)
        target_dow = (
            pattern.day_of_week if pattern.day_of_week is not None else current_dow
        )

        # Calculate days until next occurrence
        days_ahead = target_dow - current_dow
        if days_ahead <= 0:  # Target day has passed this week
            days_ahead += 7 * pattern.interval
        elif (
            pattern.interval > 1
        ):  # Target day hasn't passed, but need to account for interval
            days_ahead += 7 * (pattern.interval - 1)

        next_time = (base_time + timedelta(days=days_ahead)).replace(
            hour=time_components.hour,
            minute=time_components.minute,
            second=time_components.second,
            microsecond=0,
        )

        # If we've calculated a time in the past, move forward by interval weeks
        if next_time <= datetime.now(self.timezone):
            next_time += timedelta(weeks=pattern.interval)

        return next_time

    def _calculate_monthly_next_time(
        self,
        pattern: RecurringPattern,
        base_time: datetime,
        time_components: TimeComponents,
    ) -> datetime:
        """Calculate next time for monthly pattern."""
        current_day = pattern.day_of_month or base_time.day
        year = base_time.year
        month = base_time.month
        now = datetime.now(self.timezone)

        # Get valid day for current month
        _, days_in_month = calendar.monthrange(year, month)
        valid_day = min(current_day, days_in_month)

        # Try current month first
        candidate_time = base_time.replace(
            day=valid_day,
            hour=time_components.hour,
            minute=time_components.minute,
            second=time_components.second,
            microsecond=0,
        )

        # If time has passed, calculate next month
        if candidate_time <= now:
            month += pattern.interval
            year += (month - 1) // 12
            month = ((month - 1) % 12) + 1

            # Get valid day for target month
            _, days_in_month = calendar.monthrange(year, month)
            valid_day = min(current_day, days_in_month)

            return base_time.replace(
                year=year,
                month=month,
                day=valid_day,
                hour=time_components.hour,
                minute=time_components.minute,
                second=time_components.second,
                microsecond=0,
            )

        return candidate_time
