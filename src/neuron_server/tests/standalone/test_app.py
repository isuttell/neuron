import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from quart import Blueprint, Quart, current_app, jsonify, request
from werkzeug.exceptions import BadRequest, NotFound

# HTTP status constants
HTTP_OK = 200
HTTP_CREATED = 201
HTTP_NO_CONTENT = 204
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404

# Mock token model
class TokenPayload:
    def __init__(self, user_id, roles=None, permissions=None):
        self.user_id = user_id
        self.roles = roles or []
        self.permissions = permissions or []

# Create a mock scheduler service
class MockScheduler:
    def __init__(self):
        self.events = {}
        
    async def create_event(self, cron, event_data, user_id):
        event_id = "test-event-id"
        self.events[event_id] = {
            "id": event_id,
            "cron": cron,
            "event_data": event_data,
            "user_id": user_id
        }
        return event_id
        
    async def get_event(self, event_id):
        return self.events.get(event_id)
        
    async def update_event(self, event_id, cron=None, event_data=None):
        if event_id in self.events:
            if cron:
                self.events[event_id]["cron"] = cron
            if event_data:
                self.events[event_id]["event_data"] = event_data
                
    async def delete_event(self, event_id):
        if event_id in self.events:
            del self.events[event_id]
            
    async def list_events(self, user_id):
        return [event for event in self.events.values() if event["user_id"] == user_id]

# Mock auth functions
async def get_token_auth_header():
    return "test-token"

async def decode_token(*args, **kwargs):
    return request.auth_token

# Create blueprint for scheduler endpoints
scheduler_bp = Blueprint("scheduler", __name__, url_prefix="/api/scheduler")

@scheduler_bp.route("/events", methods=["POST"])
async def create_event():
    """Create a new scheduled event."""
    if not request.is_json:
        raise BadRequest("Request body is required")
        
    data = await request.get_json()
    
    if not data.get("cron"):
        raise BadRequest("cron is required")
        
    if not data.get("event_data"):
        raise BadRequest("event_data is required")
    
    # Get token for authentication
    token = request.auth_token
    
    # Create the event
    event_id = await current_app.scheduler.create_event(
        cron=data["cron"],
        event_data=data["event_data"],
        user_id=token.user_id,
    )
    
    return jsonify({"event_id": event_id})

@scheduler_bp.route("/events/<event_id>", methods=["PUT"])
async def update_event(event_id):
    """Update an existing scheduled event."""
    if not request.is_json:
        raise BadRequest("Request body is required")
        
    data = await request.get_json()
    
    # Get token for authentication
    token = request.auth_token
    
    # Check if event exists
    event = await current_app.scheduler.get_event(event_id)
    if not event:
        raise NotFound("Event not found")

    # Check if user owns the event
    if event["user_id"] != token.user_id:
        raise NotFound("Event not found")

    # Update the event
    await current_app.scheduler.update_event(
        event_id=event_id,
        cron=data.get("cron"),
        event_data=data.get("event_data"),
    )
    
    return jsonify({"event_id": event_id})

@scheduler_bp.route("/events/<event_id>", methods=["GET"])
async def get_event(event_id):
    """Get details of a specific scheduled event."""
    # Get token for authentication
    token = request.auth_token
    
    # Check if event exists
    event = await current_app.scheduler.get_event(event_id)
    if not event:
        raise NotFound("Event not found")

    # Check if user owns the event
    if event["user_id"] != token.user_id:
        raise NotFound("Event not found")

    return jsonify({"event": event})

@scheduler_bp.route("/events/<event_id>", methods=["DELETE"])
async def delete_event(event_id):
    """Delete a scheduled event."""
    # Get token for authentication
    token = request.auth_token
    
    # Check if event exists
    event = await current_app.scheduler.get_event(event_id)
    if not event:
        raise NotFound("Event not found")

    # Check if user owns the event
    if event["user_id"] != token.user_id:
        raise NotFound("Event not found")

    # Delete the event
    await current_app.scheduler.delete_event(event_id)
    
    return "", HTTP_NO_CONTENT

@scheduler_bp.route("/events", methods=["GET"])
async def list_events():
    """List all scheduled events for the current user."""
    # Get token for authentication
    token = request.auth_token
    
    # Get events for user
    events = await current_app.scheduler.list_events(token.user_id)
    
    # Get personalities for events
    personality_ids = set()
    for event in events:
        event_data = event.get("event_data", {})
        if "personality_id" in event_data:
            personality_ids.add(event_data["personality_id"])
    
    personalities = []
    for pid in personality_ids:
        personalities.append({
            "id": pid,
            "name": f"Test Personality {pid}"
        })
    
    return jsonify({
        "events": events,
        "personalities": personalities
    })

