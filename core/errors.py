"""
core/errors.py — Unified error handling for IP Prime OS.
All modules should import and use handle_tool_error() and PrimeError.
"""

from __future__ import annotations
import logging
import traceback
from typing import Any, Callable, TypeVar
from functools import wraps

logger = logging.getLogger("ip_prime")

F = TypeVar("F", bound=Callable[..., Any])


class PrimeError(Exception):
    """Base exception for all IP Prime errors."""
    def __init__(self, tool: str, message: str, original: Exception | None = None):
        self.tool = tool
        self.message = message
        self.original = original
        super().__init__(f"[{tool}] {message}")


class ToolNotFoundError(PrimeError):
    """Raised when a requested tool/action does not exist."""


class APIKeyMissingError(PrimeError):
    """Raised when a required API key is not configured."""


class ToolTimeoutError(PrimeError):
    """Raised when a tool exceeds its time limit."""


def handle_tool_error(tool_name: str, exc: Exception, *, context: str = "") -> str:
    """
    Standard error handler for all tool functions.
    Logs the error and returns a user-friendly Hinglish error string.
    """
    tb = traceback.format_exc()
    logger.error(f"[{tool_name}] Error{' (' + context + ')' if context else ''}: {exc}\n{tb}")
    return f"❌ [{tool_name}] Kuch error aa gaya bhai: {exc}"


def tool_safe(tool_name: str | None = None):
    """
    Decorator: wraps a tool function in try/except and returns
    a formatted error string on failure instead of crashing.

    Usage:
        @tool_safe("my_tool")
        def my_tool(args): ...
    """
    def decorator(fn: F) -> F:
        name = tool_name or fn.__name__
        @wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                return handle_tool_error(name, e)
        return wrapper  # type: ignore
    return decorator


def require_api_key(key_name: str, value: str | None) -> str:
    """
    Validate that an API key is present.
    Raises APIKeyMissingError with a clear message if missing.
    """
    if not value or len(value.strip()) < 8:
        raise APIKeyMissingError(
            key_name,
            f"{key_name} set nahi hai ya invalid hai. "
            f"config/api_keys.json mein add karo."
        )
    return value.strip()
