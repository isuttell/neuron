"""HTTP decorators for Quart applications."""

import time
from functools import wraps
from typing import Any, Callable

import redis
from quart import Response, jsonify, request

from neuron_server.config import config


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
                "https://neuron.zaks.io"
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
    """Redis-based sliding window rate limiter."""

    def __init__(self) -> None:
        self.redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
            password=config.redis.password,
            decode_responses=True,
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
            "CF-Connecting-IP",      # Cloudflare
            "True-Client-IP",        # Some CDNs
            "X-Forwarded-For",       # Standard (Traefik uses this)
            "X-Real-IP",             # Nginx
            "X-Client-IP",           # Legacy
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

    def _check_rate_limit(
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
        self.redis_client.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        current_count = self.redis_client.zcard(key)

        if current_count >= limit:
            # Get the oldest entry to calculate retry time
            oldest_entries = self.redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_entries:
                oldest_time = oldest_entries[0][1]
                retry_after = int(oldest_time + window_seconds - now) + 1
                return False, max(1, retry_after)
            return False, 60  # Default retry after 60 seconds

        # Add current request
        self.redis_client.zadd(key, {str(now): now})

        # Set expiration on the key
        self.redis_client.expire(key, window_seconds + 10)

        return True, 0

    def check_limits(self, client_ip: str, limit_type: str = "api") -> None:
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
        allowed, retry_after = self._check_rate_limit(
            minute_key, limits["requests_per_minute"], 60
        )
        if not allowed:
            raise RateLimitExceededError(
                retry_after, "requests per minute", limits["requests_per_minute"]
            )

        # Check per-hour limit
        hour_key = f"rate_limit:{limit_type}:{auth_status}:{client_ip}:hour"
        allowed, retry_after = self._check_rate_limit(
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
                _rate_limiter.check_limits(client_ip, limit_type)

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

                response = await jsonify(error_response)
                response.status_code = 429
                response.headers["Retry-After"] = str(e.retry_after)
                response.headers["X-RateLimit-Limit"] = str(e.limit_value)
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(
                    int(time.time() + e.retry_after)
                )

                return response

            except Exception as e:
                # Log the error but don't block the request on rate limiter failures
                print(f"Rate limiter error: {e}")
                return await func(*args, **kwargs)

        return wrapped_func

    return decorator
