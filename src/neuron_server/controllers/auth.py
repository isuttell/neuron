from quart import request
import jwt
from functools import wraps
from typing import Awaitable, Any, List, Dict
import aiohttp
from neuron_server.config import config
import logging
from pydantic import BaseModel
from neuron_server.cache import cache_response
from werkzeug.exceptions import Unauthorized, Forbidden

logger = logging.getLogger(__name__)


# Error handler
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


# Format error response and append status code
def get_token_auth_header():
    """Obtains the Access Token from the Authorization Header"""
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise Unauthorized("Authorization header is expected")

    parts = auth.split(" ")

    if parts[0].lower() != "bearer":
        raise Unauthorized(
            'Authorization header must start with "Bearer"',
        )
    elif len(parts) == 1:
        raise Unauthorized("Token not found")
    elif len(parts) > 2:
        raise Unauthorized("Invalid Bearer schema")
    token = parts[1]
    return token


class TokenPayload(BaseModel):
    roles: List[str]
    user_id: str
    email: str
    nickname: str
    permissions: List[str]


@cache_response(ttl=60 * 15)
async def get_jwks() -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"https://{config.auth0_domain}/.well-known/jwks.json"
        ) as response:
            return await response.json()


async def decode_token(token: str) -> TokenPayload:
    jwks = await get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    rsa_key: Dict[str, Any] | None = None
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
        raise Unauthorized("Token is expired")
    except Exception as e:
        logger.error(e)
        raise Unauthorized(str(e))


def requires_auth(func: Awaitable[Any]):
    """Determines if the Access Token is valid"""

    @wraps(func)
    async def decorated(*args, **kwargs):
        token = get_token_auth_header()
        request.token = await decode_token(token)
        return await func(*args, **kwargs)

    return decorated
