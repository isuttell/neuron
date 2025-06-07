import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import pytz

from neuron_server.util.scheduler import (
    AbstractAsyncRedisEventScheduler,
    RecurringPattern,
)

# Constants for testing
NOON_HOUR = 12
THREE_PM_HOUR = 15
TEN_AM_HOUR = 10
FIFTEENTH_DAY = 15
THURSDAY_DOW = 3  # Thursday (0 is Monday)
TWO_WEEK_DAYS = 14  # Number of days in two weeks
EVENT_COUNT = 3
USER1_EVENT_COUNT = 2
REMINDER_EVENT_COUNT = 2


@pytest.fixture
async def scheduler() -> AsyncGenerator[AbstractAsyncRedisEventScheduler, None]:
    """Create a test scheduler with mock Redis client."""

    class TestScheduler(AbstractAsyncRedisEventScheduler):
        def __init__(self) -> None:
            """Initialize with test attributes."""
            super().__init__(host="localhost", port=6379, db=0)
            # Store data in memory
            self.data: dict[str, str] = {}
            self.sets: dict[str, set[str]] = {
                "active_events": set(),
                "processing_events": set(),
                "recurring_events": set(),
            }

        async def on_event(self, event_id: str, event_data: dict) -> None:
            """Implementation of abstract method."""
            pass

        # Split redis_client mocking into multiple methods to reduce complexity
        @asynccontextmanager
        async def redis_client(self) -> AsyncGenerator[MagicMock, None]:
            """Override to simulate Redis with in-memory operations."""
            client = MagicMock()

            # Setup basic Redis operations
            self._setup_basic_operations(client)

            # Setup additional Redis operations
            self._setup_set_operations(client)

            # Setup pipeline operations
            self._setup_pipeline(client)

            try:
                yield client
            finally:
                pass

        def _setup_basic_operations(self, client: MagicMock) -> None:
            """Set up basic Redis operations."""

            async def mock_get(key: str) -> Optional[str]:
                return self.data.get(key)

            client.get = AsyncMock(side_effect=mock_get)

            async def mock_set(
                key: str,
                value: str,
                ex: Optional[int] = None,
                nx: Optional[bool] = None,
            ) -> bool:
                if nx and key in self.data:
                    return False
                self.data[key] = value
                return True

            client.set = AsyncMock(side_effect=mock_set)

            async def mock_setex(key: str, ttl: int, value: str) -> bool:
                self.data[key] = value
                return True

            client.setex = AsyncMock(side_effect=mock_setex)

            async def mock_delete(key: str) -> bool:
                if key in self.data:
                    del self.data[key]
                return True

            client.delete = AsyncMock(side_effect=mock_delete)

            # Mock Redis exists method
            async def mock_exists(key: str) -> bool:
                return key in self.data

            client.exists = AsyncMock(side_effect=mock_exists)

            # Mock Redis config_set method
            client.config_set = AsyncMock(return_value=True)

        def _setup_set_operations(self, client: MagicMock) -> None:
            """Set up Redis set operations."""

            async def mock_sadd(set_name: str, *values: str) -> int:
                if set_name not in self.sets:
                    self.sets[set_name] = set()
                self.sets[set_name].update(values)
                return len(values)

            client.sadd = AsyncMock(side_effect=mock_sadd)

            async def mock_srem(set_name: str, *values: str) -> int:
                if set_name not in self.sets:
                    return 0
                removed = 0
                for value in values:
                    if value in self.sets[set_name]:
                        self.sets[set_name].remove(value)
                        removed += 1
                return removed

            client.srem = AsyncMock(side_effect=mock_srem)

            async def mock_smembers(set_name: str) -> set[str]:
                return self.sets.get(set_name, set())

            client.smembers = AsyncMock(side_effect=mock_smembers)

            async def mock_mget(keys: list[str]) -> list[Optional[str]]:
                return [self.data.get(key) for key in keys]

            client.mget = AsyncMock(side_effect=mock_mget)

            # Mock PubSub
            pubsub = AsyncMock()
            pubsub.psubscribe = AsyncMock()
            pubsub.listen = AsyncMock()
            pubsub.__aiter__ = AsyncMock(return_value=pubsub)
            pubsub.__anext__ = AsyncMock(side_effect=StopAsyncIteration)
            client.pubsub = Mock(return_value=pubsub)

        def _setup_pipeline(self, client: MagicMock) -> None:
            """Set up Redis pipeline operations."""
            pipeline = AsyncMock()
            pipeline.__aenter__ = AsyncMock(return_value=pipeline)
            pipeline.__aexit__ = AsyncMock(return_value=None)

            # Track pipeline commands for execution
            commands = []

            def add_command(cmd_type: str) -> callable:
                def command_adder(*args: Any, **kwargs: Any) -> AsyncMock:
                    commands.append((cmd_type, args, kwargs))
                    return pipeline

                return command_adder

            # Add pipeline methods
            pipeline.set = AsyncMock(side_effect=add_command("set"))
            pipeline.setex = AsyncMock(side_effect=add_command("setex"))
            pipeline.delete = AsyncMock(side_effect=add_command("delete"))
            pipeline.sadd = AsyncMock(side_effect=add_command("sadd"))
            pipeline.srem = AsyncMock(side_effect=add_command("srem"))

            # Add execute method that processes all commands
            async def execute() -> list[Any]:
                results = []
                for cmd_type, args, kwargs in commands:
                    method = getattr(client, cmd_type)
                    if cmd_type == "setex":
                        key, ttl, value = args
                        results.append(await client.set(key, value, ex=ttl))
                    else:
                        results.append(await method(*args, **kwargs))
                commands.clear()
                return results

            pipeline.execute = AsyncMock(side_effect=execute)
            client.pipeline = Mock(return_value=pipeline)

    # Create the scheduler
    scheduler = TestScheduler()
    scheduler.on_event = AsyncMock()

    yield scheduler


