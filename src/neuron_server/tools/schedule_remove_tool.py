import asyncio
from typing import Any, NoReturn

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.logger import logger


class ScheduleRemoveToolArgs(BaseModel):
    event_ids: list[str] = Field(
        description=(
            "The event_id's to remove. This is permanent and cannot be undone."
        )
    )


class ScheduleRemoveTool(BaseTool):
    name: str = "remove_scheduled_prompt"
    description: str = (
        "Removes scheduled prompts by their event_id. Use the list_scheduled_prompts "
        "tool to get the event_id of the prompts to remove."
    )

    args_schema: type[ScheduleRemoveToolArgs] = ScheduleRemoveToolArgs

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        event_ids: list[str],
        config: RunnableConfig,
    ) -> str:
        try:
            from neuron_server.api import scheduler

            logger.debug("Removing scheduled events %s", event_ids)
            failed_events = []
            personality_id = config["configurable"]["personality_id"]
            for event_id in event_ids:
                try:
                    event = await scheduler.get_event(event_id)
                    if not event:
                        raise ValueError(f"Event {event_id} not found")

                    if event["event_data"]["personality_id"] != personality_id:
                        raise ValueError(
                            f"Event {event_id} does not belong to personality {personality_id}"  # noqa: E501
                        )

                    await scheduler.delete_event(event_id)
                except Exception as e:
                    logger.error(
                        "Error removing scheduled event %s: %s",
                        event_id,
                        str(e),
                        exc_info=True,
                    )
                    failed_events.append(event_id)

            if failed_events:
                raise RuntimeError(
                    f"Failed to remove events: {', '.join(failed_events)}"
                )

            return f"Successfully removed events: {', '.join(event_ids)}"

        except Exception as e:
            logger.error(
                "Error removing scheduled events %s: %s",
                event_ids,
                str(e),
                exc_info=True,
            )
            raise RuntimeError("Failed to remove scheduled events") from e


def main() -> NoReturn:
    tool = ScheduleRemoveTool()
    try:
        results = asyncio.run(
            tool.ainvoke(
                input={"event_ids": ["123"]},
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
