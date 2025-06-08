"""Request proxy for typed access."""
from typing import TYPE_CHECKING, cast

from quart import request as _quart_request

if TYPE_CHECKING:
    from neuron_server.type_defs.auth_request import AuthenticatedRequest

# Export a pre-cast version of request for authenticated endpoints
request = cast("AuthenticatedRequest", _quart_request)
