from uuid import UUID

from quart import Blueprint, request
from werkzeug.exceptions import Forbidden

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.models.provider_model import ProviderModelModel

provider_blueprint = Blueprint("provider", __name__)


@provider_blueprint.get("/")
@requires_auth
async def list_providers() -> dict[str, list[dict] | UUID | None]:
    """Get all available providers and the active provider ID"""
    if "admin" not in request.token.roles:
        raise Forbidden("Admin access required")

    providers = await ProviderModelModel.list()
    active_provider_id = await ProviderModelModel.get_active_provider_id()

    return {
        "providers": [provider.model_dump() for provider in providers],
        "active_provider_id": active_provider_id,
    }


@provider_blueprint.post("/<uuid:provider_id>/activate")
@requires_auth
@requires_csrf
async def activate_provider(provider_id: UUID) -> dict[str, str | UUID]:
    """Activate a specific provider"""
    if "admin" not in request.token.roles:
        raise Forbidden("Admin access required")
    await ProviderModelModel.setup(provider_id=provider_id)
    return {
        "message": "Provider activated successfully",
        "active_provider_id": provider_id,
    }