@pytest.mark.asyncio
async def test_schedule_event_basic(
    scheduler: AbstractAsyncRedisEventScheduler,
) -> None:
    """Test basic event scheduling."""
    event_id = "test_event_1"
    event_data = {"message": "test"}
    trigger_time = datetime.now(pytz.UTC) + timedelta(minutes=5)

    await scheduler.schedule_event(event_id, event_data, trigger_time)

    # Verify data was stored
    metadata_key = f"{scheduler.metadata_prefix}{event_id}"

    # Check metadata and event data
    assert scheduler.data.get(metadata_key) is not None
    metadata = json.loads(scheduler.data.get(metadata_key))
    assert metadata["event_id"] == event_id
    assert metadata["event_data"] == event_data

    # Check event was added to active events set
    assert event_id in scheduler.sets["active_events"]


@pytest.mark.asyncio
async def test_get_event(scheduler: AbstractAsyncRedisEventScheduler) -> None:
    """Test retrieving event details."""
    event_id = "test_event_3"
    event_data = {
        "event_id": event_id,
        "event_data": {"message": "test"},
        "scheduled_time": "2024-01-23T12:00:00",
        "created_at": "2024-01-23T11:00:00",
        "recurring_pattern": None,
        "time_remaining_seconds": 3600,
    }

    # Store test data
    scheduler.data[f"{scheduler.metadata_prefix}{event_id}"] = json.dumps(event_data)

    # Retrieve event
    result = await scheduler.get_event(event_id)
    assert result == event_data


@pytest.mark.asyncio
async def test_delete_event(scheduler: AbstractAsyncRedisEventScheduler) -> None:
    """Test event deletion."""
    event_id = "test_event_4"

    # Setup test data
    metadata_key = f"{scheduler.metadata_prefix}{event_id}"
    event_key = f"event:{event_id}"

    scheduler.data[metadata_key] = json.dumps({"event_id": event_id})
    scheduler.data[event_key] = json.dumps({"message": "test"})
    scheduler.sets["active_events"].add(event_id)
    scheduler.sets["recurring_events"].add(event_id)

    # Delete event
    success = await scheduler.delete_event(event_id)

    # Verify deletion
    assert success is True
    assert metadata_key not in scheduler.data
    assert event_key not in scheduler.data
    assert event_id not in scheduler.sets["active_events"]
    assert event_id not in scheduler.sets["recurring_events"]


