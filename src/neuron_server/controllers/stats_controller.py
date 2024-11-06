from quart import websocket
from neuron_server.event_router import EventRouter
from neuron_server.logger import logger
from neuron_server.controllers.events.stat_events import (
    GetTokenStats,
    TokenStatsResponse,
)
from neuron_server.models.message_model import MessageModel

router = EventRouter()


@router.on(GetTokenStats)
async def get_token_counts(event: GetTokenStats):
    input_tokens, output_tokens = MessageModel.count_tokens()
    await websocket.send(
        TokenStatsResponse(
            input_tokens=input_tokens, output_tokens=output_tokens
        ).model_dump_json()
    )
