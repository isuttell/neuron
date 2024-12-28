from quart import Blueprint, request
from neuron_server.event_router import EventRouter
from pydantic import BaseModel
from neuron_server.graph import question_graph, OutputState
from pydantic import BaseModel
from neuron_server.tools.graph_arxiv_import_tool import GraphArxivImportTool
from neuron_server.graph import process_document, get_document, encode_md5
import pymupdf4llm
from neuron_server.config import config as neuron_config
import os
from werkzeug.exceptions import BadRequest

router = EventRouter()


blueprint = Blueprint("graph", __name__)


@blueprint.post("/arxiv/<arxiv_id>")
async def post_arxiv_import(arxiv_id: str):
    tool = GraphArxivImportTool()
    return await tool.ainvoke({"arxiv_id": arxiv_id})


@blueprint.post("/pdf")
async def post_upload_pdf():
    files = await request.files
    form = await request.form
    file = files["file"]
    document_name = file.filename
    personality_id = form.get("personality_id")
    if not personality_id:
        raise BadRequest("Personality ID is required")
    filename = f"{encode_md5(document_name)}.pdf"
    tmp_file_path = os.path.abspath(os.path.join(neuron_config.temp_folder, filename))
    try:
        await file.save(tmp_file_path)

        # Convert the PDF to markdown text
        text = pymupdf4llm.to_markdown(tmp_file_path, show_progress=True).strip()

        document_id = f"pdf:{encode_md5(document_name)}"
        # Process the document and add it to the graph
        await process_document(
            text=text,
            document_id=document_id,
            document_name=document_name,
            config={
                "configurable": {
                    "personality_id": personality_id,
                }
            },
        )
        return "success"
    finally:
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)


class QuestionRequest(BaseModel):
    question: str


@blueprint.post("/question")
async def post_question():
    body = await request.get_json()
    payload = QuestionRequest(**body)
    response: OutputState = await question_graph.ainvoke({"question": payload.question})
    return {
        "answer": response.get("answer"),
    }
