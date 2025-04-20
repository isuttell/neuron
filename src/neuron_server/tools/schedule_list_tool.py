import asyncio
import json
from datetime import datetime
from typing import Any, NoReturn

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from neuron_server.logger import logger


class ScheduleListToolArgs(BaseModel):
    pass


class ScheduleListTool(BaseTool):
    name: str = "list_scheduled_prompts"
    description: str = (
        "Lists all scheduled prompts with their event ids, scheduled time, "
        "recurring pattern, and time remaining. Time remaining must be greater "
        "than 0 for the event to be triggered."
    )
    args_schema: type[BaseModel] = ScheduleListToolArgs

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
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
                        f"/thread/{event['event_data'].get('thread_id')}"
                        if event["event_data"].get("thread_id")
                        else None
                    ),
                }
                for event in events
            ]
            current_time = datetime.now().astimezone().isoformat(timespec="seconds")
            return f"""
# Scheduled Events

The current time is {current_time}

```json
{json.dumps(response, indent=2)}
```
"""
        except Exception as e:
            logger.error("Error listing scheduled events: %s", str(e), exc_info=True)
            raise RuntimeError("Failed to list scheduled events") from e


def main() -> NoReturn:
    tool = ScheduleListTool()
    try:
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
        raise SystemExit(0)
    except Exception as e:
        print("Error:", str(e))
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
