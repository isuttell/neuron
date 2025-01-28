from typing import Literal

from neuron_server.event_router import IncomingEvent, OutgoingEvent
from neuron_server.models.provider_model import ProviderModelModel


class GetProviders(IncomingEvent):
    pass


class GetProvidersResponse(OutgoingEvent):
    type: Literal["providers"] = "providers"
    providers: list[ProviderModelModel]
