"""Utility functions for graph operations."""

import hashlib


def encode_md5(text: str) -> str:
    """Convert a string to an MD5 hash."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()
