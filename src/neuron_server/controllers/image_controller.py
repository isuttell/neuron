from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint, request

from neuron_server.controllers.auth import requires_auth
from neuron_server.event_router import EventRouter
from neuron_server.models.media_item_model import MediaItemModel

blueprint = Blueprint("image", __name__)
router = EventRouter()


class ImageRequest(BaseModel):
    prompt: str
    model: str
    thread_id: UUID | None = None


@blueprint.get("/")
@requires_auth
async def get_images() -> list[dict]:
    return [
        image.model_dump(exclude={"path"})
        for image in await MediaItemModel.get_user_media(
            user_id=request.token.user_id,
            media_type="image"
        )
    ]
