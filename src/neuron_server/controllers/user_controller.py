from quart import Blueprint, Response, jsonify

from neuron_server.controllers.auth import TokenPayload, requires_auth
from neuron_server.controllers.csrf import (
    COOKIE_MAX_AGE,
    IS_PRODUCTION,
    create_session_cookie,
)
from neuron_server.models import UserModel  # Import UserModel
from neuron_server.type_defs.request_proxy import request

user_bp = Blueprint("user", __name__)


@user_bp.route("/", methods=["GET"])
@requires_auth
async def search_users() -> Response:
    """Search for users by email."""
    email = request.args.get("email")

    if not email:
        return jsonify({"users": []}), 200

    user = await UserModel.get_by_email(email)

    if user:
        return jsonify({"users": [user.model_dump()]}), 200

    return jsonify({"users": []}), 200


@user_bp.route("/login", methods=["POST"])
@requires_auth
async def login_user() -> Response:  # Add return type hint
    """
    Endpoint called after successful frontend authentication.
    Uses the validated token from requires_auth to upsert user info.
    """
    payload: TokenPayload = request.token  # requires_auth attaches this

    # Call the upsert method on the UserModel
    await UserModel.upsert_from_payload(payload)

    # Create session cookie with CSRF token
    cookie_value, csrf_token = create_session_cookie(payload.user_id, include_csrf=True)

    # Create response with CSRF token
    response = jsonify(
        {
            "status": "success",
            "user_id": payload.user_id,
            "csrf_token": csrf_token,  # Send CSRF token to client
        }
    )

    # Set secure session cookie
    response.set_cookie(
        "neuron_session",
        value=cookie_value,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",  # Protect against CSRF attacks
        secure=IS_PRODUCTION,  # Use secure cookies in production
        path="/",  # Ensure cookie is sent with all requests
    )

    return response, 200
