from dotenv import load_dotenv


# Load environment variables from a .env file
load_dotenv()


import sys


import asyncio
from neuron_server.api import app
from neuron_server.config import config
from neuron_server.logger import logger
from neuron_server.database import start
from neuron_server.models.provider_model import ProviderModelModel
from hypercorn.config import Config
from hypercorn.asyncio import serve
import time


async def start_database():
    start_time = time.perf_counter()
    logger.debug("Starting database...")
    await start()
    await ProviderModelModel.setup()
    logger.debug(f"Database started in {time.perf_counter() - start_time:.2f} seconds")


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    asyncio.run(start_database())

    if config.debug:
        app.run(
            debug=config.debug, host=config.host, port=config.port, use_reloader=False
        )
    else:
        hypercorn_config = Config()
        hypercorn_config.bind = [f"{config.host}:{config.port}"]
        asyncio.run(serve(app, hypercorn_config))
