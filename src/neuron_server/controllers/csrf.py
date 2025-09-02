"""CSRF protection for Neuron API."""

import base64
import binascii
import hashlib
import hmac
import json
import logging
import secrets
import sys
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Callable, TypeVar

from quart import Request, Response, request
from werkzeug.exceptions import Forbidden

from neuron_server.config import config

# Logger for CSRF events
logger = logging.getLogger(__name__)

# Configuration validation
# Check if we're running tests
is_test = (
    "pytest" in sys.modules
    or "test" in sys.argv[0]
    or any("test" in arg for arg in sys.argv)
)

dev_key = "dev-secret-key-only-for-local-development"
if not config.debug and not is_test and config.secret_key == dev_key:
    raise ValueError(
        "SECRET_KEY must be set to a secure value in production! "
        "Set the SECRET_KEY environment variable."
    )

# Configuration
COOKIE_MAX_AGE = config.csrf_cookie_max_age
SECRET_KEY = config.secret_key
ENABLE_TOKEN_ROTATION = config.csrf_token_rotation
IS_PRODUCTION = config.is_production

T = TypeVar("T")


def _should_use_secure_cookies() -> bool:
    """
    Determine if secure flag should be used for cookies.
    Uses enhanced detection for production environments.
    """
    # If explicitly in production, always use secure cookies
    if IS_PRODUCTION:
        return True

    # Check for HTTPS in current request if available
    try:
        if hasattr(request, "is_secure") and request.is_secure:
            return True
        if hasattr(request, "scheme") and request.scheme == "https":
            return True
        if request.headers.get("X-Forwarded-Proto") == "https":
            return True
        if request.headers.get("X-Forwarded-Scheme") == "https":
            return True
    except RuntimeError:
        # No request context available
        pass

    # Default to secure in production-like environments
    return IS_PRODUCTION


def _get_cookie_domain() -> str | None:
    """
    Get appropriate domain for session cookies.
    Returns None for localhost/development, specific domain for production.
    """
    if not IS_PRODUCTION:
        return None

    # Set domain for production to ensure cookies work across subdomains
    try:
        host = request.headers.get("Host", "")
        if "zaks.io" in host:
            return ".zaks.io"
        if "neuron." in host:
            # Extract main domain from neuron.domain.com
            parts = host.split(".")
            min_domain_parts = 2
            if len(parts) >= min_domain_parts:
                return f".{'.'.join(parts[-2:])}"
    except RuntimeError:
        # No request context available
        pass

    return None


async def _update_session_activity_if_needed(user_id: str | None) -> None:
    """
    Update session activity for sliding expiration if user has active sessions.
    This implements sliding session expiration by extending TTL on each request.
    """
    if not user_id:
        return

    try:
        # Import here to avoid circular imports
        from neuron_server.redis_session_store import redis_session_store

        # Get user's active sessions
        sessions = await redis_session_store.get_user_sessions(user_id)

        # Update activity for all user's sessions to implement sliding expiration
        for session in sessions:
            await redis_session_store.update_session_activity(session.session_id)

        if sessions and config.debug:
            logger.debug(
                f"Updated activity for {len(sessions)} sessions for user {user_id}"
            )

    except Exception as e:
        # Don't fail authentication if session update fails
        logger.warning(f"Failed to update session activity for user {user_id}: {e}")
        if config.debug:
            logger.exception("Session activity update error details")


class CSRFError(Forbidden):
    """Custom CSRF error exception with structured error codes"""

    def __init__(
        self,
        description: str = "CSRF validation failed",
        error_code: str = "CSRF_VALIDATION_FAILED",
        retry_possible: bool = True,
        session_expired: bool = False,
    ) -> None:
        super().__init__(description=description)
        self.error_code = error_code
        self.error_type = "csrf"
        self.retry_possible = retry_possible
        self.session_expired = session_expired


def generate_csrf_token() -> str:
    """Generate a secure CSRF token"""
    return secrets.token_urlsafe(32)


def sign_cookie_data(data: dict[str, Any]) -> str:
    """Sign cookie data with HMAC"""
    # Convert data to JSON string
    json_data = json.dumps(data, sort_keys=True)

    # Create HMAC signature
    signature = hmac.new(
        SECRET_KEY.encode(), json_data.encode(), hashlib.sha256
    ).hexdigest()

    # Return base64-encoded signed data
    # Simply concatenate - we know signature is always 64 chars
    signed_data = f"{json_data}{signature}"
    return base64.urlsafe_b64encode(signed_data.encode()).decode()


