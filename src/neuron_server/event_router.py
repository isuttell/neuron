from typing import Dict, Tuple, Callable, Any, Coroutine
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Self, Literal, Optional
from quart import websocket
from neuron_server.logger import logger


class Event(BaseModel):
    type: str


class IncomingEvent(Event):
    pass


class IncomingLLMEvent(IncomingEvent):
    provider_id: Optional[str] = None


class OutgoingEvent(Event):
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).astimezone().isoformat()
    )


class ErrorEvent(Event):
    type: Literal["error"] = "error"
    message: str


class EventRouter:
    routes: Dict[str, Tuple[BaseModel, Callable]]

    def __init__(self, routes: Dict[str, Tuple[BaseModel, Callable]] = None):
        self.routes = routes or {}

    def on(self, model: BaseModel):
        def decorator(func):
            if model.__name__ in self.routes:
                raise ValueError(f"Event type {model.__name__} already registered")
            self.routes[model.__name__] = model, func
            return func

        return decorator

    def register_controller(self, event_router: Self):
        self.routes.update(event_router.routes)

    async def dispatch(self, event: Dict[str, Any]) -> Coroutine[Any, Any, None]:
        event_type = event.get("type")
        if not event_type:
            raise ValueError("Event type is required")
        if not event_type in self.routes:
            raise ValueError(f"No route for event type: {event_type}")
        model, func = self.routes[event_type]
        try:
            logger.debug(f"incoming={event_type}")
            return await func(model(**event))
        except Exception as e:
            await websocket.send(ErrorEvent(message=str(e)).model_dump_json())
            raise e
