from quart import Blueprint
from typing import Dict, Any
from neuron_server.controllers.auth import requires_auth
from neuron_server.cache import get_cache_key
from neuron_server.config import config

blueprint = Blueprint(
    "app",
    __name__,
)


@blueprint.get("/config")
async def get_config() -> Dict[str, Any]:
    """
    Returns application configuration settings.

    Returns:
        Dict containing application configuration settings like feature flags,
        API endpoints, and environment-specific values.
    """
    return {
        "sidebar_image": await get_cache_key("sidebar_image"),
        "api": {
            "baseUrl": "/api",
            "wsEndpoint": "/ws",
        },
        "auth0": {
            "domain": config.auth0_domain,
            "clientId": config.auth0_client_id,
            "audience": config.auth0_api_audience,
        },
    }
