from pydantic import BaseModel
from quart import Blueprint, Response
from werkzeug.exceptions import BadRequest, NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.type_defs.request_proxy import request

blueprint = Blueprint("scheduler", __name__)


class ScheduleEvent(BaseModel):
    cron: str
    event_data: dict


@blueprint.post("/events")
@requires_auth
@requires_csrf
async def create_event() -> dict[str, str]:
    """Create a new scheduled event"""
    from neuron_server.api import scheduler

    body = await request.get_json()
    if not body:
        raise BadRequest("Request body is required")

    payload = ScheduleEvent(**body)
    event_id = await scheduler.create_event(
        cron=payload.cron,
        event_data=payload.event_data,
        user_id=request.token.user_id,
    )

    return {"event_id": event_id}


@blueprint.put("/events/<event_id>")
@requires_auth
@requires_csrf
async def update_event(event_id: str) -> dict[str, str]:
    """Update an existing scheduled event"""
    from neuron_server.api import scheduler

    body = await request.get_json()
    if not body:
        raise BadRequest("Request body is required")

    payload = ScheduleEvent(**body)
    event = await scheduler.get_event(event_id)
    if not event:
        raise NotFound("Event not found")

    if event["user_id"] != request.token.user_id:
        raise NotFound("Event not found")

    await scheduler.update_event(
        event_id=event_id,
        cron=payload.cron,
        event_data=payload.event_data,
    )

    return {"event_id": event_id}


@blueprint.get("/events/<event_id>")
@requires_auth
async def get_event(event_id: str) -> dict[str, dict]:
    """Get details of a specific scheduled event"""
    from neuron_server.api import scheduler

    event = await scheduler.get_event(event_id)
    if not event:
        raise NotFound("Event not found")

    if event["user_id"] != request.token.user_id:
        raise NotFound("Event not found")

    return {"event": event}


@blueprint.get("/events")
@requires_auth
async def list_events() -> dict[str, list[dict]]:
    """List all scheduled events for the authenticated user"""
    from neuron_server.api import scheduler

    filters = {
        "user_id": request.token.user_id,
    }

    events = await scheduler.list_events(filters=filters)
    personality_ids = {event["event_data"].get("personality_id") for event in events}
    personalities = await PersonalityModel.get_many(personality_ids)

    return {
        "events": events,
        "personalities": [personality.model_dump() for personality in personalities],
    }


@blueprint.delete("/events/<event_id>")
@requires_auth
@requires_csrf
async def delete_event(event_id: str) -> Response:
    """Delete a scheduled event"""
    from neuron_server.api import scheduler

    event = await scheduler.get_event(event_id)
    if not event:
        raise NotFound("Event not found")

    if event["user_id"] != request.token.user_id:
        raise NotFound("Event not found")

    await scheduler.delete_event(event_id)
    return Response(status=204)
