from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
from neuron_server.config import config as neuron_config
import time
import aiohttp
import asyncio
from langchain_core.runnables import RunnableConfig


class SendNotificationToolArgs(BaseModel):
    title: str = Field(description="A short title for the notification")
    message: str = Field(description="A message to be displayed to the user")
    url: Optional[str] = Field(
        description="This URL will be passed directly to the device client. By default links back to the thread."
    )
    url_title: Optional[str] = Field(
        description="A title for the URL to be displayed to the user"
    )
    sound: Optional[str] = Field(
        description="""The name of a sound to be played when the notification is received. Use one of the following:
pushover - Pushover (default)
cosmic - Cosmic
incoming - Incoming
pianobar - Piano Bar
spacealarm - Space Alarm
persistent - Persistent (long)
vibrate - Vibrate Only
none - None (silent)
        """.strip(),
        default="pushover",
    )


class SendNotificationTool(BaseTool):
    name: str = "send_notification"
    description: str = (
        """
Immediately send a notification to the Isaac's phone using Pushover.
""".strip()
    )

    args_schema: Type[SendNotificationToolArgs] = SendNotificationToolArgs

    def _run(self, *args, **kwargs):
        return asyncio.run(self._arun(*args, **kwargs))

    async def _arun(
        self,
        title: str,
        message: str,
        config: RunnableConfig,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
        sound: Optional[str] = None,
    ) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.post(
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
            ) as response:
                response.raise_for_status()
                return "Message sent"
