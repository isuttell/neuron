import asyncio
import json
from collections.abc import Generator
from contextlib import suppress
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, call, patch

import pytest
import pytz

from neuron_server.util.scheduler import AsyncRedisEventScheduler, RecurringPattern

# Constants for magic numbers
DELETE_COUNT = 2
SADD_COUNT = 2
NOON_HOUR = 12
THREE_PM_HOUR = 15
TEN_AM_HOUR = 10
FIFTEENTH_DAY = 15


class TestEventScheduler(AsyncRedisEventScheduler):
    """Test implementation of AsyncRedisEventScheduler"""

    async def on_event(self, event_id: str, event_data: dict) -> None:
        pass


@pytest.fixture
def scheduler() -> TestEventScheduler:
    return TestEventScheduler(host="localhost", port=6379, db=2)


@pytest.fixture
def mock_redis() -> Generator[AsyncMock, None, None]:
    with patch("redis.asyncio.Redis") as mock:
        # Create AsyncMock instances for Redis methods
        mock.return_value.get = AsyncMock()
        mock.return_value.set = AsyncMock()
        mock.return_value.setex = AsyncMock()
        mock.return_value.delete = AsyncMock()
        mock.return_value.sadd = AsyncMock()
        mock.return_value.srem = AsyncMock()
        mock.return_value.smembers = AsyncMock()
        mock.return_value.exists = AsyncMock()
        mock.return_value.close = AsyncMock()
        mock.return_value.config_set = AsyncMock()
        mock.return_value.pubsub = AsyncMock()

        # Mock pipeline
        pipeline_mock = AsyncMock()
        pipeline_mock.execute = AsyncMock()
        mock.return_value.pipeline.return_value.__aenter__.return_value = pipeline_mock

        yield mock


@pytest.mark.asyncio
async def test_schedule_event_basic(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
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
async def test_schedule_event_past_time(scheduler: TestEventScheduler) -> None:
    """Test scheduling event in the past raises ValueError"""
    event_id = "test_event_2"
    event_data = {"message": "test"}
    trigger_time = datetime.now(pytz.UTC) - timedelta(minutes=5)

    with pytest.raises(ValueError, match="Cannot schedule events in the past"):
        await scheduler.schedule_event(event_id, event_data, trigger_time)


@pytest.mark.asyncio
async def test_get_event(scheduler: TestEventScheduler, mock_redis: AsyncMock) -> None:
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
async def test_delete_event(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test event deletion"""
    event_id = "test_event_4"

    success = await scheduler.delete_event(event_id)

    assert success is True
    pipeline = mock_redis.return_value.pipeline.return_value.__aenter__.return_value
    assert pipeline.delete.call_count == DELETE_COUNT
    assert pipeline.srem.call_count == DELETE_COUNT


@pytest.mark.asyncio
async def test_recurring_event_schedule(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
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
async def test_start_scheduler(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test scheduler startup"""
    await scheduler.start()

    mock_redis.return_value.config_set.assert_called_once_with(
        "notify-keyspace-events", "KEx"
    )
    assert scheduler._running is True


@pytest.mark.asyncio
async def test_stop_scheduler(scheduler: TestEventScheduler) -> None:
    """Test scheduler shutdown"""
    scheduler._running = True
    scheduler._listener_task = asyncio.create_task(asyncio.sleep(0))
    scheduler._reconciliation_task = asyncio.create_task(asyncio.sleep(0))

    await scheduler.stop()

    assert scheduler._running is False
    assert scheduler._listener_task.cancelled()
    assert scheduler._reconciliation_task.cancelled()


@pytest.mark.asyncio
async def test_process_expired_event(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
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
    mock_redis.return_value.set.return_value = True
    mock_redis.return_value.get.return_value = json.dumps(event_data)

    # Mock the on_event method
    with patch.object(scheduler, "on_event", new_callable=AsyncMock) as mock_on_event:
        await scheduler._process_expired_event(event_id)

        mock_on_event.assert_called_once_with(event_id, event_data["event_data"])
        # Verify lock was deleted
        mock_redis.return_value.delete.assert_called_with(
            f"{scheduler.processing_events_set}:{event_id}"
        )


@pytest.mark.asyncio
async def test_process_expired_event_locked(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
) -> None:
    """Test handling of already locked events"""
    event_id = "test_event_6"

    # Mock failed lock acquisition
    mock_redis.return_value.set.return_value = False

    await scheduler._process_expired_event(event_id)

    # Verify event was not processed
    mock_redis.return_value.get.assert_not_called()


@pytest.mark.asyncio
async def test_recurring_event_next_occurrence(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
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
    scheduler = TestEventScheduler()
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


@pytest.mark.asyncio
async def test_reconcile_events(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
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
async def test_error_handling(
    scheduler: TestEventScheduler, mock_redis: AsyncMock
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
