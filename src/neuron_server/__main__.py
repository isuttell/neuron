import asyncio
import sys
import time

from hypercorn.asyncio import serve
from hypercorn.config import Config
from pi_heif import register_heif_opener

from neuron_server.api import app
from neuron_server.config import config
from neuron_server.database import start
from neuron_server.logger import logger

register_heif_opener()


async def init() -> None:
    start_time = time.perf_counter()
    logger.debug("Starting database...")
    await start()
    logger.debug(f"Database started in {time.perf_counter() - start_time:.2f} seconds")


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    asyncio.run(init())

    if config.debug:
        app.run(
            debug=config.debug, host=config.host, port=config.port, use_reloader=False
        )
    else:
        hypercorn_config = Config()
        hypercorn_config.bind = [f"{config.host}:{config.port}"]
        asyncio.run(serve(app, hypercorn_config))
