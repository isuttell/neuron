"""HTTP decorators for Quart applications."""

import logging
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, TypeVar

import redis.asyncio as redis
from quart import Response, jsonify, request

from neuron_server.config import config

T = TypeVar("T")

logger = logging.getLogger(__name__)


def cors(
    allowed_origins: list[str] | None = None,
    allowed_methods: list[str] | None = None,
    allowed_headers: list[str] | None = None,
) -> Callable:
    """Add CORS headers to response.

    Args:
        allowed_origins: List of allowed origins. Defaults to production origins
            or all origins in debug mode.
        allowed_methods: List of allowed methods. Defaults to
            ["GET", "POST", "PUT", "DELETE", "OPTIONS"].
        allowed_headers: List of allowed headers. Defaults to
            ["Content-Type", "Authorization"].

    Returns:
        Decorated function that adds CORS headers to response.
    """
    if allowed_origins is None:
        if config.debug:
            # Allow localhost origins in debug mode
            allowed_origins = [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
                "https://neuron.zaks.io",
            ]
        else:
            # Production: only allow specific domain
            allowed_origins = ["https://neuron.zaks.io"]
    if allowed_methods is None:
        allowed_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    if allowed_headers is None:
        allowed_headers = ["Content-Type", "Authorization"]

    def add_cors_headers(func: Callable) -> Callable:
        func.required_methods = getattr(func, "required_methods", set())  # type: ignore
        func.required_methods.add("OPTIONS")  # type: ignore
        func.provide_automatic_options = False  # type: ignore

        @wraps(func)
        async def wrapped_func(*args: Any, **kwargs: Any) -> Response:
            # Get the origin from the request
            origin = request.headers.get("Origin", "")

            # Always process the request since CORS is a browser protection
            response: Response = await func(*args, **kwargs)

            # Only add CORS headers if origin is allowed
            if origin in allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = ", ".join(
                    allowed_methods
                )
                response.headers["Access-Control-Allow-Headers"] = ", ".join(
                    allowed_headers
                )
                response.headers["Access-Control-Allow-Credentials"] = "true"

            return response

        return wrapped_func

    return add_cors_headers


def cache_control(
    max_age: int | None = None,
    no_cache: bool = False,
    private: bool = False,
    public: bool = False,
    immutable: bool = False,
) -> Callable:
    """Add Cache-Control headers to response.

    Args:
        max_age: Maximum age in seconds.
        no_cache: Whether to use no-cache directive.
        private: Whether to use private directive.
        public: Whether to use public directive.
        immutable: Whether to use immutable directive.

    Returns:
        Decorated function that adds Cache-Control headers to response.
    """

    def add_headers(func: Callable) -> Callable:
        @wraps(func)
        async def wrapped_func(*args: Any, **kwargs: Any) -> Response:
            response: Response = await func(*args, **kwargs)
            values = []

            if isinstance(max_age, int):
                values.append(f"max-age={max_age}")
            elif no_cache:
                values.append("no-cache")

            if private:
                values.append("private")
            elif public:
                values.append("public")

            if immutable:
                values.append("immutable")

            if values:
                response.headers["Cache-Control"] = ", ".join(values)
            return response

        return wrapped_func

    return add_headers


class RateLimitExceededError(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: int, limit_type: str, limit_value: int) -> None:
        self.retry_after = retry_after
        self.limit_type = limit_type
        self.limit_value = limit_value
        super().__init__(f"Rate limit exceeded: {limit_value} {limit_type}")


