from dotenv import load_dotenv


# Load environment variables from a .env file
load_dotenv()


import asyncio
import sys
import warnings
import logging

logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=FutureWarning, message=".*stop_sequences.*")

from neuron_server.api import app
from neuron_server.config import config
from neuron_server.logger import logger
from neuron_server.database import create_tables


async def start_database():
    logger.info(f"Initializing database")
    await create_tables()


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":

    asyncio.run(start_database())

    logger.info(f"Starting server on {config.host}:{config.port}")
    app.run(debug=config.debug, host=config.host, port=config.port, use_reloader=False)
