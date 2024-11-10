from quart import websocket
from neuron_server.event_router import EventRouter
from neuron_server.controllers.events.provider_events import (
    GetProviders,
    GetProvidersResponse,
)
from neuron_server.models.provider_model import ProviderModelModel

router = EventRouter()


@router.on(GetProviders)
async def get_providers(event: GetProviders):
    providers = await ProviderModelModel.list()
    await websocket.send(GetProvidersResponse(providers=providers).model_dump_json())
