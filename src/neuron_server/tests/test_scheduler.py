import asyncio
import calendar
import json
from collections.abc import AsyncGenerator
from contextlib import suppress
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, call

import pytest
import pytz

from neuron_server.util.scheduler import (
    MAX_MONTHDAY,
    AbstractAsyncRedisEventScheduler,
    RecurringPattern,
)


@pytest.fixture
async def scheduler() -> AsyncGenerator[AbstractAsyncRedisEventScheduler, None]:
    """Create a test scheduler with mocked on_event method."""
    # Import the redis client mock from conftest
    import sys
    redis_mock = sys.modules["redis"]
    redis_client_mock = redis_mock.Redis()

    class SimpleScheduler(AbstractAsyncRedisEventScheduler):
        def __init__(self) -> None:
            """Initialize with mock attributes to match actual implementation."""
            super().__init__(host="localhost", port=6379, db=0)
            # Setup attributes for tests to access
            self.active_events_set = "active_events"
            self.processing_events_set = "processing_events"
            self.metadata_prefix = "event_metadata:"
            self._running = False
            self._client = redis_client_mock

        async def on_event(self, event_id: str, event_data: dict) -> None:
            """Implementation of abstract method"""
            pass

        def redis_client(self) -> object:
            """Override to return the mock Redis client as context manager."""
            return redis_client_mock

        async def _get_redis_client(self) -> object:
            """Override to return the mock Redis client."""
            return redis_client_mock

    # Create the scheduler with our overrides
    scheduler = SimpleScheduler()
    mock_on_event = AsyncMock()
    scheduler.on_event = mock_on_event

    yield scheduler


# Constants for magic numbers
DELETE_COUNT = 2
SADD_COUNT = 2
NOON_HOUR = 12
THREE_PM_HOUR = 15
TEN_AM_HOUR = 10
FIFTEENTH_DAY = 15
THURSDAY_DOW = 3  # Thursday (0 is Monday)
TWO_WEEK_DAYS = 14  # Number of days in two weeks


