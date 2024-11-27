from dotenv import load_dotenv


# Load environment variables from a .env file
load_dotenv()


import sys
import warnings
import logging

logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)


import asyncio
from neuron_server.api import app
from neuron_server.config import config
from neuron_server.logger import logger
from neuron_server.database import create_tables, pool
from hypercorn.config import Config
from hypercorn.asyncio import serve


async def start_database():
    logger.debug("Starting database")
    await create_tables()
    logger.info("Database started")


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    logger.debug("Starting server...")
    asyncio.run(start_database())

    if config.debug:
        app.run(
            debug=config.debug, host=config.host, port=config.port, use_reloader=False
        )
    else:
        hypercorn_config = Config()
        hypercorn_config.bind = [f"{config.host}:{config.port}"]
        asyncio.run(serve(app, hypercorn_config))
