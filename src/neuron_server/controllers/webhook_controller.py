from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint
from werkzeug.exceptions import BadRequest

from neuron_server.controllers.auth import requires_api_key
from neuron_server.decorators import rate_limit
from neuron_server.llms.agent import execute_agent
from neuron_server.logger import logger
from neuron_server.type_defs.request_proxy import request

blueprint = Blueprint("webhooks", __name__)


class PromptRequest(BaseModel):
    run_name: str | None = None
    prompt: str
    personality_id: UUID


@blueprint.post("/prompt")
@blueprint.post("/home_prompt")
@requires_api_key
@rate_limit()
async def prompt() -> dict[str, str]:
    body = await request.get_json()
    if not body:
        raise BadRequest("Request body is required")

    payload = PromptRequest(**body)
    logger.info(f"prompt.prompt={payload.prompt}")
    content = await execute_agent(
        prompt=payload.prompt
        + (
            "\n\nDo not ask for confirmation before responding or ask any "
            "follow questions. This is an automated request."
        ),
        personality_id=payload.personality_id,
        user_id="auth0|677842260dc433462eaf13a6",
        username="Isaac",
    )
    logger.info(f"prompt.response={content}")
    return {"status": "success", "content": content}