def verify_cookie_data(signed_data: str) -> dict[str, Any] | None:
    """Verify and extract data from signed cookie"""
    try:
        # Add padding if missing - some systems strip the '=' padding
        padding_needed = len(signed_data) % 4
        if padding_needed:
            signed_data += "=" * (4 - padding_needed)

        # Decode base64
        decoded = base64.urlsafe_b64decode(signed_data.encode()).decode()

        # HMAC-SHA256 signature is always 64 hex characters
        signature_length = 64

        # Extract signature from the end and JSON from the beginning
        if len(decoded) < signature_length:
            if config.debug:
                logger.warning("Cookie verification failed: Too short for signature")
            return None

        signature = decoded[-signature_length:]
        json_data = decoded[:-signature_length]

        # Verify signature
        expected_signature = hmac.new(
            SECRET_KEY.encode(), json_data.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            if config.debug:
                logger.warning("Cookie verification failed: Invalid signature")
            return None

        # Parse and return data
        data = json.loads(json_data)

        # Check expiration
        if "expires" in data:
            expires = datetime.fromisoformat(data["expires"])
            if datetime.utcnow() > expires:
                if config.debug:
                    logger.warning("Cookie verification failed: Expired")
                # Return special marker for expired sessions
                return {"_session_expired": True}

        return data

    except (
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
        TypeError,
    ) as e:
        if config.debug:
            logger.warning(f"Cookie verification failed: {type(e).__name__}: {e}")
        return None


def create_session_cookie(
    user_id: str, include_csrf: bool = True
) -> tuple[str, str | None]:
    """
    Create a signed session cookie with optional CSRF token.
    Returns (cookie_value, csrf_token)
    """
    csrf_token = generate_csrf_token() if include_csrf else None

    cookie_data = {
        "user_id": user_id,
        "created": datetime.utcnow().isoformat(),
        "expires": (datetime.utcnow() + timedelta(seconds=COOKIE_MAX_AGE)).isoformat(),
    }

    if csrf_token:
        cookie_data["csrf_token"] = csrf_token

    signed_cookie = sign_cookie_data(cookie_data)

    return signed_cookie, csrf_token


async def extract_csrf_token(request: Request) -> str | None:
    """Extract CSRF token from request headers or form data"""
    # Check header first (for AJAX requests) - this is the most common case
    csrf_token = request.headers.get("X-CSRF-Token")
    if csrf_token:
        return csrf_token

    # For non-GET methods, check body data
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        content_type = request.headers.get("Content-Type", "")

        # Check JSON body for API requests
        if request.is_json or "application/json" in content_type:
            try:
                data = await request.get_json(cache=True)
                if isinstance(data, dict):
                    csrf_token = data.get("csrf_token")
                    if csrf_token:
                        return csrf_token
            except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
                # Invalid JSON data, continue to form data check
                pass

        # Check form data only if we haven't found the token yet
        elif (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            try:
                form = await request.form
                csrf_token = form.get("csrf_token")
                if csrf_token:
                    return csrf_token
            except (UnicodeDecodeError, ValueError, RuntimeError):
                # Form data might not be available or malformed
                pass

    return csrf_token


async def rotate_csrf_token(response: Response, user_id: str) -> str | None:
    """
    Rotate CSRF token after successful state-changing request.
    Returns the new CSRF token.
    """
    if not ENABLE_TOKEN_ROTATION:
        return None

    # Create new session with new CSRF token
    cookie_value, new_csrf_token = create_session_cookie(user_id, include_csrf=True)

    # Set the new cookie
    response.set_cookie(
        "neuron_session",
        value=cookie_value,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=_should_use_secure_cookies(),  # Enhanced secure flag detection
        path="/",  # Ensure cookie is sent with all requests
        domain=_get_cookie_domain(),  # Set domain for production
    )

    if config.debug:
        logger.debug(f"Rotated CSRF token for user {user_id}")

    return new_csrf_token


async def _validate_csrf_cookie(request: Request) -> dict[str, Any]:
    """Validate and extract CSRF cookie data."""
    cookie = request.cookies.get("neuron_session")
    if not cookie:
        if config.debug:
            logger.warning(
                f"CSRF check failed: Session cookie missing for "
                f"{request.method} {request.path}"
            )
        raise CSRFError("Session cookie missing", "CSRF_SESSION_MISSING")

    cookie_data = verify_cookie_data(cookie)
    if not cookie_data:
        if config.debug:
            logger.warning(
                f"CSRF check failed: Invalid session cookie for "
                f"{request.method} {request.path}"
            )
        raise CSRFError("Invalid session cookie", "CSRF_SESSION_INVALID")

    # Check for expired session marker
    if cookie_data.get("_session_expired"):
        logger.info(f"Session expired for {request.method} {request.path}")
        raise CSRFError(
            "Your session has expired. Please log in again.",
            "CSRF_SESSION_EXPIRED",
            retry_possible=False,
            session_expired=True,
        )

    # Update session activity for sliding expiration
    await _update_session_activity_if_needed(cookie_data.get("user_id"))

    return cookie_data


async def _validate_csrf_tokens(request: Request, cookie_data: dict[str, Any]) -> None:
    """Validate CSRF tokens from cookie and request."""
    stored_csrf = cookie_data.get("csrf_token")
    if not stored_csrf:
        if config.debug:
            logger.warning(
                f"CSRF check failed: Token not in session for "
                f"{request.method} {request.path}"
            )
        raise CSRFError("CSRF token not found in session", "CSRF_TOKEN_NOT_IN_SESSION")

    provided_csrf = await extract_csrf_token(request)
    if not provided_csrf:
        if config.debug:
            logger.warning(
                f"CSRF check failed: Token missing from request for "
                f"{request.method} {request.path}"
            )
        raise CSRFError("CSRF token missing from request", "CSRF_TOKEN_MISSING")

    if not hmac.compare_digest(stored_csrf, provided_csrf):
        user_id = cookie_data.get("user_id", "unknown")
        logger.warning(
            f"CSRF token mismatch for user {user_id} from IP {request.remote_addr} "
            f"on {request.method} {request.path}"
        )
        if config.debug:
            logger.debug(f"Expected: {stored_csrf[:8]}..., Got: {provided_csrf[:8]}...")
        raise CSRFError("Invalid CSRF token", "CSRF_TOKEN_INVALID")


async def _handle_token_rotation(result: object, user_id: str) -> None:
    """Handle CSRF token rotation in response."""
    if not ENABLE_TOKEN_ROTATION or not isinstance(result, Response):
        return

    new_token = await rotate_csrf_token(result, user_id)
    if new_token:
        result.headers["X-New-CSRF-Token"] = new_token
        if config.debug:
            logger.debug(f"Added new CSRF token to response headers for user {user_id}")


def requires_csrf(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to require CSRF validation for state-changing operations.
    Use this on POST, PUT, DELETE, PATCH endpoints.
    """

    @wraps(func)
    async def decorated(*args: object, **kwargs: object) -> T:
        # Skip CSRF check for safe methods
        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return await func(*args, **kwargs)

        # Validate cookie and extract data
        cookie_data = await _validate_csrf_cookie(request)

        # Validate CSRF tokens
        await _validate_csrf_tokens(request, cookie_data)

        # Attach validated user data to request
        request.user_id = cookie_data.get("user_id")  # type: ignore[attr-defined]
        request.session_data = cookie_data  # type: ignore[attr-defined]

        # Execute the protected function
        result = await func(*args, **kwargs)

        # Handle token rotation
        await _handle_token_rotation(result, request.user_id)  # type: ignore[attr-defined]

        return result

    return decorated


def requires_csrf_or_api_key(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator that allows either CSRF validation or API key authentication.
    Useful for endpoints that need to support both browser and API access.
    """

    @wraps(func)
    async def decorated(*args: object, **kwargs: object) -> T:
        # Check for API key first
        api_key = request.headers.get("X-API-Key")
        if api_key and config.api_key and api_key == config.api_key:
            if config.debug:
                logger.debug(
                    f"API key auth successful for {request.method} {request.path}"
                )
            # Valid API key, skip CSRF check
            return await func(*args, **kwargs)

        # No valid API key, fall back to CSRF check
        return await requires_csrf(func)(*args, **kwargs)

    return decorated
