from quart import Blueprint, request, Response
from neuron_server.logger import logger
from uuid import UUID
from neuron_server.llms.tools import homeassistant_tools
from neuron_server.llms.agent import execute_agent
from pydantic import BaseModel
from typing import Optional
from neuron_server.models.thread_model import ThreadModel
from neuron_server.llms.agent import aget_state

blueprint = Blueprint(
    "webhooks",
    __name__,
)


class UpdateThreadRequest(BaseModel):
    thread_id: Optional[UUID]
    personality_id: UUID


@blueprint.post("/check_front_door")
async def check_front_door():
    body = await request.get_json()
    if not body:
        return Response({"status": "error", "message": "No body provided"}, status=400)
    payload = UpdateThreadRequest(**body)
    content = await execute_agent(
        "What is happening at the front door? If you see a package, a person, or otherwise anything unusual, send a notification to the user otherwise do nothing. Include a link to the image showing what you are seeing.",
        config={
            "run_name": "check_front_door",
            "configurable": {"thread_id": str(payload.thread_id)},
        },
        personality_id=payload.personality_id,
        tools=homeassistant_tools,
    )
    logger.info(f"check_front_door={content}")
    return {"status": "success", "content": content}


@blueprint.post("/home_status")
async def home_status():
    body = await request.get_json()
    if not body:
        return Response({"status": "error", "message": "No body provided"}, status=400)
    payload = UpdateThreadRequest(**body)
    content = await execute_agent(
        "What is the complete status of the home right now? If there is any unusual activity or anything like low cat food that needs to be addressed send short a notification letting the user know.",
        config={
            "run_name": "home_status",
            "configurable": {"thread_id": str(payload.thread_id)},
        },
        personality_id=payload.personality_id,
        tools=homeassistant_tools,
    )
    logger.info(f"home_status={content}")
    return {"status": "success", "content": content}


class PromptRequest(BaseModel):
    thread_id: Optional[UUID] = None
    run_name: Optional[str] = None
    prompt: str
    personality_id: UUID


@blueprint.post("/home_prompt")
async def prompt():
    body = await request.get_json()
    if not body:
        return Response({"status": "error", "message": "No body provided"}, status=400)
    payload = PromptRequest(**body)
    thread = await ThreadModel.get(id=payload.thread_id)
    if not thread:
        return Response({"status": "error", "message": "Thread not found"}, status=404)
    thread.status = "thinking"
    await thread.save()
    try:
        content = await execute_agent(
            prompt=payload.prompt,
            config={
                "run_name": payload.run_name or "home_prompt",
                "configurable": {"thread_id": str(thread.id)},
            },
            personality_id=payload.personality_id,
            tools=homeassistant_tools,
        )
        logger.info(f"home_prompt={content}")
        return {"status": "success", "content": content}
    finally:
        state = await aget_state(thread_id=payload.thread_id)
        thread.message_count = len(state.values.get("messages", []))
        thread.status = "idle"
        await thread.save()
