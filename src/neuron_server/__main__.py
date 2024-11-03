from dotenv import load_dotenv


# Load environment variables from a .env file
load_dotenv()

from neuron_server.api import app
from neuron_server.config import config
from neuron_server.logger import logger
import warnings


warnings.filterwarnings("ignore", category=FutureWarning, message=".*stop_sequences.*")


if __name__ == "__main__":
    logger.info(f"Starting server on {config.host}:{config.port}")
    app.run(debug=config.debug, host=config.host, port=config.port, use_reloader=False)
