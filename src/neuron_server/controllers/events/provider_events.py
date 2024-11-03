from typing import Literal, List
from neuron_server.event_router import OutgoingEvent, IncomingEvent
from neuron_server.models.provider_model import ProviderModel


class GetProviders(IncomingEvent):
    pass


class GetProvidersResponse(OutgoingEvent):
    type: Literal["providers"] = "providers"
    providers: List[ProviderModel]
