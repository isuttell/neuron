import logging
from collections.abc import Callable
from functools import wraps
from typing import TypeVar

import aiohttp
import jwt
from pydantic import BaseModel
from quart import request
from werkzeug.exceptions import Unauthorized

from neuron_server.cache import cache_response
from neuron_server.config import config

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
    rsa_key: dict[str, str | dict] | None = None
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
        request.token = await decode_token(token)
        return await func(*args, **kwargs)

    return decorated
