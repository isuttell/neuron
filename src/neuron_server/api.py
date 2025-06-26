import asyncio
import json
import logging
import os
import re
from typing import Any

import openai
from quart import Blueprint, Quart, Response, send_from_directory, websocket
from werkzeug.exceptions import HTTPException

from neuron_server.config import config
from neuron_server.controllers.app_controller import (
    blueprint as app_blueprint,
)
from neuron_server.controllers.auth import decode_token, requires_auth, requires_cookie
from neuron_server.controllers.csrf import create_session_cookie
from neuron_server.controllers.embedding_controller import (
    blueprint as embedding_blueprint,
)
from neuron_server.controllers.graph_controller import (
    blueprint as graph_blueprint,
)
from neuron_server.controllers.image_controller import (
    blueprint as image_blueprint,
)
from neuron_server.controllers.image_controller import (
    router as image_router,
)
from neuron_server.controllers.media_controller import blueprint as media_blueprint
from neuron_server.controllers.message_controller import (
    blueprint as message_blueprint,
)
from neuron_server.controllers.message_controller import (
    router as message_router,
)
from neuron_server.controllers.personality_controller import (
    blueprint as personality_blueprint,
)
from neuron_server.controllers.personality_controller import (
    router as personality_router,
)
from neuron_server.controllers.prompt_controller import (
    blueprint as prompt_blueprint,
)
from neuron_server.controllers.prompt_controller import (
    router as prompt_router,
)
from neuron_server.controllers.provider_controller import provider_blueprint
from neuron_server.controllers.scheduler_controller import (
    blueprint as scheduler_blueprint,
)
from neuron_server.controllers.thread_controller import (
    blueprint as thread_blueprint,
)
from neuron_server.controllers.thread_controller import (
    router as thread_router,
)
from neuron_server.controllers.user_controller import (
    user_bp,
)
from neuron_server.controllers.webhook_controller import blueprint as webhook_blueprint
from neuron_server.database import pool
from neuron_server.decorators.http_decorators import cache_control, cors, rate_limit
from neuron_server.event_router import EventRouter
from neuron_server.graph.connection import connection_manager
from neuron_server.pubsub import client
from neuron_server.task_scheduler import TaskScheduler
from neuron_server.type_defs.request import NeuronRequest
from neuron_server.util.image_utilities import create_thumbnails

logger = logging.getLogger(__name__)

router = EventRouter()

router.register_controller(thread_router)
router.register_controller(message_router)
router.register_controller(personality_router)
router.register_controller(image_router)
router.register_controller(prompt_router)

app = Quart(
    __name__,
    static_url_path="/" if config.serve_client else None,
    static_folder=config.client_assets_folder if config.serve_client else None,
    root_path="/",
)
app.request_class = NeuronRequest


@app.before_request
async def fix_scheme() -> None:
    """Fix scheme detection when behind reverse proxy.

    Ensures that redirects use the correct protocol (https) when the app
    is deployed behind a reverse proxy that sets X-Forwarded-Proto header.
    Without this, redirects may incorrectly use http instead of https.
    """
    from quart import request

    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    if forwarded_proto == "https":
        request.scheme = "https"


blueprint = Blueprint(
    "neuron",
    __name__,
    static_url_path="/" if config.serve_client else None,
    static_folder=config.client_assets_folder if config.serve_client else None,
)


# Client routes - conditionally served based on config
if config.serve_client:

    @blueprint.get("/")
    @blueprint.get("/thread/<thread_id>")
    @blueprint.get("/personalities")
    @blueprint.get("/personality/<personality_id>")
    @blueprint.get("/personality/<personality_id>/embeddings")
    @blueprint.get("/gallery")
    @blueprint.get("/code-viewer")
    @blueprint.get("/stats")
    @blueprint.get("/prompts")
    @blueprint.get("/scheduled")
    @blueprint.get("/providers")
    @blueprint.get("/share/<list_id>")
    async def index(**kwargs: Any) -> Response:
        return await blueprint.send_static_file("index.html")

    # Assets don't change so we can cache them for a long time
    # Public route for logo without authentication
    @blueprint.get("/logo.svg")
    @cors(allowed_methods=["GET", "OPTIONS"])
    @cache_control(max_age=31536000)
    async def get_logo() -> Response:
        """Serve logo.svg without authentication requirement."""
        return await send_from_directory(config.client_assets_folder, "logo.svg")


