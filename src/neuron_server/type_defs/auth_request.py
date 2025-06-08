"""Authenticated request type for use in protected endpoints."""
from typing import TYPE_CHECKING

from neuron_server.type_defs.request import NeuronRequest

if TYPE_CHECKING:
    from neuron_server.controllers.auth import TokenPayload


class AuthenticatedRequest(NeuronRequest):
    """Request type that guarantees token is present."""

    token: "TokenPayload"  # Not optional in authenticated context
