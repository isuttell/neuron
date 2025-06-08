"""Helper functions for type casting."""
from typing import TYPE_CHECKING, cast

from quart import request as quart_request

if TYPE_CHECKING:
    from neuron_server.type_defs.request import NeuronRequest


def get_typed_request() -> "NeuronRequest":
    """Get the current request with proper typing for authenticated endpoints.

    This should only be used within handlers decorated with @requires_auth.

    Returns:
        The current request object typed as NeuronRequest with token attribute.
    """
    return cast("NeuronRequest", quart_request)
