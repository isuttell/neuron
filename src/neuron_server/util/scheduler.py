import redis.asyncio as redis
from redis.asyncio.retry import Retry
from redis.backoff import ExponentialBackoff
import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Literal, Any, Set, TypedDict
from dataclasses import dataclass
import pytz
import logging
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Constants for Redis operations
REDIS_RETRY_ATTEMPTS = 3
REDIS_RETRY_DELAY = 0.1  # seconds
REDIS_OPERATION_TIMEOUT = 5.0  # seconds


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


class ScheduledEvent(TypedDict):
    event_id: str
    event_data: Dict[str, Any]
    scheduled_time: str
    created_at: str
    recurring_pattern: Optional[Dict[str, Any]]
    time_remaining_seconds: int


class AsyncRedisEventScheduler(ABC):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 2,
        password: str = None,
    ):
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
        event_data: Dict[str, Any],
    ) -> None:
        """Event handler for triggered events."""
        raise NotImplementedError("on_event must be implemented")

    @asynccontextmanager
    async def redis_client(self):
        """Get a Redis client from the connection pool with automatic cleanup."""
        client = redis.Redis(connection_pool=self.redis_pool)
        try:
            yield client
        finally:
            await client.close()

    async def get_event(self, event_id: str) -> Optional[Dict]:
        """Get details of a specific event. All times are in UTC."""
        try:
            async with self.redis_client() as client:
                metadata = await client.get(f"{self.metadata_prefix}{event_id}")
                if metadata:
                    event_data = json.loads(metadata)
                    return event_data
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

    async def list_events(
        self, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List all scheduled events matching the filters.

        Args:
            filters: Dictionary of filters to apply to event metadata (e.g., {"user_id": "123"})

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
                    if filters:
                        matches = True
                        for key, value in filters.items():
                            # Handle nested keys in event_data
                            if key in event.get("event_data", {}):
                                if event["event_data"][key] != value:
                                    matches = False
                                    break
                            elif key in event:
                                if event[key] != value:
                                    matches = False
                                    break
                            else:
                                matches = False
                                break

                        if not matches:
                            continue

                    events.append(event)

                return events

        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            return []

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
        logger.debug(
            f"Event will be executed in {ttl} seconds (trigger_time={trigger_time.isoformat()}, now={now.isoformat()})"
        )
        if ttl <= 0:
            logger.error(
                f"Cannot schedule events in the past: trigger_time={trigger_time.isoformat()}, now={now.isoformat()}, diff={time_diff}"
            )
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

    async def start(self):
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

    async def stop(self):
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

    async def _listen_for_events(self):
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

    async def _process_expired_event(self, event_id: str):
        """Process an expired event with proper locking and error handling."""
        async with self.redis_client() as client:
            # Add expiration to processing lock
            lock_key = f"{self.processing_events_set}:{event_id}"
            if not await client.set(lock_key, "1", ex=300, nx=True):  # 5 min timeout
                logger.warning(f"Event {event_id} is already being processed")
                return

            try:
                logger.debug(
                    f"Processing event {event_id} at {datetime.now(self.timezone).isoformat()} UTC"
                )

                event = await self.get_event(event_id)
                if not event:
                    logger.warning(f"Event {event_id} not found")
                    return

                try:
                    if asyncio.iscoroutinefunction(self.on_event):
                        await self.on_event(event_id, event["event_data"])
                    else:
                        self.on_event(event_id, event["event_data"])
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

    async def _schedule_next_occurrence(self, event_id: str, metadata: dict):
        """Schedule the next occurrence of a recurring event."""
        if not metadata.get("recurring_pattern"):
            return

        pattern = RecurringPattern(**metadata["recurring_pattern"])
        last_run = datetime.fromisoformat(metadata["scheduled_time"])
        next_time = self._calculate_next_occurrence(pattern, last_run)

        try:
            # Schedule new occurrence first, then clean up old one atomically
            async with self.redis_client() as client:
                async with client.pipeline() as pipe:
                    # Schedule new occurrence
                    metadata_key = f"{self.metadata_prefix}{event_id}"
                    event_key = f"event:{event_id}"

                    new_metadata = {
                        "event_id": event_id,
                        "event_data": metadata["event_data"],
                        "scheduled_time": next_time.isoformat(timespec="seconds"),
                        "created_at": datetime.now(self.timezone).isoformat(
                            timespec="seconds"
                        ),
                        "recurring_pattern": metadata["recurring_pattern"],
                        "time_remaining_seconds": int(
                            (next_time - datetime.now(self.timezone)).total_seconds()
                        ),
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
                        f"Scheduled next occurrence of event {event_id} at {next_time.isoformat()}"
                    )
        except Exception as e:
            logger.error(
                f"Failed to schedule next occurrence of event {event_id}: {str(e)}"
            )
            raise

    async def _reconcile_events(self):
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

            await asyncio.sleep(60)

    def _calculate_next_occurrence(
        self, pattern: RecurringPattern, last_run: Optional[datetime] = None
    ) -> datetime:
        """Calculate the next occurrence based on the recurring pattern."""
        now = datetime.now(self.timezone)

        if last_run and last_run.tzinfo is None:
            last_run = self.timezone.localize(last_run)
        elif last_run and last_run.tzinfo != self.timezone:
            last_run = last_run.astimezone(self.timezone)

        base_time = last_run if last_run else now

        if pattern.time_of_day:
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
            today = now.replace(hour=hour, minute=minute, second=second, microsecond=0)
            if today <= now:
                next_time = (now + timedelta(days=1)).replace(
                    hour=hour, minute=minute, second=second, microsecond=0
                )
                if pattern.interval > 1:
                    next_time += timedelta(days=pattern.interval - 1)
            else:
                next_time = today

        elif pattern.unit == "weeks" and pattern.day_of_week is not None:
            current_dow = base_time.weekday()
            days_ahead = pattern.day_of_week - current_dow
            if days_ahead <= 0:
                days_ahead += 7
            next_time = (base_time + timedelta(days=days_ahead)).replace(
                hour=hour, minute=minute, second=second
            )
            if next_time <= now:
                next_time += timedelta(weeks=pattern.interval)

        elif pattern.unit == "months":
            current_day = pattern.day_of_month or base_time.day
            year = base_time.year
            month = base_time.month

            try:
                candidate_time = base_time.replace(
                    day=current_day, hour=hour, minute=minute, second=second
                )
                if candidate_time <= now:
                    month += pattern.interval
                    year += (month - 1) // 12
                    month = ((month - 1) % 12) + 1

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
                            current_day -= 1
                else:
                    next_time = candidate_time
            except ValueError:
                current_day -= 1
                next_time = self._calculate_next_occurrence(pattern, base_time)

        min_future_time = now + timedelta(seconds=30)
        if next_time < min_future_time:
            if pattern.unit in ["seconds", "minutes", "hours"]:
                next_time = now + timedelta(**{pattern.unit: pattern.interval})
            else:
                next_time = self._calculate_next_occurrence(
                    pattern, now + timedelta(days=1)
                )

            if next_time < min_future_time:
                logger.warning(
                    f"Next occurrence time {next_time} is less than 30 seconds in the future. Adjusting to now + 30 seconds."
                )
                next_time = min_future_time

        return next_time
