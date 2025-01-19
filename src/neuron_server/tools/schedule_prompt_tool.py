from langchain.tools import BaseTool
from typing import List, Type, Literal, Optional
from pydantic import BaseModel, Field
import random
from neuron_server.logger import logger
from datetime import datetime
import asyncio
from langchain_core.runnables import RunnableConfig
from uuid import uuid4


class RecurringPattern(BaseModel):
    interval: int = Field(description="The interval to trigger the prompt")
    unit: Literal["seconds", "minutes", "hours", "days", "weeks", "months"] = Field(
        description="The unit of time to trigger the prompt"
    )
    time_of_day: Optional[str] = Field(
        description="HH:MM:SS or HH:MM format for daily/weekly/monthly. Must be in UTC."
    )
    day_of_week: Optional[int] = Field(description="0-6 for weekly (0 is Monday)")
    day_of_month: Optional[int] = Field(description="1-31 for monthly")


class SchedulePromptToolArgs(BaseModel):
    event_id: Optional[str] = Field(
        description="If provided this event will be updated instead of creating a new one."
    )
    prompt: Optional[str] = Field(
        description="The prompt to schedule. Required creating a new event and event_id is not provided. Include all relevant context and instructions. It should be in 2nd person describing the action to take. It will be executed by the AI at the scheduled time."
    )
    trigger_time: Optional[datetime] = Field(
        description="The time to trigger the prompt. Must be at least 30 seconds in the future to take into account the time it takes to process the request. Must be in UTC."
    )
    recurring_pattern: Optional[RecurringPattern] = Field(
        description="The recurring pattern to trigger the prompt. Must be in UTC."
    )


class SchedulePromptTool(BaseTool):
    name: str = "schedule_prompt"
    description: str = (
        """
Schedules or edits an action to be taken on this thread at a given time or on a recurring schedule. For example, it can be used to generate a news report every morning at 7:30am or remind the user to take a break in 5 minutes or repeatedly monitor something until a condition is met. Use this to schedule prompts in the future or edit existing events. Be careful not to duplicate events.
""".strip()
    )

    args_schema: Type[SchedulePromptToolArgs] = SchedulePromptToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        config: RunnableConfig,
        prompt: Optional[str] = None,
        event_id: Optional[str] = None,
        trigger_time: Optional[datetime] = None,
        recurring_pattern: Optional[RecurringPattern] = None,
    ) -> str:
        try:
            from neuron_server.api import scheduler

            action = "create" if not event_id else "update"
            logger.debug(f"{action} prompt: {prompt}")
            if not recurring_pattern and not trigger_time:
                raise ValueError("trigger_time is required for non-recurring events")
            if action == "update":
                await scheduler.update_event(
                    event_id=event_id,
                    new_data={"prompt": prompt},
                    new_trigger_time=trigger_time,
                    new_recurring_pattern=recurring_pattern,
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
            return f"event_id ({event_id}) successfully {action}d"
        except Exception as e:
            logger.error(f"Error scheduling prompt: {e}", exc_info=True)
            raise e
