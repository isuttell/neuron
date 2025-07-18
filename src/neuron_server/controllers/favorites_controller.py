from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint, Response
from werkzeug.exceptions import BadRequest, NotFound

from neuron_server.controllers.auth import TokenPayload, requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.models.personality_favorite_model import PersonalityFavoriteModel
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.type_defs.request_proxy import request

blueprint = Blueprint("favorites", __name__)


class AddFavoritePayload(BaseModel):
    personality_id: str


@blueprint.get("/")
@requires_auth
async def get_favorites() -> dict[str, list[dict]]:
    """Get user's favorite personalities.

    Returns:
        A dictionary with a list of favorite objects
    """
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    favorites = await PersonalityFavoriteModel.get_user_favorites(user_id=user_id)
    return {"favorites": [favorite.model_dump() for favorite in favorites]}


@blueprint.post("/")
@requires_auth
@requires_csrf
async def add_favorite() -> dict[str, dict]:
    """Add a personality to user's favorites.

    Returns:
        A dictionary with the created favorite

    Raises:
        NotFound: If the personality doesn't exist or user doesn't have access
        BadRequest: If the personality is already favorited
    """
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    body = await request.get_json()
    payload = AddFavoritePayload(**body)
    personality_id = UUID(payload.personality_id)

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Check if already favorited
    is_favorited = await PersonalityFavoriteModel.is_favorite(
        personality_id=personality_id, user_id=user_id
    )
    if is_favorited:
        raise BadRequest("Personality is already favorited")

    # Add to favorites
    favorite = await PersonalityFavoriteModel.create(
        PersonalityFavoriteModel.CreateParams(
            personality_id=personality_id,
            user_id=user_id,
        )
    )

    return {"favorite": favorite.model_dump()}


@blueprint.delete("/<uuid:personality_id>")
@requires_auth
@requires_csrf
async def remove_favorite(personality_id: UUID) -> Response:
    """Remove a personality from user's favorites.

    Args:
        personality_id: The ID of the personality to unfavorite

    Returns:
        204 No Content

    Raises:
        NotFound: If the personality doesn't exist or user doesn't have access
        BadRequest: If the personality is not favorited
    """
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Check if actually favorited
    is_favorited = await PersonalityFavoriteModel.is_favorite(
        personality_id=personality_id, user_id=user_id
    )
    if not is_favorited:
        raise BadRequest("Personality is not favorited")

    # Remove from favorites
    await PersonalityFavoriteModel.delete(
        personality_id=personality_id, user_id=user_id
    )

    return Response(status=204)


@blueprint.post("/<uuid:personality_id>/toggle")
@requires_auth
@requires_csrf
async def toggle_favorite(personality_id: UUID) -> dict[str, dict | bool]:
    """Toggle a personality favorite for a user.

    Args:
        personality_id: The ID of the personality to toggle

    Returns:
        A dictionary with the toggle result and favorite object if added

    Raises:
        NotFound: If the personality doesn't exist or user doesn't have access
    """
    assert isinstance(request.token, TokenPayload)
    user_id = request.token.user_id

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Toggle the favorite
    was_added = await PersonalityFavoriteModel.toggle_favorite(
        personality_id=personality_id, user_id=user_id
    )

    result = {"added": was_added}

    # If favorite was added, return the favorite object
    if was_added:
        favorite = await PersonalityFavoriteModel.get(
            personality_id=personality_id, user_id=user_id
        )
        if favorite:
            result["favorite"] = favorite.model_dump()

    return result
