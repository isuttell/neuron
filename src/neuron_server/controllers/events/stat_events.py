from typing import Literal

from neuron_server.event_router import IncomingEvent, OutgoingEvent


class GetTokenStats(IncomingEvent):
    pass


class TokenStatsResponse(OutgoingEvent):
    type: Literal["token_stats"] = "token_stats"
    input_tokens: int
    output_tokens: int
