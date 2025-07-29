"""Room-related WebSocket events for real-time messaging."""

from typing import Literal
from uuid import UUID

from neuron_server.event_router import IncomingEvent, OutgoingEvent


class JoinRoom(IncomingEvent):
    """Event to join a room."""

    room_type: str
    room_id: str


class LeaveRoom(IncomingEvent):
    """Event to leave a room."""

    room_type: str
    room_id: str


class JoinPersonalityRoom(IncomingEvent):
    """Event to join a personality chat room."""

    personality_id: UUID
    room_id: UUID


class LeavePersonalityRoom(IncomingEvent):
    """Event to leave a personality chat room."""

    personality_id: UUID
    room_id: UUID


class RoomJoinedEvent(OutgoingEvent):
    """Event sent when user successfully joins a room."""

    type: Literal["room_joined"] = "room_joined"
    room_type: str
    room_id: str
    member_count: int


class RoomLeftEvent(OutgoingEvent):
    """Event sent when user successfully leaves a room."""

    type: Literal["room_left"] = "room_left"
    room_type: str
    room_id: str


class UserJoinedRoomEvent(OutgoingEvent):
    """Event sent to other room members when a user joins."""

    type: Literal["user_joined_room"] = "user_joined_room"
    room_type: str
    room_id: str
    user_id: str
    nickname: str


class UserLeftRoomEvent(OutgoingEvent):
    """Event sent to other room members when a user leaves."""

    type: Literal["user_left_room"] = "user_left_room"
    room_type: str
    room_id: str
    user_id: str
    nickname: str
