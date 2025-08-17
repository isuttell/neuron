import logging
from collections.abc import Callable
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar, cast

import aiohttp
import jwt
from pydantic import BaseModel
from quart import request
from werkzeug.exceptions import Unauthorized

from neuron_server.cache import cache_response
from neuron_server.config import config

if TYPE_CHECKING:
    from neuron_server.type_defs.request import NeuronRequest

logger = logging.getLogger(__name__)

# Constants
BEARER_PARTS_LENGTH = 2

T = TypeVar("T")


# Error handler
class AuthError(Exception):
    def __init__(self, error: str, status_code: int) -> None:
        self.error = error
        self.status_code = status_code


# Format error response and append status code
def get_token_auth_header() -> str:
    """Obtains the Access Token from the Authorization Header"""
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise Unauthorized("Authorization header is expected")

    parts = auth.split(" ")

    if parts[0].lower() != "bearer":
        raise Unauthorized(
            'Authorization header must start with "Bearer"',
        )
    if len(parts) == 1:
        raise Unauthorized("Token not found")
    if len(parts) > BEARER_PARTS_LENGTH:
        raise Unauthorized("Invalid Bearer schema")
    return parts[1]


class TokenPayload(BaseModel):
    roles: list[str]
    user_id: str
    email: str
    nickname: str
    picture: str | None
    permissions: list[str]


@cache_response(ttl=60 * 15)
async def get_jwks() -> dict[str, dict]:
    async with (
        aiohttp.ClientSession() as session,
        session.get(f"https://{config.auth0_domain}/.well-known/jwks.json") as response,
    ):
        return await response.json()


async def decode_token(token: str) -> TokenPayload:
    jwks = await get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    rsa_key: dict[str, Any] | None = None
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
                "pem": jwt.algorithms.RSAAlgorithm.from_jwk(key),
            }
    if not rsa_key:
        raise Unauthorized("Unable to find appropriate key")
    try:
        payload = jwt.decode(
            jwt=token,
            key=rsa_key["pem"],
            algorithms=["RS256"],
            audience=config.auth0_api_audience,
            issuer="https://" + config.auth0_domain + "/",
            leeway=10,
        )
        return TokenPayload(
            roles=payload.get("neuron/roles"),
            user_id=payload.get("neuron/user_id"),
            email=payload.get("neuron/email"),
            nickname=payload.get("neuron/nickname"),
            picture=payload.get("neuron/picture"),
            permissions=payload.get("permissions"),
        )
    except jwt.ExpiredSignatureError:
        raise Unauthorized("Token is expired") from None
    except Exception as e:
        logger.error(e)
        raise Unauthorized(str(e)) from e


def requires_auth(func: Callable[..., T]) -> Callable[..., T]:
    """Determines if the Access Token is valid"""

    @wraps(func)
    async def decorated(*args: object, **kwargs: object) -> T:
        token = get_token_auth_header()
        token_payload = await decode_token(token)

        # Check if user has the required "user" role
        if "user" not in token_payload.roles:
            raise Unauthorized("User role required")

        # Cast request to our custom type and set the token
        typed_request = cast("NeuronRequest", request)
        typed_request.token = token_payload

        return await func(*args, **kwargs)

    return decorated


def requires_cookie(func: Callable[..., T]) -> Callable[..., T]:
    """Determines if the session cookie is present and valid"""

    @wraps(func)
    async def decorated(*args: object, **kwargs: object) -> T:
        cookie = request.cookies.get("neuron_session")
        if not cookie and config.static_require_auth:
            raise Unauthorized("Authentication required")

        # If cookie exists, verify it's valid
        if cookie:
            from neuron_server.controllers.csrf import verify_cookie_data

            cookie_data = verify_cookie_data(cookie)
            if not cookie_data and config.static_require_auth:
                raise Unauthorized("Invalid session cookie")

            # Attach user info to request if valid
            if cookie_data:
                request.user_id = cookie_data.get("user_id")  # type: ignore[attr-defined]
                request.session_data = cookie_data  # type: ignore[attr-defined]

        return await func(*args, **kwargs)

    return decorated


def requires_api_key(func: Callable[..., T]) -> Callable[..., T]:
    """Determines if the API key is valid"""

    @wraps(func)
    async def decorated(*args: object, **kwargs: object) -> T:
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise Unauthorized("API key is required")

        if not config.api_key:
            raise Unauthorized("API key is not configured on the server")

        if api_key != config.api_key:
            raise Unauthorized("Invalid API key")

        return await func(*args, **kwargs)

    return decorated


def has_permission(token_payload: TokenPayload, permission: str) -> bool:
    """Check if user has a specific permission"""
    return permission in token_payload.permissions


def has_role(token_payload: TokenPayload, role: str) -> bool:
    """Check if user has a specific role"""
    return role in token_payload.roles


def _create_auth_decorator(
    check_func: Callable[[TokenPayload, str], bool],
    access_type: str,
    value: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Common implementation for auth decorators.

    Args:
        check_func: Function to check if user has required access (permission or role)
        access_type: Type of access being checked ("Permission" or "Role")
        value: The specific permission or role required
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def decorated(*args: object, **kwargs: object) -> T:
            token = get_token_auth_header()
            token_payload = await decode_token(token)

            # Check if user has the required "user" role first
            if "user" not in token_payload.roles:
                raise Unauthorized("User role required")

            # Check if user has the required access
            if not check_func(token_payload, value):
                raise Unauthorized(f"{access_type} '{value}' required")

            # Cast request to our custom type and set the token
            typed_request = cast("NeuronRequest", request)
            typed_request.token = token_payload

            return await func(*args, **kwargs)

        return decorated

    return decorator


def requires_permission(
    permission: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that requires a specific permission for endpoint access.

    Permissions are fine-grained access controls
    (e.g., "admin-prompts", "admin-providers").
    Use this when you need granular access control beyond just role membership.

    Note: Currently permissions don't appear in Auth0 user objects in the frontend,
    so this is primarily for backend-only endpoints or when permissions are available.
    """
    return _create_auth_decorator(has_permission, "Permission", permission)


def requires_role(
    role: str,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator that requires a specific role for endpoint access.

    Roles are broader access controls (e.g., "admin", "user").
    Use this when you need simple role-based access control that works consistently
    across both frontend and backend, as roles are available in Auth0 user objects.

    This is the preferred approach for most access control needs.
    """
    return _create_auth_decorator(has_role, "Role", role)
