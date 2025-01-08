from typing import Literal
from neuron_server.event_router import OutgoingEvent
from neuron_server.models.prompt_model import PromptModel


class GetPromptResponse(OutgoingEvent):
    type: Literal["prompt"] = "prompt"
    prompt: PromptModel