@pytest.mark.asyncio
async def test_recurring_event_schedule(
    scheduler: AbstractAsyncRedisEventScheduler,
) -> None:
    """Test scheduling recurring event."""
    event_id = "test_recurring_1"
    event_data = {"message": "recurring test"}
    pattern = RecurringPattern(interval=1, unit="days", time_of_day="12:00")

    await scheduler.schedule_event(event_id, event_data, recurring_pattern=pattern)

    # Verify event was added to sets
    assert event_id in scheduler.sets["active_events"]
    assert event_id in scheduler.sets["recurring_events"]

    # Verify metadata contains recurring pattern
    metadata_key = f"{scheduler.metadata_prefix}{event_id}"
    assert metadata_key in scheduler.data

    metadata = json.loads(scheduler.data[metadata_key])
    assert metadata["recurring_pattern"] is not None
    assert metadata["recurring_pattern"]["interval"] == 1
    assert metadata["recurring_pattern"]["unit"] == "days"
    assert metadata["recurring_pattern"]["time_of_day"] == "12:00"


@pytest.mark.asyncio
async def test_process_expired_event(
    scheduler: AbstractAsyncRedisEventScheduler,
) -> None:
    """Test processing of expired events."""
    event_id = "test_event_5"
    event_data = {
        "event_id": event_id,
        "event_data": {"message": "test"},
        "scheduled_time": "2024-01-23T12:00:00",
        "created_at": "2024-01-23T11:00:00",
        "recurring_pattern": None,
        "time_remaining_seconds": 0,
    }

    # Store test data
    scheduler.data[f"{scheduler.metadata_prefix}{event_id}"] = json.dumps(event_data)

    # Process the event
    await scheduler._process_expired_event(event_id)

    # Verify on_event was called
    scheduler.on_event.assert_awaited_once_with(event_id, event_data["event_data"])

    # Non-recurring event should be deleted
    assert f"{scheduler.metadata_prefix}{event_id}" not in scheduler.data


@pytest.mark.asyncio
async def test_process_expired_event_locked(
    scheduler: AbstractAsyncRedisEventScheduler,
) -> None:
    """Test handling of already locked events."""
    event_id = "test_event_6"
    lock_key = f"{scheduler.processing_events_set}:{event_id}"

    # Pre-set the lock
    scheduler.data[lock_key] = "1"

    # Process the event
    await scheduler._process_expired_event(event_id)

    # Verify on_event was not called
    scheduler.on_event.assert_not_called()


@pytest.mark.asyncio
async def test_recurring_event_next_occurrence(
    scheduler: AbstractAsyncRedisEventScheduler,
) -> None:
    """Test scheduling next occurrence of recurring event."""
    event_id = "test_recurring_2"
    now = datetime.now(pytz.UTC)

    # Create a recurring event with a daily pattern
    event_data = {
        "event_id": event_id,
        "event_data": {"message": "recurring test"},
        "scheduled_time": now.isoformat(),
        "created_at": (now - timedelta(days=1)).isoformat(),
        "recurring_pattern": {
            "interval": 1,
            "unit": "days",
            "time_of_day": "12:00",
        },
        "time_remaining_seconds": 0,
    }

    # Store test data
    scheduler.data[f"{scheduler.metadata_prefix}{event_id}"] = json.dumps(event_data)

    # Process the event
    await scheduler._process_expired_event(event_id)

    # Verify on_event was called
    scheduler.on_event.assert_awaited_once_with(event_id, event_data["event_data"])

    # Recurring event should be scheduled again
    metadata_key = f"{scheduler.metadata_prefix}{event_id}"
    assert metadata_key in scheduler.data

    metadata = json.loads(scheduler.data[metadata_key])
    next_time = datetime.fromisoformat(metadata["scheduled_time"])

    # Verify next time is in the future and at correct time
    assert next_time > now
    assert next_time.hour == NOON_HOUR
    assert next_time.minute == 0


