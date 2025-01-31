from langchain_postgres.vectorstores import PGVector

from neuron_server.config import config
from neuron_server.llms.embeddings import embeddings

connection = (
    f"postgresql+psycopg://{config.database.user}:{config.database.password}"
    f"@{config.database.host}:{config.database.port}/{config.database.database}"
)

vector_store = PGVector(
    embeddings=embeddings,
    collection_name="papers",
    connection=connection,
    use_jsonb=True,
)
