from quart import Blueprint, request, Response
from neuron_server.logger import logger
from uuid import UUID
from neuron_server.llms.tools import homeassistant_tools
from neuron_server.llms.agent import execute_agent
from pydantic import BaseModel
from typing import Optional
from neuron_server.models.thread_model import ThreadModel
import neuron_server.llms.agent as agent
from werkzeug.exceptions import NotFound, BadRequest
from neuron_server.pubsub import pubsub
from neuron_server.controllers.events.thread_events import (
    GetThreadResponse,
)

blueprint = Blueprint(
    "webhooks",
    __name__,
)


class PromptRequest(BaseModel):
    thread_id: Optional[UUID] = None
    run_name: Optional[str] = None
    prompt: str
    personality_id: UUID


@blueprint.post("/home_prompt")
async def prompt():
    body = await request.get_json()
    if not body:
        raise BadRequest
    payload = PromptRequest(**body)
    thread = await ThreadModel.get(id=payload.thread_id)
    if not thread:
        raise NotFound("Thread not found")
    thread.status = "thinking"
    await thread.save()
    await pubsub.publish("app", GetThreadResponse(thread=thread))

    try:
        content = await agent.astream(
            thread_id=thread.id,
            prompt=payload.prompt,
            personality_id=payload.personality_id,
        )
        logger.info(f"home_prompt={content}")
        return {"status": "success", "content": content}
    finally:
        state = await agent.aget_state(thread_id=payload.thread_id)
        thread.message_count = len(state.values.get("messages", []))
        thread.status = "idle"
        await thread.save()
        await pubsub.publish("app", GetThreadResponse(thread=thread))
