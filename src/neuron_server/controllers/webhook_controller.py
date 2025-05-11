from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint, request
from werkzeug.exceptions import BadRequest

from neuron_server.controllers.auth import requires_api_key, requires_auth
from neuron_server.llms.agent import execute_agent
from neuron_server.logger import logger
from neuron_server.tools.code_interpreter_api import run_code_interpreter

blueprint = Blueprint("webhooks", __name__)


class PromptRequest(BaseModel):
    run_name: str | None = None
    prompt: str
    personality_id: UUID


@blueprint.post("/prompt")
@blueprint.post("/home_prompt")
@requires_api_key
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
    )
    logger.info(f"prompt.response={content}")
    return {"status": "success", "content": content}


class CodeInterpreterRequest(BaseModel):
    python_code: str


@blueprint.post("/code-interpreter")
@requires_auth
async def code_interpreter() -> dict[str, str]:
    body = await request.get_json()
    if not body:
        raise BadRequest("Request body is required")

    payload = CodeInterpreterRequest(**body)
    status = "success"
    content = ""
    try:
        content, _ = await run_code_interpreter(
            python_code=payload.python_code,
        )
    except Exception as e:
        status = "error"
        content = str(e)
    logger.info(f"code_interpreter.response={content}")
    return {"status": status, "content": content}
