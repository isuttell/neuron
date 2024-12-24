import logging
from neuron_server.config import config

logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("langchain_core.vectorstores.base").setLevel(logging.ERROR)


logging.basicConfig(level=logging.INFO, encoding="utf-8")

logger = logging.getLogger(__name__)

log_level = getattr(logging, config.log_level.upper(), logging.INFO)

logger.setLevel(log_level)

logging.getLogger("asyncio").setLevel(logging.ERROR)
