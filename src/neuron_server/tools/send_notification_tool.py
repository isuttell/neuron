from langchain.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field
import requests
from neuron_server.config import config
import time


class SendNotificationToolArgs(BaseModel):
    title: str = Field(description="A short title for the notification")
    message: str = Field(description="A message to be displayed to the user")
    url: Optional[str] = Field(
        description="This URL will be passed directly to the device client, with a URL title of the supplied title (defaulting to the URL itself if no title given). Supplementary URLs can be useful for presenting long URLs in a notification as well as interacting with 3rd party applications. "
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
Send a notification to the user's phone.
""".strip()
    )

    args_schema: Type[SendNotificationToolArgs] = SendNotificationToolArgs

    def _run(
        self,
        title: str,
        message: str,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
        sound: Optional[str] = None,
    ) -> str:
        response = requests.post(
            "https://api.pushover.net/1/messages.json",
            json={
                "token": config.pushover.token,
                "user": config.pushover.user,
                "title": title,
                "message": message,
                "timestamp": int(time.time()),
                "url": url,
                "url_title": url_title,
                "sound": sound,
            },
        )
        response.raise_for_status()
        return "Message sent"
