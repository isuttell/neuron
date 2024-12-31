from quart import Quart, websocket, send_from_directory, Blueprint
from neuron_server.logger import logger
import json
from neuron_server.config import config
from neuron_server.event_router import EventRouter, ErrorEvent
from neuron_server.controllers.thread_controller import (
    router as thread_router,
    blueprint as thread_blueprint,
)
from neuron_server.controllers.message_controller import (
    router as message_router,
    blueprint as message_blueprint,
)
from neuron_server.controllers.personality_controller import (
    router as personality_router,
    blueprint as personality_blueprint,
)
from neuron_server.controllers.image_controller import (
    router as image_router,
    blueprint as image_blueprint,
)
from neuron_server.controllers.webhook_controller import blueprint as webhook_blueprint
from neuron_server.controllers.graph_controller import (
    blueprint as graph_blueprint,
)
from functools import wraps
from quart import Response
from typing import Optional
import asyncio
from neuron_server.database import pool
from neuron_server.pubsub import client
import re
import os
from PIL import Image


router = EventRouter()

router.register_controller(thread_router)
router.register_controller(message_router)
router.register_controller(personality_router)
router.register_controller(image_router)


app = Quart(
    __name__,
    static_url_path="/",
    static_folder=config.client_assets_folder,
    root_path="/",
)


def cors(
    allowed_origins: list[str] = ["*"],
    allowed_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowed_headers: list[str] = ["Content-Type", "Authorization"],
):
    def add_cors_headers(func):
        func.required_methods = getattr(func, "required_methods", set())  # type: ignore
        func.required_methods.add("OPTIONS")  # type: ignore
        func.provide_automatic_options = False  # type: ignore

        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            response: Response = await func(*args, **kwargs)
            response.headers["Access-Control-Allow-Origin"] = ", ".join(allowed_origins)
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                allowed_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ", ".join(
                allowed_headers
            )
            return response

        return wrapped_func

    return add_cors_headers


def cache_control(
    max_age: Optional[int] = None,
    no_cache: bool = False,
    private: bool = False,
    public: bool = False,
    immutable: bool = False,
):
    def add_headers(func):
        @wraps(func)
        async def wrapped_func(*args, **kwargs):
            response: Response = await func(*args, **kwargs)
            values = []

            if isinstance(max_age, int):
                values.append(f"max-age={max_age}")
            elif no_cache:
                values.append("no-cache")

            if private:
                values.append("private")
            elif public:
                values.append("public")

            if immutable:
                values.append("immutable")

            if values:
                response.headers["Cache-Control"] = ", ".join(values)
            return response

        return wrapped_func

    return add_headers


blueprint = Blueprint(
    "neuron",
    __name__,
    static_url_path="/",
    static_folder=config.client_assets_folder,
)


@blueprint.get("/")
@blueprint.get("/thread/<thread_id>")
@blueprint.get("/personalities")
@blueprint.get("/personality/<personality_id>")
@blueprint.get("/gallery")
@blueprint.get("/code-viewer")
@blueprint.get("/stats")
async def index(**kwargs):
    return await blueprint.send_static_file("index.html")


# Assets don't change so we can cache them for a long time
@blueprint.get("/static/<path:path>")
@blueprint.get("/neuron/static/<path:path>")
@cors(allowed_methods=["GET", "OPTIONS"], allowed_headers=["Authorization"])
@cache_control(max_age=31536000, immutable=True)
async def get_static(path):
    match = re.match(r".*_(t|l|xl)\.(jpe?g|png)$", path)
    if (
        match
        and not os.path.exists(os.path.join(config.static_folder, path))
        and os.path.exists(
            os.path.join(config.static_folder, path.replace(f"_{match.group(1)}.", "."))
        )
    ):
        image = Image.open(
            os.path.join(config.static_folder, path.replace(f"_{match.group(1)}.", "."))
        )
        size = {"t": 512, "l": 768, "xl": 1024}.get(match.group(1), 512)
        image.thumbnail((size, size))
        image.save(os.path.join(config.static_folder, path), quality=85)
    return await send_from_directory(config.static_folder, path, as_attachment=True)


async def sending():
    async with client.pubsub() as pubsub:
        await pubsub.subscribe("app")
        while True:
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=None
            )
            if message is not None:
                await websocket.send(message["data"].decode("utf-8"))


async def receiving():
    while True:
        try:
            data = await websocket.receive()
            body = json.loads(data)
            await router.dispatch(body)
        except Exception as e:
            logger.exception(e)


@blueprint.websocket("/ws")
async def ws():
    producer = asyncio.create_task(sending())
    consumer = asyncio.create_task(receiving())
    await asyncio.gather(producer, consumer)


@app.get("/status")
async def health():
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


@app.errorhandler(404)
async def not_found_error(error):
    return {"error": "Not Found", "message": str(error)}, 404


@app.errorhandler(500)
async def internal_error(error):
    return {"error": "Internal Server Error", "message": str(error)}, 500


@app.errorhandler(400)
async def bad_request_error(error):
    return {"error": "Bad Request", "message": str(error)}, 400


@app.errorhandler(403)
async def forbidden_error(error):
    return {"error": "Forbidden", "message": str(error)}, 403