@blueprint.get("/static/<path:path>")
@cors(allowed_methods=["GET", "OPTIONS"], allowed_headers=["Authorization"])
@cache_control(max_age=31536000)
@requires_cookie
@rate_limit(limit_type="static")
async def get_static(path: str) -> Response:
    match = re.match(r".*_(t|l|xl|xxl|o)\.(jpe?g|png|webp)$", path)
    if match and not os.path.exists(os.path.join(config.static_folder, path)):
        size_suffix = match.group(1)
        # Get the base path without size suffix and with original extension
        base_path = re.sub(f"_{size_suffix}\\.(jpe?g|png|webp)$", "", path)

        # Check for original file with various extensions
        for ext in [".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"]:
            original_file = os.path.join(config.static_folder, base_path + ext)
            if os.path.exists(original_file):
                create_thumbnails(original_file)
                break
    if not os.path.exists(os.path.join(config.static_folder, path)):
        logger.warning(f"File not found: {path}")
        return Response("File not found", 404)
    return await send_from_directory(config.static_folder, path)


async def sending() -> None:
    async with client.pubsub() as pubsub:
        await pubsub.subscribe("app")
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=None
            )
            if message is not None:
                await websocket.send(message["data"].decode("utf-8"))


async def receiving() -> None:
    while True:
        try:
            data = await websocket.receive()
            body = json.loads(data)
            await router.dispatch(body)
        except Exception as e:
            logger.error(e, exc_info=True)


@blueprint.websocket("/ws")
async def ws() -> None:
    # First message is the access token
    data = await websocket.receive()
    token = None
    try:
        # Verify the access token
        access_token = data.split("=")[-1]
        token = await decode_token(access_token)
        logger.info(f"Connected ({token.user_id})")
        # Start the producer and consumer
        producer = asyncio.create_task(sending())
        consumer = asyncio.create_task(receiving())
        await asyncio.gather(producer, consumer)
    except Exception as e:
        await websocket.close(401, str(e))
        logger.error(e)
    finally:
        if token:
            logger.info(f"Disconnected ({token.user_id})")


@app.get("/status")
async def health() -> dict[str, str]:
    await client.ping()
    await pool.check()
    return {"server": "neuron", "status": "healthy"}


app.register_blueprint(blueprint, url_prefix="/")
app.register_blueprint(webhook_blueprint, url_prefix="/api/webhooks")
app.register_blueprint(thread_blueprint, url_prefix="/api/threads")
app.register_blueprint(message_blueprint, url_prefix="/api/messages")
app.register_blueprint(personality_blueprint, url_prefix="/api/personalities")
app.register_blueprint(image_blueprint, url_prefix="/api/images")
app.register_blueprint(graph_blueprint, url_prefix="/api/graph")
app.register_blueprint(prompt_blueprint, url_prefix="/api/prompts")
app.register_blueprint(app_blueprint, url_prefix="/api/app")
app.register_blueprint(embedding_blueprint, url_prefix="/api/embeddings")
app.register_blueprint(media_blueprint, url_prefix="/api/media")
app.register_blueprint(scheduler_blueprint, url_prefix="/api/scheduler")
app.register_blueprint(provider_blueprint, url_prefix="/api/providers")
app.register_blueprint(user_bp, url_prefix="/api/users")


@app.route("/api/auth/refresh-csrf", methods=["POST"])
@requires_auth
async def refresh_csrf() -> tuple[dict[str, str], int]:
    """
    Refresh CSRF token endpoint.
    Used by the frontend when CSRF token becomes invalid.
    """
    from quart import jsonify

    from neuron_server.type_defs.request_proxy import request

    # Create new session cookie with CSRF token
    cookie_value, csrf_token = create_session_cookie(
        request.token.user_id, include_csrf=True
    )

    # Create response with new CSRF token
    response = jsonify({"status": "success", "csrf_token": csrf_token})

    # Set new session cookie
    response.set_cookie(
        "neuron_session",
        value=cookie_value,
        max_age=config.csrf_cookie_max_age,
        httponly=True,
        samesite="Lax",
        secure=config.is_production,
        path="/",  # Ensure cookie is sent with all requests
    )

    return response, 200


@app.errorhandler(openai.APIError)
async def openai_api_error(error: openai.APIError) -> tuple[dict[str, str], int]:
    logger.error(error, exc_info=True)
    if error.body:
        logger.error(error.body)
    return {"error": "API Error", "message": str(error)}, 400


@app.errorhandler(Exception)
async def internal_error(error: Exception) -> tuple[dict[str, str], int]:
    logger.error(error, exc_info=True)
    return {"error": "Internal Server Error", "message": str(error)}, 500


@app.errorhandler(HTTPException)
async def http_error(error: HTTPException) -> tuple[dict[str, str], int]:
    logger.error(error, exc_info=True)
    return {"error": error.name, "message": error.description}, error.code


scheduler = TaskScheduler(host=config.redis.host, port=config.redis.port, db=2)


@app.before_serving
async def startup() -> None:
    await scheduler.start()
    logger.debug("Task scheduler started")
    connection_manager.initialize()
    logger.debug("Neo4j initialized")


@app.after_serving
async def shutdown() -> None:
    connection_manager.cleanup()
    logger.info("Neo4j connection closed")

    # Clean up tools
    from neuron_server.llms.tools import cleanup

    await cleanup()
    logger.info("Tools cleaned up")
