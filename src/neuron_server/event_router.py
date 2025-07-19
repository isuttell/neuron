import asyncio
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, Literal, Self

from pydantic import BaseModel, Field

from neuron_server.logger import logger
from neuron_server.websocket_session_manager import session_manager


class Event(BaseModel):
    type: str


class IncomingEvent(Event):
    pass


class OutgoingEvent(Event):
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).astimezone().isoformat()
    )


class ErrorEvent(Event):
    type: Literal["error"] = "error"
    message: str


class EventRouter:
    routes: dict[str, tuple[BaseModel, Callable]]

    def __init__(self, routes: dict[str, tuple[BaseModel, Callable]] = None) -> None:
        self.routes = routes or {}

    def on(self, model: type[BaseModel]) -> Callable[[Callable], Callable]:
        def decorator(func: Callable[..., Coroutine]) -> Callable:
            if model.__name__ in self.routes:
                raise ValueError(f"Event type {model.__name__} already registered")
            self.routes[model.__name__] = model, func
            return func

        return decorator

    def register_controller(self, event_router: Self) -> None:
        self.routes.update(event_router.routes)

    async def dispatch(self, event: dict[str, Any]) -> None:
        event_type = event.get("type")
        if not event_type:
            raise ValueError("Event type is required")
        if event_type not in self.routes:
            raise ValueError(f"No route for event type: {event_type}")

        # Extract session context if present
        session_id = event.pop("_session_id", None)
        session = None
        if session_id:
            session = await session_manager.get_session(session_id)

        model, func = self.routes[event_type]
        user_id = session.user_id if session else "unknown"
        logger.debug(f"incoming={event_type} from user={user_id}")

        # Pass session context to the handler
        if session:
            asyncio.create_task(func(model(**event), session=session))
        else:
            # Fallback for handlers without session context
            asyncio.create_task(func(model(**event)))
