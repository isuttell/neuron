from pydantic import BaseModel
from quart import Blueprint
from werkzeug.exceptions import BadRequest

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.tools.graph_arxiv_import_tool import GraphArxivImportTool
from neuron_server.tools.graph_import_tool import GraphImportTool
from neuron_server.tools.graph_question_tool import GraphQuestionTool
from neuron_server.type_defs.request_proxy import request

blueprint = Blueprint("graph", __name__)


class QuestionRequest(BaseModel):
    question: str


@blueprint.post("/arxiv/<arxiv_id>")
@requires_auth
@requires_csrf
async def post_arxiv_import(arxiv_id: str) -> dict[str, str]:
    tool = GraphArxivImportTool()
    results = await tool.ainvoke({"arxiv_id": arxiv_id})
    return {"message": results}


@blueprint.post("/pdf")
@requires_auth
@requires_csrf
async def post_upload_pdf() -> dict[str, str]:
    files = await request.files
    form = await request.form

    if "file" not in files:
        raise BadRequest("No file provided")

    file = files["file"]
    if not file.filename:
        raise BadRequest("No filename provided")

    if not file.filename.endswith(".pdf"):
        raise BadRequest("File must be a PDF")

    tool = GraphImportTool()
    results = await tool.ainvoke(
        {
            "file": file,
            "filename": file.filename,
            "title": form.get("title", file.filename),
            "description": form.get("description", ""),
        }
    )

    return {"message": results}


@blueprint.post("/doc")
@requires_auth
@requires_csrf
async def post_upload_doc() -> dict[str, str]:
    files = await request.files
    form = await request.form

    if "file" not in files:
        raise BadRequest("No file provided")

    file = files["file"]
    if not file.filename:
        raise BadRequest("No filename provided")

    if not file.filename.endswith((".doc", ".docx")):
        raise BadRequest("File must be a DOC or DOCX")

    tool = GraphImportTool()
    results = await tool.ainvoke(
        {
            "file": file,
            "filename": file.filename,
            "title": form.get("title", file.filename),
            "description": form.get("description", ""),
        }
    )

    return {"message": results}


@blueprint.post("/question")
@requires_auth
@requires_csrf
async def post_question() -> dict[str, str]:
    body = await request.get_json()
    payload = QuestionRequest(**body)

    tool = GraphQuestionTool()
    results = await tool.ainvoke({"question": payload.question})

    return {"message": results}
