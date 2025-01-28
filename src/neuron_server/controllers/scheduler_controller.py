import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from quart import Blueprint, jsonify, request

from neuron_server.controllers.auth import requires_auth
from neuron_server.models import PersonalityModel
from neuron_server.util.scheduler import RecurringPattern

logger = logging.getLogger(__name__)

blueprint = Blueprint("scheduler", __name__)


@blueprint.post("/events")
@requires_auth
async def create_event():
    """Create a new scheduled event"""
    from neuron_server.api import scheduler

    data = await request.get_json()

    # Parse recurring pattern if provided
    recurring_pattern: RecurringPattern | None = None
    if pattern_data := data.get("recurring_pattern"):
        recurring_pattern = RecurringPattern(**pattern_data)

    # Parse trigger time if provided
    trigger_time: datetime | None = None
    if time_str := data.get("trigger_time"):
        trigger_time = datetime.fromisoformat(time_str)

    event_id = str(uuid4())

    # Schedule the event
    await scheduler.schedule_event(
        event_id=event_id,
        event_data={
            # First add the additional data so it can't override the other fields
            **data.get("additional_data", {}),
            "prompt": data["prompt"],
            "thread_id": data.get("thread_id"),
            "personality_id": data["personality_id"],
            "user_id": request.token.user_id,
            "username": request.token.username,
        },
        trigger_time=trigger_time,
        recurring_pattern=recurring_pattern,
    )

    return jsonify({"event_id": event_id, "status": "created"}), 201


@blueprint.put("/events/<event_id>")
@requires_auth
async def update_event(event_id: str):
    """Update an existing scheduled event"""
    from neuron_server.api import scheduler

    data = await request.get_json()

    # Parse recurring pattern if provided
    recurring_pattern: RecurringPattern | None = None
    if pattern_data := data.get("recurring_pattern"):
        recurring_pattern = RecurringPattern(**pattern_data)

    # Parse trigger time if provided
    trigger_time: datetime | None = None
    if time_str := data.get("trigger_time"):
        trigger_time = datetime.fromisoformat(time_str)

    # Get current event to verify ownership
    current_event = await scheduler.get_event(event_id)
    if not current_event:
        return jsonify({"error": "Event not found"}), 404

    if current_event["event_data"]["user_id"] != request.token.user_id:
        return jsonify({"error": "Unauthorized"}), 403

    # Update the event
    await scheduler.update_event(
        event_id=event_id,
        new_data=data.get("event_data"),
        new_trigger_time=trigger_time,
        new_recurring_pattern=recurring_pattern,
    )

    return jsonify({"status": "updated"})


@blueprint.get("/events/<event_id>")
@requires_auth
async def get_event(event_id: str):
    """Get details of a specific scheduled event"""
    from neuron_server.api import scheduler

    event = await scheduler.get_event(event_id)
    if not event:
        return jsonify({"error": "Event not found"}), 404

    if event["event_data"]["user_id"] != request.token.user_id:
        return jsonify({"error": "Unauthorized"}), 403

    if personality_id := event["event_data"].get("personality_id"):
        personality = await PersonalityModel.get(personality_id)
        return jsonify(
            {
                "events": [event],
                "personalities": [personality.model_dump()] if personality else [],
            }
        )
    return jsonify({"events": [event]})


@blueprint.get("/events")
@requires_auth
async def list_events():
    """List all scheduled events for the authenticated user"""
    from neuron_server.api import scheduler

    filters: dict[str, Any] = {"user_id": request.token.user_id}

    # Add any additional filters from query parameters
    for key, value in request.args.items():
        if key not in ["user_id"]:
            filters[key] = value

    events = await scheduler.list_events(filters=filters)
    personality_ids = list(
        set(event["event_data"].get("personality_id") for event in events)
    )
    personalities = await PersonalityModel.get_many(personality_ids)

    return jsonify(
        {
            "events": events,
            "personalities": [
                personality.model_dump() for personality in personalities
            ],
        }
    )


@blueprint.delete("/events/<event_id>")
@requires_auth
async def delete_event(event_id: str):
    """Delete a scheduled event"""
    from neuron_server.api import scheduler

    # Get current event to verify ownership
    current_event = await scheduler.get_event(event_id)
    if not current_event:
        return jsonify({"error": "Event not found"}), 404

    if current_event["event_data"]["user_id"] != request.token.user_id:
        return jsonify({"error": "Unauthorized"}), 403

    success = await scheduler.delete_event(event_id)
    if success:
        return jsonify({"status": "deleted"})
    return jsonify({"error": "Failed to delete event"}), 500
