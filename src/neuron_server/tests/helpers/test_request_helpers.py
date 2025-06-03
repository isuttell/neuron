"""Helper functions for creating test requests with CSRF tokens"""
from quart import Quart

from neuron_server.controllers.csrf import create_session_cookie


async def setup_csrf_request_context(
    app: Quart,
    path: str,
    method: str = "POST",
    user_id: str = "test_user_id",
    headers: dict[str, str] | None = None,
    json: dict | None = None,
    form: dict | None = None,
) -> object:
    """
    Create a test request context with CSRF headers and session cookie.

    Args:
        app: The Quart app instance
        path: The request path
        method: The HTTP method (default: POST)
        user_id: The user ID for the session (default: test_user_id)
        headers: Additional headers to include
        json: JSON data for the request body
        form: Form data for the request body

    Returns:
        Test request context
    """
    # Create session cookie with CSRF token
    cookie_value, csrf_token = create_session_cookie(user_id, include_csrf=True)

    # Build headers
    request_headers = headers or {}
    request_headers["Cookie"] = f"neuron_session={cookie_value}"

    # Add CSRF token for non-GET/HEAD/OPTIONS methods
    if method not in ["GET", "HEAD", "OPTIONS"]:
        request_headers["X-CSRF-Token"] = csrf_token

    # Create request context
    ctx = app.test_request_context(
        path,
        method=method,
        headers=request_headers,
        json=json,
        form_data=form,
    )

    # Set session data on request
    async with ctx:
        from quart import request
        request.user_id = user_id
        request.session_data = {"user_id": user_id, "csrf_token": csrf_token}

    return ctx