# Setup test fixtures
@pytest.fixture
def app():
    """Create test app with scheduler blueprint."""
    app = Quart(__name__)
    app.register_blueprint(scheduler_bp)
    app.scheduler = MockScheduler()
    
    @app.before_request
    async def add_auth_token():
        if request.headers.get("Authorization", "").startswith("Bearer "):
            # Create mock token
            request.auth_token = TokenPayload(
                user_id="test-user-id",
                roles=["user"],
                permissions=["read:events", "write:events"]
            )
    
    return app

# Tests for scheduler endpoints
@pytest.mark.asyncio
async def test_create_event(app):
    """Test creating a new scheduled event."""
    test_client = app.test_client()
    
    payload = {
        "cron": "0 0 * * *",
        "event_data": {"message": "test", "personality_id": "test-personality-id"}
    }
    
    response = await test_client.post(
        "/api/scheduler/events",
        json=payload,
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == HTTP_OK
    response_data = await response.get_json()
    assert response_data == {"event_id": "test-event-id"}

@pytest.mark.asyncio
async def test_create_event_missing_body(app):
    """Test creating an event with missing body."""
    test_client = app.test_client()
    
    response = await test_client.post(
        "/api/scheduler/events",
        data="",  # Empty body
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == HTTP_BAD_REQUEST

@pytest.mark.asyncio
async def test_update_event(app):
    """Test updating an existing event."""
    test_client = app.test_client()
    app.scheduler.events["test-event-id"] = {
        "id": "test-event-id",
        "cron": "0 0 * * *",
        "event_data": {"message": "test"},
        "user_id": "test-user-id"  # Same as token user_id
    }
    
    payload = {
        "cron": "0 12 * * *",
        "event_data": {"message": "updated test"}
    }
    
    response = await test_client.put(
        "/api/scheduler/events/test-event-id",
        json=payload,
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == HTTP_OK
    response_data = await response.get_json()
    assert response_data == {"event_id": "test-event-id"}

@pytest.mark.asyncio
async def test_update_event_not_found(app):
    """Test updating a non-existent event."""
    test_client = app.test_client()
    
    payload = {
        "cron": "0 12 * * *",
        "event_data": {"message": "updated test"}
    }
    
    response = await test_client.put(
        "/api/scheduler/events/non-existent-id",
        json=payload,
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == HTTP_NOT_FOUND

@pytest.mark.asyncio
async def test_get_event(app):
    """Test getting details of a specific event."""
    test_client = app.test_client()
    event = {
        "id": "test-event-id",
        "cron": "0 0 * * *",
        "event_data": {"message": "test"},
        "user_id": "test-user-id"  # Same as token user_id
    }
    app.scheduler.events["test-event-id"] = event
    
    response = await test_client.get(
        "/api/scheduler/events/test-event-id",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == HTTP_OK
    response_data = await response.get_json()
    assert response_data == {"event": event}

@pytest.mark.asyncio
async def test_delete_event(app):
    """Test deleting an event."""
    test_client = app.test_client()
    app.scheduler.events["test-event-id"] = {
        "id": "test-event-id",
        "cron": "0 0 * * *",
        "event_data": {"message": "test"},
        "user_id": "test-user-id"  # Same as token user_id
    }
    
    response = await test_client.delete(
        "/api/scheduler/events/test-event-id",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == HTTP_NO_CONTENT
    assert "test-event-id" not in app.scheduler.events

@pytest.mark.asyncio
async def test_list_events(app):
    """Test listing all events for the current user."""
    test_client = app.test_client()
    app.scheduler.events["test-event-1"] = {
        "id": "test-event-1",
        "cron": "0 0 * * *",
        "event_data": {"message": "test", "personality_id": "test-personality-id"},
        "user_id": "test-user-id"
    }
    app.scheduler.events["test-event-2"] = {
        "id": "test-event-2",
        "cron": "0 12 * * *",
        "event_data": {"message": "another test", "personality_id": "test-personality-id"},
        "user_id": "test-user-id"
    }
    
    response = await test_client.get(
        "/api/scheduler/events",
        headers={"Authorization": "Bearer test-token"}
    )
    
    assert response.status_code == HTTP_OK
    response_data = await response.get_json()
    assert "events" in response_data
    assert "personalities" in response_data
    assert len(response_data["events"]) == 2
    assert len(response_data["personalities"]) == 1