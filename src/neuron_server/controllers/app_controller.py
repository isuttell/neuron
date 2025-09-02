import logging
from typing import Any

from quart import Blueprint

from neuron_server.cache import get_cache_key
from neuron_server.config import config
from neuron_server.llms.tools import get_protected_tool_sets

logger = logging.getLogger(__name__)

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


@blueprint.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Health check endpoint with configuration validation.

    Returns:
        Dict containing health status and any configuration issues.
    """
    issues = config.validate_production_config()

    # Log configuration issues
    for issue in issues:
        if issue.startswith("CRITICAL"):
            logger.error(issue)
        elif issue.startswith("WARNING"):
            logger.warning(issue)
        else:
            logger.info(issue)

    status = "healthy"
    if any(issue.startswith("CRITICAL") for issue in issues):
        status = "unhealthy"
    elif any(issue.startswith("WARNING") for issue in issues):
        status = "degraded"

    return {
        "status": status,
        "environment": "production" if config.is_production else "development",
        "session_ttl_hours": config.redis.session_ttl // 3600,
        "csrf_rotation_enabled": config.csrf_token_rotation,
        "configuration_issues": issues,
    }
