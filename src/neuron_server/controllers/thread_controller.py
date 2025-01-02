from neuron_server.models import ThreadModel, PersonalityModel
from quart import Blueprint, request, Response
from neuron_server.event_router import EventRouter
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from neuron_server.llms.agent import astream
import asyncio
from werkzeug.exceptions import BadRequest
import hashlib
import os
import aiofiles
from neuron_server.config import config as neuron_config

router = EventRouter()
blueprint = Blueprint("thread", __name__)


@blueprint.get("/<uuid:thread_id>")
async def get_thread(thread_id: UUID):
    thread = await ThreadModel.get(thread_id)
    if not thread:
        raise ValueError("Thread not found")
    return {
        "thread": thread.model_dump(),
    }


@blueprint.get("/personality/<uuid:personality_id>")
async def get_threads(personality_id: UUID):
    threads = await ThreadModel.list(personality_id=personality_id)
    return {
        "threads": [thread.model_dump() for thread in threads],
    }


@blueprint.get("/recent")
async def get_recent_threads():
    threads = await ThreadModel.get_recent_threads(hours=24)
    personalities = await PersonalityModel.get_many(
        list(set(thread.personality_id for thread in threads))
    )
    return {
        "threads": [thread.model_dump() for thread in threads],
        "personalities": [personality.model_dump() for personality in personalities],
    }


class CreateThread(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None
    greeting: Optional[bool] = None
    prompt: Optional[str] = None
    personality_id: UUID


@blueprint.post("/")
async def post_create_thread():

    files = await request.files
    form = await request.form
    personality_id = form.get("personality_id")
    if not personality_id:
        raise BadRequest("personality_id is required")
    prompt = str(form.get("prompt", ""))
    greeting = str(form.get("greeting", "false")).lower() == "true"
    personality = await PersonalityModel.get(personality_id)
    if not personality:
        raise ValueError("Personality not found")

    if "file" in files:
        file = files["file"]
        ext = os.path.splitext(file.filename)[1]
        if ext not in neuron_config.allowed_file_types:
            raise BadRequest("Invalid file type")

        # Create hash of file contents
        hasher = hashlib.sha256()
        file_contents: bytes = file.read()
        assert isinstance(file_contents, bytes)
        if len(file_contents) > neuron_config.max_file_size:
            raise BadRequest("File too large")
        hasher.update(file_contents)
        content_hash = hasher.hexdigest()

        filename = f"{content_hash}{ext}"
        file_path = os.path.abspath(
            os.path.join(neuron_config.static_folder, "user", filename)
        )
        url = f"{neuron_config.static_content_url}/user/{filename}"

        # Only save if file doesn't already exist
        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(file_contents)

        prompt = f"<|AI|>The user has uploaded a file called '{file.filename}' to <{url}> as part the request<|AI|>\n{prompt}"

    thread = await ThreadModel.create(
        personality_id=personality.id,
        name=form.get("name"),
        context=form.get("context"),
    )

    if greeting:
        prompt = f"{prompt or ''}<|AI|>Start the conversation in a sentence or two and then provide some prompt suggestions as a list. Don't run any tools<|AI|>"

    if prompt:
        # Start the conversation and stream the response if we have any actions to take
        # don't wait for the response to finish before returning so that we can return
        # the thread immediately and stream the response in the background
        asyncio.create_task(
            astream(
                prompt=prompt,
                personality_id=personality.id,
                thread_id=thread.id,
                user_id=None,
            )
        )

    return {
        "thread": thread.model_dump(),
    }


@blueprint.delete("/<uuid:thread_id>")
async def delete_thread(thread_id: UUID):
    await ThreadModel.delete(thread_id)
    return Response(status=204)


class UpdateThread(BaseModel):
    name: Optional[str] = None
    context: Optional[str] = None


@blueprint.put("/<uuid:thread_id>")
async def update_thread(thread_id: UUID):
    body = await request.get_json()
    payload = UpdateThread(**body)
    thread = await ThreadModel.get(thread_id)
    if not thread:
        raise ValueError("Thread not found")
    thread.name = payload.name
    thread.context = payload.context
    await thread.save()
    return {
        "thread": thread.model_dump(),
    }
