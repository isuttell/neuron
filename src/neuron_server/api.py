from quart import Quart, websocket, send_from_directory, Blueprint
from neuron_server.logger import logger
import json
from neuron_server.config import config
from neuron_server.event_router import EventRouter, ErrorEvent
from neuron_server.controllers.thread_controller import (
    router as thread_router,
    blueprint as thread_blueprint,
)
from neuron_server.controllers.message_controller import router as message_router
from neuron_server.controllers.personality_controller import router as user_router
from neuron_server.controllers.image_controller import router as image_router
from neuron_server.controllers.provider_controller import router as provider_router
from neuron_server.controllers.stats_controller import router as stats_router
from neuron_server.controllers.webhook_controller import blueprint as webhook_blueprint
from functools import wraps
from quart import Response
from uuid import UUID
from neuron_server.llms.tools import homeassistant_tools
from neuron_server.llms.agent import execute_agent
from typing import Optional

from neuron_server.database import DB_URI

router = EventRouter()

router.register_controller(thread_router)
router.register_controller(message_router)
router.register_controller(user_router)
router.register_controller(image_router)
router.register_controller(provider_router)
router.register_controller(stats_router)


app = Quart(
    __name__,
    static_url_path="/",
    static_folder=config.client_assets_folder,
    root_path="/",
)

app.register_blueprint(thread_blueprint, url_prefix="/api/threads")


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
@blueprint.get("/image")
@blueprint.get("/gallery")
@blueprint.get("/stats")
async def index(**kwargs):
    return await blueprint.send_static_file("index.html")


# Assets don't change so we can cache them for a long time
@blueprint.get("/static/<path:path>")
@cors(allowed_methods=["GET", "OPTIONS"], allowed_headers=["Authorization"])
@cache_control(max_age=31536000, immutable=True)
async def get_static(path):
    return await send_from_directory(config.static_folder, path)


@blueprint.websocket("/ws")
async def ws():
    while True:
        try:
            data = await websocket.receive()
            body = json.loads(data)
            await router.dispatch(body)
        except Exception as e:
            logger.exception(e)


@app.get("/")
async def health():
    return {"server": "neuron", "status": "healthy"}


app.register_blueprint(blueprint, url_prefix="/neuron")
app.register_blueprint(webhook_blueprint, url_prefix="/neuron/webhooks")
