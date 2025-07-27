"""Personality room-related WebSocket events for real-time updates."""

from typing import Literal
from uuid import UUID

from neuron_server.event_router import OutgoingEvent


class PersonalityRoomCreatedEvent(OutgoingEvent):
    """Event sent when a new personality room is created."""

    type: Literal["personality_room_created"] = "personality_room_created"
    personality_id: UUID
    room_id: UUID
    name: str
    room_type: str  # 'private' or 'shared'
    created_by: str | None
    message_count: int


class PersonalityRoomUpdatedEvent(OutgoingEvent):
    """Event sent when a personality room is updated."""

    type: Literal["personality_room_updated"] = "personality_room_updated"
    personality_id: UUID
    room_id: UUID
    name: str
    room_type: str  # 'private' or 'shared'


class PersonalityRoomDeletedEvent(OutgoingEvent):
    """Event sent when a personality room is deleted."""

    type: Literal["personality_room_deleted"] = "personality_room_deleted"
    personality_id: UUID
    room_id: UUID


class UserJoinedPersonalityRoomEvent(OutgoingEvent):
    """Event sent when a user is added to a personality room."""

    type: Literal["user_joined_personality_room"] = "user_joined_personality_room"
    personality_id: UUID
    room_id: UUID
    user_id: str
    role: str  # 'admin' or 'user'


class UserLeftPersonalityRoomEvent(OutgoingEvent):
    """Event sent when a user is removed from a personality room."""

    type: Literal["user_left_personality_room"] = "user_left_personality_room"
    personality_id: UUID
    room_id: UUID
    user_id: str


class PersonalityRoomDataEvent(OutgoingEvent):
    """Event sent to a user with complete room data when they are added to a room."""

    type: Literal["personality_room_data"] = "personality_room_data"
    personality_room: dict
    personality_room_users: list[dict]
    users: list[dict]
