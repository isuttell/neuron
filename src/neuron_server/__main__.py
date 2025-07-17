import argparse
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
from neuron_server.migrations import run_migrations

register_heif_opener()


async def init() -> None:
    start_time = time.perf_counter()
    logger.debug("Starting database...")
    await start()
    logger.debug(f"Database started in {time.perf_counter() - start_time:.2f} seconds")


async def migrate() -> None:
    """Run database migrations and exit."""
    logger.info("Running database migrations...")
    start_time = time.perf_counter()
    await run_migrations()
    elapsed_time = time.perf_counter() - start_time
    logger.info(f"Database migrations completed in {elapsed_time:.2f} seconds")


if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Neuron Server")
    parser.add_argument(
        "--migration",
        action="store_true",
        help="Run database migrations and exit"
    )
    args = parser.parse_args()

    if args.migration:
        asyncio.run(migrate())
    else:
        asyncio.run(init())

        if config.debug:
            app.run(
                debug=config.debug,
                host=config.host,
                port=config.port,
                use_reloader=False
            )
        else:
            hypercorn_config = Config()
            hypercorn_config.bind = [f"{config.host}:{config.port}"]
            asyncio.run(serve(app, hypercorn_config))
