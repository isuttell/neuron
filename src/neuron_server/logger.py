import logging
from neuron_server.config import config

logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("langchain_core.vectorstores.base").setLevel(logging.ERROR)
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("matplotlib").setLevel(logging.WARNING)
logging.getLogger("neo4j").setLevel(logging.WARNING)
logging.getLogger("neuron_server.cache").setLevel(logging.INFO)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.INFO)
logging.getLogger("openai").setLevel(logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("PIL").setLevel(logging.WARNING)

log_level = getattr(logging, config.log_level.upper(), logging.INFO)

logging.basicConfig(level=log_level, encoding="utf-8")

logger = logging.getLogger(__name__)
