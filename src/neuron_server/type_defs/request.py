"""Request type definitions."""
from typing import TYPE_CHECKING, Any, Optional

from quart import Request as QuartRequest

if TYPE_CHECKING:
    from neuron_server.controllers.auth import TokenPayload


class NeuronRequest(QuartRequest):
    """Custom request class with authentication token."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.token: Optional[TokenPayload] = None
