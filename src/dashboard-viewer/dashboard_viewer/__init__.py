"""Dashboard Viewer - A real-time image dashboard with WebSocket updates."""

__version__ = "0.1.0"

from .server import app, main

__all__ = ["app", "main", "__version__"]
