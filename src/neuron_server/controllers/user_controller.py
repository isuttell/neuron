from quart import Blueprint, Response, jsonify, request

from neuron_server.controllers.auth import TokenPayload, requires_auth
from neuron_server.models import UserModel  # Import UserModel

user_bp = Blueprint("user", __name__)


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

    # Create response
    response = jsonify({"status": "success", "user_id": payload.user_id})

    # Set cookie with user ID that expires in 24 hours
    response.set_cookie(
        "neuron_session",
        value=payload.user_id,
        max_age=86400,  # 24 hours in seconds
        httponly=True,
        samesite="Lax"
    )

    return response, 200
