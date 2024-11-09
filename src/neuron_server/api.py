from quart import Quart, websocket, send_from_directory
from neuron_server.logger import logger
import json
from neuron_server.config import config
from neuron_server.event_router import EventRouter, ErrorEvent
from neuron_server.controllers.thread_controller import router as thread_router
from neuron_server.controllers.message_controller import router as message_router
from neuron_server.controllers.personality_controller import router as user_router
from neuron_server.controllers.image_controller import router as image_router
from neuron_server.controllers.provider_controller import router as provider_router
from neuron_server.controllers.stats_controller import router as stats_router
from neuron_server.database import engine
from typing import Optional
from functools import wraps
from quart import Response


router = EventRouter()

router.register_controller(thread_router)
router.register_controller(message_router)
router.register_controller(user_router)
router.register_controller(image_router)
router.register_controller(provider_router)
router.register_controller(stats_router)
app = Quart(__name__, static_url_path="/", static_folder=config.client_assets_folder)


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


@app.get("/")
@app.get("/thread/<thread_id>")
@app.get("/personalities")
@app.get("/personality/<personality_id>")
@app.get("/image")
@app.get("/gallery")
@app.get("/stats")
async def index(**kwargs):
    return await app.send_static_file("index.html")


# Assets don't change so we can cache them for a long time
@app.get("/static/<path:path>")
@cors(allowed_methods=["GET", "OPTIONS"], allowed_headers=["Authorization"])
@cache_control(max_age=31536000, immutable=True)
async def get_static(path):
    return await send_from_directory(config.static_folder, path)


@app.websocket("/ws")
async def ws():
    while True:
        try:
            data = await websocket.receive()
            body = json.loads(data)
            await router.dispatch(body)
        except Exception as e:
            logger.exception(e)