class RateLimiter:
    """Redis-based sliding window rate limiter with connection management."""

    def __init__(self) -> None:
        self._redis_config = {
            "host": config.redis.host,
            "port": config.redis.port,
            "db": config.redis.db,
            "password": config.redis.password,
            "decode_responses": True,
            "socket_connect_timeout": 5,
            "socket_timeout": 5,
            "retry_on_timeout": True,
            "health_check_interval": 30,
        }
        self.redis_client = self._create_redis_client()

    def _create_redis_client(self) -> redis.Redis:
        """Create Redis client with connection pool and retry logic."""
        return redis.Redis(
            connection_pool=redis.ConnectionPool(**self._redis_config),
        )

    def _get_client_ip(self) -> str:
        """Get client IP address, handling proxies (including Traefik)."""
        # Priority order for proxy headers:
        # 1. CF-Connecting-IP (Cloudflare)
        # 2. True-Client-IP (CDNs)
        # 3. X-Forwarded-For (Standard proxy header, including Traefik)
        # 4. X-Real-IP (Nginx, some proxies)
        # 5. X-Client-IP (Legacy)
        # 6. request.remote_addr (Direct connection)

        # Check various proxy headers in order of reliability
        for header in [
            "CF-Connecting-IP",  # Cloudflare
            "True-Client-IP",  # Some CDNs
            "X-Forwarded-For",  # Standard (Traefik uses this)
            "X-Real-IP",  # Nginx
            "X-Client-IP",  # Legacy
        ]:
            ip_value = request.headers.get(header)
            if ip_value:
                # For X-Forwarded-For, take the first (leftmost) IP
                if header == "X-Forwarded-For":
                    return ip_value.split(",")[0].strip()
                return ip_value.strip()

        # Fall back to direct connection
        return request.remote_addr or "unknown"

    def _is_authenticated(self) -> bool:
        """Check if the request is from an authenticated user."""
        # Check for Authorization header
        auth_header = request.headers.get("Authorization")
        return bool(auth_header and auth_header.startswith("Bearer "))

    def _get_rate_limits(self, limit_type: str = "api") -> dict[str, int]:
        """Get rate limits based on authentication status and endpoint type."""
        if limit_type == "static":
            # More restrictive limits for static content (thumbnail generation)
            if self._is_authenticated():
                return {
                    "requests_per_minute": 120,
                    "requests_per_hour": 1000,
                }
            return {
                "requests_per_minute": 30,
                "requests_per_hour": 200,
            }
        # Standard API limits
        if self._is_authenticated():
            return {
                "requests_per_minute": 300,
                "requests_per_hour": 5000,
            }
        return {
            "requests_per_minute": 60,
            "requests_per_hour": 500,
        }

    async def _execute_redis_command(
        self,
        command_name: str,
        command_func: Callable[[], Awaitable[T]],
        *,
        max_retries: int = 2,
        fail_fast: bool = True,
    ) -> T:
        """
        Execute Redis command with connection management and retry logic.

        Args:
            command_name: Name of the command for logging
            command_func: Function that executes the Redis command
            max_retries: Maximum number of retries for connection errors
            fail_fast: If True, raise on Redis errors (protects system)

        Returns:
            Result of the Redis command

        Raises:
            Exception: If Redis fails and fail_fast is True
        """
        for attempt in range(max_retries + 1):
            try:
                return await command_func()
            except redis.ConnectionError as e:
                if attempt < max_retries:
                    logger.warning(
                        f"Redis connection error on {command_name} "
                        f"(attempt {attempt + 1}/{max_retries + 1}): {e}"
                    )
                    # Quick retry for connection issues
                    time.sleep(0.1 * (attempt + 1))
                    continue
                # Final attempt failed
                logger.error(
                    f"Redis connection failed after {max_retries + 1} attempts "
                    f"for {command_name}: {e}",
                    exc_info=True,
                )
                if fail_fast:
                    raise
            except redis.TimeoutError as e:
                # Don't retry timeouts - Redis is overwhelmed
                logger.error(
                    f"Redis timeout error on {command_name}: {e}", exc_info=True
                )
                if fail_fast:
                    raise
            except redis.RedisError as e:
                logger.error(f"Redis error on {command_name}: {e}", exc_info=True)
                if fail_fast:
                    raise

        # Should not reach here with fail_fast=True
        raise RuntimeError(f"Redis command {command_name} failed after all retries")

    async def _check_rate_limit(
        self, key: str, limit: int, window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window.

        Returns:
            tuple: (is_allowed, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds

        # Remove old entries outside the window
        await self._execute_redis_command(
            "zremrangebyscore",
            lambda: self.redis_client.zremrangebyscore(key, 0, window_start),
        )

        # Count current requests in window
        current_count = await self._execute_redis_command(
            "zcard", lambda: self.redis_client.zcard(key)
        )

        if current_count >= limit:
            # Get the oldest entry to calculate retry time
            oldest_entries = await self._execute_redis_command(
                "zrange", lambda: self.redis_client.zrange(key, 0, 0, withscores=True)
            )
            if oldest_entries:
                oldest_time = oldest_entries[0][1]
                retry_after = int(oldest_time + window_seconds - now) + 1
                return False, max(1, retry_after)
            return False, 60  # Default retry after 60 seconds

        # Add current request
        await self._execute_redis_command(
            "zadd", lambda: self.redis_client.zadd(key, {str(now): now})
        )

        # Set expiration on the key
        await self._execute_redis_command(
            "expire", lambda: self.redis_client.expire(key, window_seconds + 10)
        )

        return True, 0

    async def check_limits(self, client_ip: str, limit_type: str = "api") -> None:
        """
        Check all rate limits for a client.

        Args:
            client_ip: Client IP address
            limit_type: Type of limits to apply ("api" or "static")

        Raises:
            RateLimitExceededError: If any rate limit is exceeded
        """
        limits = self._get_rate_limits(limit_type)
        auth_status = "auth" if self._is_authenticated() else "unauth"

        # Include limit_type in the key to separate static vs API limits
        # Check per-minute limit
        minute_key = f"rate_limit:{limit_type}:{auth_status}:{client_ip}:minute"
        allowed, retry_after = await self._check_rate_limit(
            minute_key, limits["requests_per_minute"], 60
        )
        if not allowed:
            raise RateLimitExceededError(
                retry_after, "requests per minute", limits["requests_per_minute"]
            )

        # Check per-hour limit
        hour_key = f"rate_limit:{limit_type}:{auth_status}:{client_ip}:hour"
        allowed, retry_after = await self._check_rate_limit(
            hour_key, limits["requests_per_hour"], 3600
        )
        if not allowed:
            raise RateLimitExceededError(
                retry_after, "requests per hour", limits["requests_per_hour"]
            )


# Global rate limiter instance
_rate_limiter = RateLimiter()


def rate_limit(enabled: bool = True, limit_type: str = "api") -> Callable:
    """
    Rate limiting decorator for Quart routes.

    Args:
        enabled: Whether rate limiting is enabled. Defaults to True.
        limit_type: Type of rate limits to apply ("api" or "static").
                   Static endpoints have more restrictive limits.

    Returns:
        Decorated function that enforces rate limits.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapped_func(*args: Any, **kwargs: Any) -> Response:
            if not enabled:
                return await func(*args, **kwargs)

            try:
                client_ip = _rate_limiter._get_client_ip()
                await _rate_limiter.check_limits(client_ip, limit_type)

                # Rate limit passed, process request normally
                return await func(*args, **kwargs)

            except RateLimitExceededError as e:
                # Create JSON error response
                error_response = {
                    "error": "rate_limit_exceeded",
                    "message": f"Rate limit exceeded: {e.limit_value} {e.limit_type}",
                    "retry_after": e.retry_after,
                    "limit_type": e.limit_type,
                    "limit_value": e.limit_value,
                }

                response = jsonify(error_response)
                response.status_code = 429
                response.headers["Retry-After"] = str(e.retry_after)
                response.headers["X-RateLimit-Limit"] = str(e.limit_value)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(
                    int(time.time() + e.retry_after)
                )

                return response

            except Exception as e:
                # Only handle Redis-related exceptions
                is_redis_error = False
                try:
                    is_redis_error = isinstance(
                        e, (redis.ConnectionError, redis.TimeoutError, redis.RedisError)
                    )
                except (TypeError, AttributeError):
                    # In test environment, redis may not have these exception types
                    is_redis_error = type(e).__name__ in (
                        "ConnectionError",
                        "TimeoutError",
                        "RedisError",
                    )

                if is_redis_error:
                    # Log the error and reject the request to protect the system
                    logger.error(
                        "Rate limiter error - rejecting request to protect system: %s",
                        e,
                        exc_info=True,
                    )
                    # Return 503 Service Unavailable when rate limiter fails
                    error_response = {
                        "error": "service_unavailable",
                        "message": "Rate limiting service temporarily unavailable",
                        "retry_after": 60,
                    }
                    response = jsonify(error_response)
                    response.status_code = 503
                    response.headers["Retry-After"] = "60"
                    return response
                # Re-raise non-Redis exceptions (like BadRequest)
                raise

        return wrapped_func

    return decorator