@pytest.mark.asyncio
async def test_list_events(scheduler: AbstractAsyncRedisEventScheduler) -> None:
    """Test listing events with optional filtering."""
    # Setup test data for multiple events
    events = [
        {
            "event_id": "event1",
            "event_data": {"type": "reminder", "user_id": "user1"},
            "scheduled_time": "2024-01-23T12:00:00",
            "created_at": "2024-01-23T11:00:00",
            "recurring_pattern": None,
            "time_remaining_seconds": 3600,
        },
        {
            "event_id": "event2",
            "event_data": {"type": "notification", "user_id": "user1"},
            "scheduled_time": "2024-01-23T13:00:00",
            "created_at": "2024-01-23T11:00:00",
            "recurring_pattern": None,
            "time_remaining_seconds": 7200,
        },
        {
            "event_id": "event3",
            "event_data": {"type": "reminder", "user_id": "user2"},
            "scheduled_time": "2024-01-23T14:00:00",
            "created_at": "2024-01-23T11:00:00",
            "recurring_pattern": None,
            "time_remaining_seconds": 10800,
        },
    ]

    # Add events
    for event in events:
        key = f"{scheduler.metadata_prefix}{event['event_id']}"
        scheduler.data[key] = json.dumps(event)
        scheduler.sets["active_events"].add(event["event_id"])

    # Test listing all events
    all_events = await scheduler.list_events()
    assert len(all_events) == EVENT_COUNT

    # Test filtering by user_id in event_data
    user1_events = await scheduler.list_events(filters={"user_id": "user1"})
    assert len(user1_events) == USER1_EVENT_COUNT
    assert all(event["event_data"]["user_id"] == "user1" for event in user1_events)

    # Test filtering by type in event_data
    reminder_events = await scheduler.list_events(filters={"type": "reminder"})
    assert len(reminder_events) == REMINDER_EVENT_COUNT
    assert all(event["event_data"]["type"] == "reminder" for event in reminder_events)

    # Test compound filters
    filters = {"user_id": "user1", "type": "reminder"}
    user1_reminders = await scheduler.list_events(filters=filters)
    assert len(user1_reminders) == 1


@pytest.mark.asyncio
async def test_calculate_next_occurrence() -> None:
    """Test calculation of next occurrence for different patterns."""

    class SimpleScheduler(AbstractAsyncRedisEventScheduler):
        async def on_event(self, event_id: str, event_data: dict) -> None:
            pass

    scheduler = SimpleScheduler()
    now = datetime.now(pytz.UTC)

    # Test daily pattern
    daily_pattern = RecurringPattern(interval=1, unit="days", time_of_day="12:00")
    next_daily = scheduler._calculate_next_occurrence(daily_pattern)
    assert next_daily.hour == NOON_HOUR
    assert next_daily.minute == 0
    assert next_daily > now

    # Test weekly pattern
    weekly_pattern = RecurringPattern(
        interval=1,
        unit="weeks",
        day_of_week=1,  # Tuesday
        time_of_day="15:00",
    )
    next_weekly = scheduler._calculate_next_occurrence(weekly_pattern)
    assert next_weekly.hour == THREE_PM_HOUR
    assert next_weekly.minute == 0
    assert next_weekly.weekday() == 1
    assert next_weekly > now

    # Test monthly pattern
    monthly_pattern = RecurringPattern(
        interval=1, unit="months", day_of_month=15, time_of_day="10:00"
    )
    next_monthly = scheduler._calculate_next_occurrence(monthly_pattern)
    assert next_monthly.hour == TEN_AM_HOUR
    assert next_monthly.minute == 0
    assert next_monthly.day == FIFTEENTH_DAY
    assert next_monthly > now
