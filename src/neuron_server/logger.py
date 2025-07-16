import logging

from langchain.globals import set_debug

from neuron_server.config import config

logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("langchain_core.vectorstores.base").setLevel(logging.ERROR)
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("neuron_server.cache").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.INFO)
logging.getLogger("anthropic").setLevel(logging.INFO)
logging.getLogger("openai").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)
logging.getLogger("neo4j.notifications").setLevel(logging.ERROR)

log_level = getattr(logging, config.log_level.strip().upper(), logging.INFO)

logging.basicConfig(level=log_level, encoding="utf-8")

logger = logging.getLogger(__name__)


if config.llm_debug:
    logger.debug("Enabling langchain debug mode")
    set_debug(True)
