from langchain_postgres import PGVector
from langchain_postgres.vectorstores import PGVector
from langchain_openai import OpenAIEmbeddings
from neuron_server.database import engine

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

memories_store = PGVector(
    embeddings=embeddings,
    collection_name="memories",
    connection=engine,
    use_jsonb=True,
)

arxiv_store = PGVector(
    embeddings=embeddings,
    collection_name="arxiv",
    connection=engine,
    use_jsonb=True,
)
