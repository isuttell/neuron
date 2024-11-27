from langchain.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field
from neuron_server.logger import logger
import asyncio
import time


class WaitToolArgs(BaseModel):
    duration: float = Field(
        description="The number of seconds to wait before continuing. Must be a positive integer over zero."
    )


class WaitTool(BaseTool):
    name: str = "wait"
    description: str = (
        """
This tool allows you to pause the execution of an agent for a specified number of seconds. It is useful for scenarios where you need to wait before proceeding, such as taking another image in a sequence. For instance, to wait for 5 seconds before capturing the next image, set the duration to 5.
""".strip()
    )

    args_schema: Type[WaitToolArgs] = WaitToolArgs

    def _run(self, duration: float) -> str:
        logger.debug(f"Waiting for {str(duration)} seconds...")
        time.sleep(duration)
        return f"Waited for {str(duration)} seconds"

    async def _arun(self, duration: float) -> str:
        logger.debug(f"Waiting for {str(duration)} seconds...")
        await asyncio.sleep(duration)
        return f"Waited for {str(duration)} seconds"
