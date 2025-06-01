"""Helper functions for CSRF testing"""
from neuron_server.controllers.csrf import create_session_cookie


def get_csrf_headers(user_id: str = "test_user_id") -> tuple[dict[str, str], str]:
    """
    Create CSRF headers for testing.

    Returns:
        Tuple of (headers dict with CSRF token, cookie value)
    """
    cookie_value, csrf_token = create_session_cookie(user_id, include_csrf=True)

    headers = {
        "X-CSRF-Token": csrf_token,
        "Cookie": f"neuron_session={cookie_value}"
    }

    return headers, cookie_value


def add_csrf_to_headers(headers: dict[str, str], user_id: str = "test_user_id") -> dict[str, str]:
    """
    Add CSRF headers to existing headers.

    Args:
        headers: Existing headers dict
        user_id: User ID for the session

    Returns:
        Updated headers dict with CSRF token
    """
    csrf_headers, _ = get_csrf_headers(user_id)
    return {**headers, **csrf_headers}
