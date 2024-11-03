from quart import Quart, websocket, send_from_directory
from neuron_server.logger import logger
import json
from neuron_server.config import config
from neuron_server.models import PersonalityModel, ThreadModel, MessageModel, ImageModel
from neuron_server.event_router import EventRouter, ErrorEvent
from neuron_server.controllers.thread_controller import router as thread_router
from neuron_server.controllers.message_controller import router as message_router
from neuron_server.controllers.personality_controller import router as user_router
from neuron_server.controllers.image_controller import router as image_router
from neuron_server.controllers.provider_controller import router as provider_router

PersonalityModel.create_table_if_not_exists()
ThreadModel.create_table_if_not_exists()
MessageModel.create_table_if_not_exists()
ImageModel.create_table_if_not_exists()

router = EventRouter()

router.register_controller(thread_router)
router.register_controller(message_router)
router.register_controller(user_router)
router.register_controller(image_router)
router.register_controller(provider_router)
app = Quart(__name__, static_url_path="/", static_folder=config.client_assets_folder)


@app.get("/")
@app.get("/thread/<thread_id>")
@app.get("/personalities")
@app.get("/image")
@app.get("/gallery")
async def index(**kwargs):
    return await app.send_static_file("index.html")


@app.get("/static/<path:path>")
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
            await websocket.send(ErrorEvent(message=str(e)).model_dump_json())
