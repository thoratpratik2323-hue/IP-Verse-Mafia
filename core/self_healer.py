"""
core/self_healer.py — Auto-retry engine for failed tool calls.
When a tool returns an error, analyses the failure and attempts recovery.
"""

from __future__ import annotations
import logging
import time
from typing import Callable, Any

logger = logging.getLogger("self_healer")

# Error patterns and their retry strategies
_RETRY_STRATEGIES: dict[str, str] = {
    "timeout":       "Increase timeout and retry with smaller input",
    "rate limit":    "Wait 10 seconds and retry with lower model",
    "api key":       "Check api_keys.json configuration",
    "network":       "Check internet connection and retry",
    "not found":     "Verify file/path exists before retrying",
    "permission":    "Run as administrator or check file permissions",
    "json":          "Parse raw output differently",
}

_MAX_RETRIES = 2
_BACKOFF_SECONDS = [2, 5]  # Wait before each retry


class SelfHealer:
    """Wraps tool calls with automatic retry and recovery logic."""

    def __init__(self, ai_callback: Callable[[str], str] | None = None):
        """
        ai_callback: optional function to ask AI for a fix suggestion.
        Signature: (error_description: str) -> suggested_action: str
        """
        self._ai = ai_callback
        self._failure_log: list[dict] = []

    def run_with_healing(
        self,
        fn: Callable[..., Any],
        *args,
        tool_name: str = "unknown",
        **kwargs
    ) -> Any:
        """
        Execute fn(*args, **kwargs) with auto-retry on failure.
        Returns the result or a formatted error string.
        """
        last_error = None
        for attempt in range(1, _MAX_RETRIES + 2):
            try:
                result = fn(*args, **kwargs)
                if isinstance(result, str) and result.startswith("❌"):
                    raise RuntimeError(f"Tool returned error: {result}")
                if attempt > 1:
                    logger.info(f"[SelfHealer] ✓ {tool_name} recovered on attempt {attempt}")
                return result
            except Exception as e:
                last_error = e
                self._log_failure(tool_name, e, attempt)
                if attempt <= _MAX_RETRIES:
                    strategy = self._get_strategy(str(e))
                    logger.warning(
                        f"[SelfHealer] {tool_name} failed (attempt {attempt}): {e}. "
                        f"Strategy: {strategy}. Retrying in {_BACKOFF_SECONDS[attempt-1]}s…"
                    )
                    time.sleep(_BACKOFF_SECONDS[attempt - 1])

        logger.error(f"[SelfHealer] {tool_name} failed after {_MAX_RETRIES + 1} attempts: {last_error}")
        return f"❌ [{tool_name}] {_MAX_RETRIES + 1} attempts ke baad bhi fail hua: {last_error}"

    def _get_strategy(self, error_text: str) -> str:
        error_lower = error_text.lower()
        for pattern, strategy in _RETRY_STRATEGIES.items():
            if pattern in error_lower:
                return strategy
        return "Retry with same parameters"

    def _log_failure(self, tool_name: str, error: Exception, attempt: int):
        self._failure_log.append({
            "tool": tool_name,
            "error": str(error),
            "attempt": attempt,
        })
        # Keep only last 100 failures
        if len(self._failure_log) > 100:
            self._failure_log = self._failure_log[-100:]

    def get_failure_report(self) -> list[dict]:
        """Return recent failure log for proactive suggestions."""
        return self._failure_log[-10:]

    def most_failing_tools(self, top_n: int = 5) -> list[str]:
        from collections import Counter
        counts = Counter(f["tool"] for f in self._failure_log)
        return [tool for tool, _ in counts.most_common(top_n)]


# Singleton
Healer = SelfHealer()
