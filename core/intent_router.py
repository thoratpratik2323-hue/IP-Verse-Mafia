"""
core/intent_router.py — Smart AI Intent Router for IP Prime.

Analyzes user queries to classify if they are coding-related, routing to NVIDIA NIM
or Gemini as appropriate.

NOTE: The Gemini API classify call has been intentionally disabled to preserve
the 1000 req/day free-tier quota. Keyword matching only is sufficient — the
Gemini Live session handles all ambiguous queries natively.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("ip_prime.intent_router")

# Case-insensitive coding keywords list (fast-path matching)
CODING_KEYWORDS = [
    "code", "write a", "debug", "fix this", "error", "function", "class",
    "script", "program", "python", "javascript", "java", "c++", "html",
    "css", "sql", "api", "algorithm", "loop", "variable", "import",
    "library", "module", "compile", "syntax", "exception", "traceback",
    "refactor", "optimize", "implement", "build", "create a function",
    "write me a", "help me code", "what is wrong with", "why is this not working",
    "dev_agent", "code_helper", "run this", "execute", "terminal"
]

def is_coding_task(user_message: str) -> bool:
    """
    Determines if a user query is coding-related.
    
    Uses high-speed keyword matching only (fast path).
    The Gemini API classify call has been disabled to preserve daily quota —
    Gemini Live handles all general/ambiguous queries natively.
    """
    if not user_message:
        return False
        
    msg_l = user_message.lower().strip()

    # Fast path: Keyword matching only (no API call)
    for keyword in CODING_KEYWORDS:
        if keyword in msg_l:
            logger.info("[Router] Match found for keyword '%s' (Fast Path)", keyword)
            return True

    # Default to general path — Gemini Live handles it via the main session
    logger.debug("[Router] No keyword matched. Defaulting to general path (Gemini Live).")
    return False
