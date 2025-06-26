from typing import Any

from quart import Blueprint

from neuron_server.cache import get_cache_key
from neuron_server.config import config
from neuron_server.llms.tools import get_protected_tool_sets

blueprint = Blueprint(
    "app",
    __name__,
)


@blueprint.get("/config")
async def get_config() -> dict[str, Any]:
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
        "protectedToolSets": get_protected_tool_sets(),
    }
