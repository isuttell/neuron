import asyncio
import json
from datetime import datetime

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig

from neuron_server.logger import logger


class ScheduleListTool(BaseTool):
    name: str = "list_scheduled_prompts"
    description: str = (
        """
Lists all scheduled prompts with their event ids, scheduled time, recurring pattern, and time remaining. Time remaining must be greater than 0 for the event to be triggered.
""".strip()
    )

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        config: RunnableConfig,
    ) -> str:
        try:
            from neuron_server.api import scheduler

            logger.debug("Listing scheduled events")
            events = await scheduler.list_events(
                filters={"personality_id": config["configurable"]["personality_id"]}
            )
            response = [
                {
                    "event_id": event["event_id"],
                    "scheduled_time": event["scheduled_time"],
                    "recurring_pattern": event["recurring_pattern"],
                    "time_remaining_seconds": event["time_remaining_seconds"],
                    "prompt": event["event_data"]["prompt"],
                    "link": (
                        f"[Thread History](/thread/{event['event_data'].get('thread_id')})"
                        if event["event_data"].get("thread_id")
                        else None
                    ),
                }
                for event in events
            ]
            return f"# Scheduled Events\n\nThe current time is {datetime.now().astimezone().isoformat(timespec='seconds')}\n\n```json\n{json.dumps(response, indent=2)}\n```"
        except Exception as e:
            logger.error(f"Error listing scheduled events: {e}", exc_info=True)
            raise e


def main():
    tool = ScheduleListTool()
    results = asyncio.run(
        tool.ainvoke(
            input={},
            config={
                "configurable": {
                    "personality_id": "716f3e34-b95a-4c16-8d6f-4561c5f2b7db"
                }
            },
        )
    )
    print(results)


if __name__ == "__main__":
    main()
