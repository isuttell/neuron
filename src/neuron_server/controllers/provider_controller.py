from quart import Blueprint, request
from typing import List
from uuid import UUID
from neuron_server.models.provider_model import ProviderModelModel
from neuron_server.controllers.auth import requires_auth
from werkzeug.exceptions import NotFound, Forbidden

provider_blueprint = Blueprint("provider", __name__)


@provider_blueprint.get("/")
@requires_auth
async def list_providers() -> dict:
    """Get all available providers and the active provider ID"""
    if "admin" not in request.token.roles:
        raise Forbidden("Admin access required")

    providers = await ProviderModelModel.list()
    active_provider_id = await ProviderModelModel.get_active_provider_id()

    return {
        "providers": [provider.model_dump() for provider in providers],
        "active_provider_id": active_provider_id,
    }


@provider_blueprint.post("/<uuid:provider_id>/setup")
@requires_auth
async def setup_provider(provider_id: UUID):
    """Setup a specific provider as the active LLM"""

    if "admin" not in request.token.roles:
        raise Forbidden("Admin access required")

    provider = await ProviderModelModel.get(provider_id)
    if not provider:
        raise NotFound("Provider not found")

    await ProviderModelModel.setup(provider_id)
    return {"message": "Provider setup successfully"}
