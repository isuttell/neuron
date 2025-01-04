from typing import Literal
from neuron_server.event_router import OutgoingEvent


class SidebarImageEvent(OutgoingEvent):
    type: Literal["sidebar_image"] = "sidebar_image"
    url: str
