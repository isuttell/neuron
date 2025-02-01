import asyncio
import time
from typing import Any

import aiohttp
from langchain.tools import BaseTool
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from neuron_server.config import config as neuron_config


class SendNotificationToolArgs(BaseModel):
    title: str = Field(description="A short title for the notification")
    message: str = Field(description="A message to be displayed to the user")
    url: str | None = Field(
        description=(
            "This URL will be passed directly to the device client. By default "
            "links back to the thread."
        )
    )
    url_title: str | None = Field(
        description="A title for the URL to be displayed to the user"
    )
    sound: str | None = Field(
        description=(
            "The name of a sound to be played when the notification is received. "
            "Options: pushover (default), cosmic, incoming, pianobar, spacealarm, "
            "persistent (long), vibrate, none (silent)"
        ),
        default="pushover",
    )


class SendNotificationTool(BaseTool):
    name: str = "send_notification"
    description: str = (
        "Immediately send a notification to the Isaac's phone using Pushover."
    )

    args_schema: type[SendNotificationToolArgs] = SendNotificationToolArgs

    def _run(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(  # noqa: PLR0913
        self,
        title: str,
        message: str,
        config: RunnableConfig,
        url: str | None = None,
        url_title: str | None = None,
        sound: str | None = None,
    ) -> str:
        async with (
            aiohttp.ClientSession() as session,
            session.post(
                "https://api.pushover.net/1/messages.json",
                json={
                    "token": neuron_config.pushover.token,
                    "user": neuron_config.pushover.user,
                    "title": title,
                    "message": message,
                    "timestamp": int(time.time()),
                    "url": url
                    or f"https://neuron.zaks.io/thread/{config['configurable']['thread_id']}",
                    "url_title": url_title,
                    "sound": sound,
                },
            ) as response,
        ):
            response.raise_for_status()
            return "Message sent"
