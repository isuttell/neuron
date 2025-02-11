import asyncio
import json
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.logger import logger


class RecurringPattern(BaseModel):
    interval: int = Field(description="The interval to trigger the prompt")
    unit: Literal["seconds", "minutes", "hours", "days", "weeks", "months"] = Field(
        description="The unit of time to trigger the prompt"
    )
    time_of_day: str | None = Field(
        description=(
            "HH:MM:SS or HH:MM format for daily/weekly/monthly. Must be in UTC."
        )
    )
    day_of_week: int | None = Field(description="0-6 for weekly (0 is Monday)")
    day_of_month: int | None = Field(description="1-31 for monthly")


class SchedulePromptToolArgs(BaseModel):
    event_id: str | None = Field(
        description=(
            "If provided this event will be updated instead of creating a new one."
        )
    )
    prompt: str | None = Field(
        description=(
            "The prompt to run. Required when creating a new event and event_id is "
            "not provided. It should be self contained and include all relevant "
            "context and step by step instructions. It should be in 2nd person "
            "describing the action to take. It will be executed by the assistant at "
            "the scheduled time. Do not include schedule information in the prompt "
            "unless it needs to be dynamic."
        )
    )
    trigger_time: datetime | None = Field(
        description=(
            "The time to trigger the prompt. Must be at least 30 seconds in the "
            "future to take into account processing time. Must be in UTC."
        )
    )
    recurring_pattern: RecurringPattern | None = Field(
        description="The recurring pattern to trigger the prompt. Must be in UTC."
    )


class SchedulePromptTool(BaseTool):
    name: str = "schedule_prompt"
    description: str = (
        "Schedules or edits an action to be taken on this thread at a given time "
        "or on a recurring schedule. For example, it can be used to generate a news "
        "report every morning at 7:30am or remind the user to take a break in 5 "
        "minutes or repeatedly monitor something until a condition is met. Use this "
        "to schedule prompts in the future or edit existing events. Be careful not "
        "to duplicate events."
    )

    args_schema: type[SchedulePromptToolArgs] = SchedulePromptToolArgs

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        config: RunnableConfig,
        prompt: str | None = None,
        event_id: str | None = None,
        trigger_time: datetime | None = None,
        recurring_pattern: RecurringPattern | None = None,
    ) -> str:
        try:
            from neuron_server.api import scheduler

            action = "create" if not event_id else "update"
            logger.debug(
                "%s event_id=%s prompt=%s trigger_time=%s recurring_pattern=%s",
                action,
                event_id,
                prompt,
                trigger_time,
                recurring_pattern,
            )

            if not recurring_pattern and not trigger_time:
                raise ValueError("trigger_time is required for non-recurring events")

            if action == "update":
                await scheduler.update_event(
                    event_id=event_id,
                    event_data={"prompt": prompt} if prompt else None,
                    trigger_time=trigger_time,
                    recurring_pattern=recurring_pattern,
                )
            else:
                if not prompt:
                    raise ValueError("prompt is required for creating a new event")
                event_id = str(uuid4())
                await scheduler.schedule_event(
                    event_id=event_id,
                    event_data={
                        "prompt": prompt,
                        "thread_id": config["configurable"]["thread_id"],
                        "personality_id": config["configurable"]["personality_id"],
                        "user_id": config["configurable"]["user_id"],
                        "username": config["configurable"]["username"],
                    },
                    trigger_time=trigger_time,
                    recurring_pattern=recurring_pattern,
                )

            # return the event data so we can verify it was created/updated correctly
            event = await scheduler.get_event(event_id)
            if event is None:
                raise RuntimeError(f"Failed to retrieve event after {action}")

            return f"""
event_id ({event_id}) successfully {action}d

```json
{json.dumps(event, indent=2)}
```
"""

        except Exception as e:
            logger.error("Error scheduling prompt: %s", str(e), exc_info=True)
            raise RuntimeError("Failed to schedule prompt") from e
