import asyncio

from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.logger import logger


class ScheduleRemoveToolArgs(BaseModel):
    event_ids: list[str] = Field(
        description="The event_id's to remove. This is permanent and cannot be undone."
    )


class ScheduleRemoveTool(BaseTool):
    name: str = "remove_scheduled_prompt"
    description: str = (
        """
Removes scheduled prompts by their event_id. Use the list_scheduled_prompts tool to get the event_id of the prompts to remove.
""".strip()
    )

    args_schema: type[ScheduleRemoveToolArgs] = ScheduleRemoveToolArgs

    def _run(self, *args, **kwargs) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        event_ids: list[str],
        config: RunnableConfig,
    ) -> str:
        try:
            from neuron_server.api import scheduler

            logger.debug(f"Removing scheduled events {event_ids}")
            for event_id in event_ids:
                try:
                    event = await scheduler.get_event(event_id)
                    if not event:
                        raise Exception(f"Event {event_id} not found")
                    if (
                        event["event_data"]["personality_id"]
                        != config["configurable"]["personality_id"]
                    ):
                        raise Exception(
                            f"Event {event_id} does not belong to personality {config['configurable']['personality_id']}"
                        )
                    await scheduler.delete_event(event_id)
                except Exception as e:
                    logger.error(
                        f"Error removing scheduled event {event_id}: {e}", exc_info=True
                    )
            return f"Events {event_ids} removed"
        except Exception as e:
            logger.error(
                f"Error removing scheduled events {event_ids}: {e}", exc_info=True
            )
            raise e


def main():
    tool = ScheduleRemoveTool()
    results = asyncio.run(
        tool.ainvoke(
            input={"event_id": "123"},
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