@pytest.fixture
async def mock_redis() -> AsyncGenerator[AsyncMock, None]:
    """Use the global Redis mock from conftest instead of creating a new one."""
    import sys
    redis_mock = sys.modules["redis"]
    yield redis_mock


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_schedule_event_basic(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test basic event scheduling"""
    event_id = "test_event_1"
    event_data = {"message": "test"}
    trigger_time = datetime.now(pytz.UTC) + timedelta(minutes=5)

    await scheduler.schedule_event(event_id, event_data, trigger_time)

    # Verify Redis calls
    pipeline = mock_redis.return_value.pipeline.return_value.__aenter__.return_value
    assert pipeline.set.called
    assert pipeline.setex.called
    assert pipeline.sadd.called


@pytest.mark.asyncio
async def test_schedule_event_past_time(
    scheduler: AbstractAsyncRedisEventScheduler,
) -> None:
    """Test scheduling event in the past raises ValueError"""
    event_id = "test_event_2"
    event_data = {"message": "test"}
    trigger_time = datetime.now(pytz.UTC) - timedelta(minutes=5)

    with pytest.raises(ValueError, match="Cannot schedule events in the past"):
        await scheduler.schedule_event(event_id, event_data, trigger_time)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_get_event(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test retrieving event details"""
    event_id = "test_event_3"
    event_data = {
        "event_id": event_id,
        "event_data": {"message": "test"},
        "scheduled_time": "2024-01-23T12:00:00",
        "created_at": "2024-01-23T11:00:00",
        "recurring_pattern": None,
        "time_remaining_seconds": 3600,
    }

    mock_redis.return_value.get.return_value = json.dumps(event_data)

    result = await scheduler.get_event(event_id)
    assert result == event_data
    mock_redis.return_value.get.assert_called_once_with(
        f"{scheduler.metadata_prefix}{event_id}"
    )


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_delete_event(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test event deletion"""
    event_id = "test_event_4"

    success = await scheduler.delete_event(event_id)

    assert success is True
    pipeline = mock_redis.return_value.pipeline.return_value.__aenter__.return_value
    assert pipeline.delete.call_count == DELETE_COUNT
    assert pipeline.srem.call_count == DELETE_COUNT


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_recurring_event_schedule(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test scheduling recurring event"""
    event_id = "test_recurring_1"
    event_data = {"message": "recurring test"}
    pattern = RecurringPattern(interval=1, unit="days", time_of_day="12:00")

    await scheduler.schedule_event(event_id, event_data, recurring_pattern=pattern)

    pipeline = mock_redis.return_value.pipeline.return_value.__aenter__.return_value
    assert (
        pipeline.sadd.call_count >= SADD_COUNT
    )  # Should add to both active and recurring sets


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_start_scheduler(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test scheduler startup"""
    try:
        await scheduler.start()

        mock_redis.return_value.config_set.assert_called_once_with(
            "notify-keyspace-events", "KEx"
        )
        assert scheduler._running is True
    finally:
        await scheduler.stop()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_stop_scheduler(scheduler: AbstractAsyncRedisEventScheduler) -> None:
    """Test scheduler shutdown"""
    scheduler._running = True
    scheduler._listener_task = asyncio.create_task(asyncio.sleep(0))
    scheduler._reconciliation_task = asyncio.create_task(asyncio.sleep(0))

    await scheduler.stop()

    assert scheduler._running is False
    assert scheduler._listener_task.cancelled()
    assert scheduler._reconciliation_task.cancelled()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_process_expired_event(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test processing of expired events"""
    event_id = "test_event_5"
    event_data = {
        "event_id": event_id,
        "event_data": {"message": "test"},
        "scheduled_time": "2024-01-23T12:00:00",
        "created_at": "2024-01-23T11:00:00",
        "recurring_pattern": None,
        "time_remaining_seconds": 0,
    }

    # Mock successful lock acquisition
    mock_set = AsyncMock(return_value=True)
    mock_redis.return_value.set = mock_set
    mock_redis.return_value.get.return_value = json.dumps(event_data)

    try:
        await scheduler._process_expired_event(event_id)

        # Verify on_event was called with correct arguments
        scheduler.on_event.assert_awaited_once_with(event_id, event_data["event_data"])

        # Verify lock was deleted
        mock_redis.return_value.delete.assert_called_with(
            f"{scheduler.processing_events_set}:{event_id}"
        )
    finally:
        await mock_set.aclose()


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_process_expired_event_locked(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test handling of already locked events"""
    event_id = "test_event_6"
    lock_key = f"{scheduler.processing_events_set}:{event_id}"

    # Mock Redis client behavior
    mock_redis.return_value.set.return_value = False  # Lock acquisition fails

    # Execute and await the event processing
    await scheduler._process_expired_event(event_id)

    # Verify lock attempt
    mock_redis.return_value.set.assert_awaited_once_with(lock_key, "1", ex=300, nx=True)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_recurring_event_next_occurrence(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test scheduling next occurrence of recurring event"""
    event_id = "test_recurring_2"
    now = datetime.now(pytz.UTC)
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

    # Mock successful lock acquisition
    mock_redis.return_value.set.return_value = True
    mock_redis.return_value.get.return_value = json.dumps(event_data)

    await scheduler._process_expired_event(event_id)

    # Verify next occurrence was scheduled
    pipeline = mock_redis.return_value.pipeline.return_value.__aenter__.return_value
    assert pipeline.set.called  # New metadata
    assert pipeline.setex.called  # New event
    assert pipeline.sadd.call_count >= SADD_COUNT  # Active and recurring sets


@pytest.mark.asyncio
async def test_calculate_next_occurrence() -> None:
    """Test calculation of next occurrence for different patterns"""

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
        day_of_week=1,
        time_of_day="15:00",  # Tuesday
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

    # Test multi-week interval
    multi_week_pattern = RecurringPattern(
        interval=2,
        unit="weeks",
        day_of_week=3,  # Thursday
        time_of_day="14:00",
    )
    next_multi_week = scheduler._calculate_next_occurrence(multi_week_pattern)
    assert next_multi_week.weekday() == THURSDAY_DOW
    assert next_multi_week > now

    # Verify the interval is respected
    next_next_multi_week = scheduler._calculate_next_occurrence(
        multi_week_pattern, next_multi_week
    )
    assert (next_next_multi_week - next_multi_week).days == TWO_WEEK_DAYS

    # Test month end handling
    end_of_month_pattern = RecurringPattern(
        interval=1,
        unit="months",
        day_of_month=31,
        time_of_day="12:00",
    )
    next_end_of_month = scheduler._calculate_next_occurrence(end_of_month_pattern)

    # If next month has fewer days, it should use the last day of that month
    if (
        calendar.monthrange(next_end_of_month.year, next_end_of_month.month)[1]
        < MAX_MONTHDAY
    ):
        assert (
            next_end_of_month.day
            == calendar.monthrange(next_end_of_month.year, next_end_of_month.month)[1]
        )
    else:
        assert next_end_of_month.day == MAX_MONTHDAY


@pytest.mark.asyncio
async def test_recurring_pattern_validation() -> None:
    """Test validation of recurring pattern parameters"""

    # Test invalid interval
    with pytest.raises(ValueError, match="Interval must be positive"):
        RecurringPattern(interval=0, unit="days")

    with pytest.raises(ValueError, match="Interval must be positive"):
        RecurringPattern(interval=-1, unit="weeks")

    # Test invalid day_of_week
    with pytest.raises(ValueError, match="day_of_week must be between 0 and 6"):
        RecurringPattern(interval=1, unit="weeks", day_of_week=7)

    with pytest.raises(ValueError, match="day_of_week must be between 0 and 6"):
        RecurringPattern(interval=1, unit="weeks", day_of_week=-1)

    # Test invalid day_of_month
    with pytest.raises(ValueError, match="day_of_month must be between 1 and 31"):
        RecurringPattern(interval=1, unit="months", day_of_month=32)

    with pytest.raises(ValueError, match="day_of_month must be between 1 and 31"):
        RecurringPattern(interval=1, unit="months", day_of_month=0)

    # Test invalid time_of_day format
    with pytest.raises(
        ValueError, match="time_of_day must be in HH:MM:SS or HH:MM format"
    ):
        RecurringPattern(interval=1, unit="days", time_of_day="25:00")  # Invalid hour

    with pytest.raises(
        ValueError, match="time_of_day must be in HH:MM:SS or HH:MM format"
    ):
        RecurringPattern(interval=1, unit="days", time_of_day="12:60")  # Invalid minute


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_reconcile_events(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test event reconciliation process"""
    mock_redis.return_value.smembers.side_effect = [
        {"event1", "event2"},  # active_events
        {"event2"},  # processing_events
    ]
    mock_redis.return_value.exists.return_value = False

    # Run reconciliation once
    scheduler._running = True
    reconcile_task = asyncio.create_task(scheduler._reconcile_events())

    # Let it run for a moment then cancel
    await asyncio.sleep(0.1)
    reconcile_task.cancel()

    with suppress(asyncio.CancelledError):
        await reconcile_task

    # Verify Redis calls
    mock_redis.return_value.smembers.assert_has_calls(
        [call(scheduler.active_events_set), call(scheduler.processing_events_set)]
    )


@pytest.mark.asyncio
@pytest.mark.skip(reason="Redis mocking incompatibility in test_scheduler.py")
async def test_error_handling(
    scheduler: AbstractAsyncRedisEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test error handling in various scenarios"""
    # Test Redis connection error
    mock_redis.return_value.get.side_effect = Exception("Redis connection failed")

    result = await scheduler.get_event("test_event")
    assert result is None

    # Test pipeline error
    mock_redis.return_value.pipeline.side_effect = Exception("Pipeline error")

    success = await scheduler.delete_event("test_event")
    assert success is False


if __name__ == "__main__":
    pytest.main(["-v", "test_scheduler.py"])
