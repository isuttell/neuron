import logging
from neuron_server.config import config

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

log_level = getattr(logging, config.log_level.upper(), logging.INFO)

logger.setLevel(log_level)

logging.getLogger("asyncio").setLevel(logging.ERROR)
