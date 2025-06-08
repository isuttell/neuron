from uuid import UUID

from quart import Blueprint

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.decorators import rate_limit
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.models.media_list_item_model import MediaListItemModel
from neuron_server.models.media_list_model import MediaListModel
from neuron_server.type_defs.request_proxy import request

blueprint = Blueprint("media", __name__)


@blueprint.get("/recent")
@requires_auth
@rate_limit()
async def get_recent_media() -> dict[str, list[dict]]:
    """
    Get the most recent media items for a user with pagination support.

    Args:
        user_id: The ID of the user (injected by @requires_auth)

    Query Parameters:
        limit: Maximum number of items to return (default: 20)
        offset: Number of items to skip (default: 0)

    Returns:
        Dictionary containing a list of media items formatted for frontend consumption
    """

    limit = request.args.get("limit", default=20, type=int)
    offset = request.args.get("offset", default=0, type=int)
    assert isinstance(request.token.user_id, str)
    media_items = await MediaItemModel.get_recent(
        request.token.user_id, limit=limit, offset=offset
    )

    return {"media_items": [item.model_dump() for item in media_items]}


@blueprint.post("/lists")
@requires_auth
@requires_csrf
async def create_media_list() -> dict:
    """Create a new media list"""
    data = await request.get_json()
    assert isinstance(request.token.user_id, str)

    create_params = MediaListModel.CreateParams(
        name=data["name"],
        description=data["description"],
        user_id=request.token.user_id,
        tags=data.get("tags", []),
        visibility=data.get("visibility", "private"),
        shared_with=data.get("shared_with", []),
    )
    media_list = await MediaListModel.create(params=create_params)

    return {"media_lists": [media_list.model_dump()]}


@blueprint.get("/lists")
@requires_auth
@rate_limit()
async def get_media_lists() -> dict:
    """Get all media lists owned by or shared with the authenticated user"""
    assert isinstance(request.token.user_id, str)
    lists = await MediaListModel.list_for_user(request.token.user_id)
    media_list_items: list[MediaListItemModel] = []
    media_item_ids = set()
    for lst in lists:
        results = await MediaListItemModel.get_by_list(lst.id)
        media_item_ids.update(item.media_item_id for item in results)
        media_list_items.extend(results)
    media_items = await MediaItemModel.get_many(list(media_item_ids))
    return {
        "media_lists": [lst.model_dump() for lst in lists],
        "media_list_items": [item.model_dump() for item in media_list_items],
        "media_items": [item.model_dump() for item in media_items],
    }


@blueprint.get("/lists/<uuid:list_id>")
@requires_auth
async def get_media_list(list_id: UUID) -> dict:
    """Get a specific media list by ID with its media items"""
    assert isinstance(request.token.user_id, str)
    media_list = await MediaListModel.get(list_id=list_id)
    if not media_list:
        return {"error": "Media list not found"}, 404

    # Check if user has access to this list
    if (
        media_list.user_id != request.token.user_id
        and request.token.user_id not in media_list.shared_with
        and media_list.visibility != "public"
    ):
        return {"error": "Unauthorized"}, 403

    # Get media list items and media items
    media_list_items = await MediaListItemModel.get_by_list(list_id)
    media_item_ids = [item.media_item_id for item in media_list_items]
    media_items = await MediaItemModel.get_many(media_item_ids)

    return {
        "media_lists": [media_list.model_dump()],
        "media_list_items": [item.model_dump() for item in media_list_items],
        "media_items": [item.model_dump() for item in media_items],
    }


@blueprint.put("/lists/<uuid:list_id>")
@requires_auth
@requires_csrf
async def update_media_list(list_id: UUID) -> dict:
    """Update a media list"""
    data = await request.get_json()
    media_list = await MediaListModel.get(list_id=list_id)

    if not media_list:
        return {"error": "Media list not found"}, 404

    if media_list.user_id != request.token.user_id:
        return {"error": "Unauthorized"}, 403

    update_params = MediaListModel.UpdateParams(
        list_id=list_id,
        name=data["name"],
        description=data["description"],
        tags=data.get("tags", []),
        visibility=data.get("visibility", "private"),
        shared_with=data.get("shared_with", []),
    )
    updated_list = await MediaListModel.update(params=update_params)

    return {"media_list": updated_list.model_dump()}


@blueprint.delete("/lists/<uuid:list_id>")
@requires_auth
@requires_csrf
async def delete_media_list(list_id: UUID) -> dict:
    """Delete a media list"""
    media_list = await MediaListModel.get(list_id=list_id)

    if not media_list:
        return {"error": "Media list not found"}, 404

    if media_list.user_id != request.token.user_id:
        return {"error": "Unauthorized"}, 403

    await MediaListModel.delete(list_id=list_id)
    return {"success": True}


@blueprint.post("/lists/<uuid:list_id>/media")
@requires_auth
@requires_csrf
@rate_limit()
async def add_media_to_list(list_id: UUID) -> dict:
    """Add a media item to a list"""
    data = await request.get_json()
    assert isinstance(request.token.user_id, str)

    media_list = await MediaListModel.get(list_id=list_id)
    if not media_list:
        return {"error": "Media list not found"}, 404

    # Check if user has access to this list
    if media_list.user_id != request.token.user_id:
        return {"error": "Unauthorized"}, 403

    media_item = await MediaItemModel.get(media_id=UUID(data["media_item_id"]))
    if not media_item:
        return {"error": "Media item not found"}, 404

    # Get the current highest index in the list
    current_max_index = await MediaListModel.get_max_index(list_id)
    next_index = (current_max_index or -1) + 1

    # Add the media item to the list with the next index
    media_list_item = await MediaListModel.add_media_item(
        list_id=list_id, media_item_id=media_item.id, index=next_index
    )

    return {
        "media_list_items": [
            {
                "id": media_list_item.id,
                "index": media_list_item.index,
                "media_list_id": media_list_item.media_list_id,
                "media_item_id": media_list_item.media_item_id,
                "created_at": media_list_item.created_at.astimezone().isoformat(
                    timespec="seconds"
                ),
                "updated_at": media_list_item.updated_at.astimezone().isoformat(
                    timespec="seconds"
                ),
            }
        ]
    }
