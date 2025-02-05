"""HTTP decorators for Quart applications."""

from functools import wraps
from typing import Any, Callable

from quart import Response


def cors(
    allowed_origins: list[str] | None = None,
    allowed_methods: list[str] | None = None,
    allowed_headers: list[str] | None = None,
) -> Callable:
    """Add CORS headers to response.

    Args:
        allowed_origins: List of allowed origins. Defaults to ["*"].
        allowed_methods: List of allowed methods. Defaults to
            ["GET", "POST", "PUT", "DELETE", "OPTIONS"].
        allowed_headers: List of allowed headers. Defaults to
            ["Content-Type", "Authorization"].

    Returns:
        Decorated function that adds CORS headers to response.
    """
    if allowed_origins is None:
        allowed_origins = ["*"]
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
            response: Response = await func(*args, **kwargs)
            response.headers["Access-Control-Allow-Origin"] = ", ".join(allowed_origins)
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                allowed_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ", ".join(
                allowed_headers
            )
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
