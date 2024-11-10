from typing import Literal, List
from neuron_server.event_router import OutgoingEvent, IncomingEvent
from neuron_server.models.provider_model import ProviderModelModel


class GetProviders(IncomingEvent):
    pass


class GetProvidersResponse(OutgoingEvent):
    type: Literal["providers"] = "providers"
    providers: List[ProviderModelModel]
