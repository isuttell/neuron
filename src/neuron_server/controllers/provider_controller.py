from quart import websocket
from neuron_server.event_router import EventRouter
from neuron_server.controllers.events.provider_events import (
    GetProviders,
    GetProvidersResponse,
)
from neuron_server.llms.providers import providers

router = EventRouter()


@router.on(GetProviders)
async def get_providers(event: GetProviders):
    await websocket.send(GetProvidersResponse(providers=providers).model_dump_json())
