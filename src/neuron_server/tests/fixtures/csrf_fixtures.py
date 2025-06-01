"""CSRF test fixtures"""
from functools import wraps
from typing import Callable, TypeVar
from unittest.mock import patch

import pytest

T = TypeVar("T")


def bypass_csrf_decorator(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that bypasses CSRF check for testing."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await func(*args, **kwargs)
    return wrapper


@pytest.fixture(autouse=True)
def mock_csrf_decorator():
    """Mock the requires_csrf decorator to bypass CSRF checks in tests."""
    with patch(
        "neuron_server.controllers.csrf.requires_csrf",
        side_effect=bypass_csrf_decorator
    ):
        yield
