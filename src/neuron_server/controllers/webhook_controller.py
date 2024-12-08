from quart import Blueprint, request
from neuron_server.logger import logger
from uuid import UUID
from neuron_server.llms.agent import execute_agent
from pydantic import BaseModel
from typing import Optional
from werkzeug.exceptions import BadRequest

blueprint = Blueprint(
    "webhooks",
    __name__,
)


class PromptRequest(BaseModel):
    run_name: Optional[str] = None
    prompt: str
    personality_id: UUID


@blueprint.post("/home_prompt")
async def prompt():
    body = await request.get_json()
    if not body:
        raise BadRequest("No body provided")
    payload = PromptRequest(**body)
    logger.info(f"home_prompt.prompt={payload.prompt}")
    content = await execute_agent(
        prompt=payload.prompt
        + "\n\nDo not ask for confirmation before responding or ask any follow questions. This is an automated request.",
        personality_id=payload.personality_id,
    )
    logger.info(f"home_prompt.response={content}")
    return {"status": "success", "content": content}
