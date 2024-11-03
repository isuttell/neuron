import sqlite3
from neuron_server.config import config

database = sqlite3.connect(config.database_path)
