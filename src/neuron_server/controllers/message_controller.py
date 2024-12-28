from quart import Blueprint
from neuron_server.event_router import EventRouter
from neuron_server.models import ThreadModel
from neuron_server.controllers.events.message_events import (
    PostMessage,
    CancelMessage,
)
from neuron_server.controllers.events.message_events import (
    ThreadMessage,
)
from uuid import UUID
from neuron_server.llms.agent import aget_state
from werkzeug.exceptions import NotFound
import neuron_server.llms.agent as agent
from neuron_server.pubsub import pubsub

router = EventRouter()

blueprint = Blueprint("message", __name__)


@blueprint.get("/thread/<uuid:thread_id>")
async def get_thread_messages(thread_id: UUID):
    thread = await ThreadModel.get(thread_id)
    if not thread:
        raise NotFound("Thread not found")

    state = await aget_state(thread_id=thread.id)
    messages = [
        ThreadMessage(**message.model_dump(), thread_id=thread.id)
        for message in (state.values.get("messages", []))
        if message.type != "system"
    ]
    return {
        "messages": [message.model_dump() for message in messages],
    }


@router.on(PostMessage)
async def apost_message(event: PostMessage) -> None:
    await agent.astream(event.thread_id, event.personality_id, event.prompt)


@router.on(CancelMessage)
async def acancel_message(event: CancelMessage) -> None:
    await pubsub.publish(
        "cancel",
        event.thread_id,
    )
