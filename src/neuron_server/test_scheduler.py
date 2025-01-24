import asyncio
import logging
from datetime import datetime, timedelta
import pytz
import sys
from neuron_server.util.scheduler import AsyncRedisEventScheduler, RecurringPattern

# Configure event loop policy for Windows
if sys.platform == "win32":
    from asyncio import WindowsSelectorEventLoopPolicy

    asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Use UTC for all datetime operations
UTC = pytz.UTC


class TestScheduler(AsyncRedisEventScheduler):
    """Test scheduler that doesn't interact with the database"""

    async def on_event(self, event_id: str, event_data: dict):
        """Simple event handler that just logs the event"""
        logger.info(
            f"Event triggered - id: {event_id}, data: {event_data}, time: {datetime.now(UTC).isoformat()}"
        )


async def main():
    # Initialize scheduler
    scheduler = TestScheduler()
    await scheduler.start()

    try:
        # Test 1: One-time event (5 seconds from now)
        now = datetime.now(UTC)
        await scheduler.schedule_event(
            "test_one_time",
            {"message": "This is a one-time test event"},
            now + timedelta(seconds=5),
        )
        logger.info("Scheduled one-time event")

        # Test 2: Recurring event (every 10 seconds)
        await scheduler.schedule_event(
            "test_recurring",
            {"message": "This is a recurring test event"},
            recurring_pattern=RecurringPattern(interval=10, unit="seconds"),
        )
        logger.info("Scheduled recurring event")

        # Test 3: Rapid events to test locking
        now = datetime.now(UTC)
        for i in range(5):
            await scheduler.schedule_event(
                f"test_rapid_{i}",
                {"message": f"Rapid test event {i}"},
                now + timedelta(seconds=2),
            )
        logger.info("Scheduled rapid events")

        # Keep running for 30 seconds to observe events
        await asyncio.sleep(30)

    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
