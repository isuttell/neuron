from collections.abc import Sequence

from pydantic import BaseModel
from quart import Blueprint, Response
from werkzeug.exceptions import NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.models.embedding_model import EmbeddingModel
from neuron_server.type_defs.request_proxy import request
from neuron_server.vectorstores import memories_store

blueprint = Blueprint("embedding", __name__)


class BulkDeleteEmbeddings(BaseModel):
    embedding_ids: list[str]


class EmbeddingUpsert(BaseModel):
    content: str
    metadata: dict[str, str | int | float | bool | dict | Sequence | None] | None = None


@blueprint.post("/<string:embedding_id>")
@requires_auth
@requires_csrf
async def upsert_embedding(embedding_id: str) -> dict[str, list[dict]]:
    """Upsert an embedding by ID.

    If the embedding exists, it will be deleted and recreated with new content
    while preserving metadata. If it doesn't exist, a new embedding will be created.

    Returns:
        Response: 200 OK with the updated/created embedding
    """
    body = await request.get_json()
    payload = EmbeddingUpsert(**body)

    # Get existing embedding if it exists
    existing_metadata = {}
    existing_embedding = await EmbeddingModel.get(embedding_id=embedding_id)
    if existing_embedding:
        # Preserve existing metadata
        existing_metadata = existing_embedding.cmetadata or {}

    # Merge existing metadata with any new metadata
    merged_metadata = {**existing_metadata, **(payload.metadata or {})}

    # Add document to vector store to generate embeddings
    await memories_store.aadd_texts(
        texts=[payload.content], metadatas=[merged_metadata], ids=[embedding_id]
    )

    embedding = await EmbeddingModel.get(embedding_id=embedding_id)

    return {
        "embeddings": [embedding.model_dump(exclude={"embedding"})],
    }


@blueprint.delete("/<string:embedding_id>")
@requires_auth
@requires_csrf
async def delete_embedding(embedding_id: str) -> Response:
    embedding = await EmbeddingModel.get(embedding_id=embedding_id)
    if not embedding:
        raise NotFound("Embedding not found")

    await EmbeddingModel.delete(embedding_id=embedding_id)
    return Response(status=204)


@requires_auth
@requires_csrf
@blueprint.delete("/bulk")
async def bulk_delete_embeddings() -> Response:
    """Delete multiple embeddings at once.

    Returns:
        Response: 204 No Content on success
    """
    body = await request.get_json()
    payload = BulkDeleteEmbeddings(**body)

    # Get existing embeddings to verify they exist
    existing_embeddings = await EmbeddingModel.get_many(ids=payload.embedding_ids)
    existing_ids = {e.id for e in existing_embeddings}

    # Check if any requested embeddings don't exist
    missing_ids = set(payload.embedding_ids) - existing_ids
    if missing_ids:
        raise NotFound(f"Embeddings not found: {', '.join(missing_ids)}")

    # Delete all embeddings
    await EmbeddingModel.delete_many(ids=payload.embedding_ids)
    return Response(status=204)
