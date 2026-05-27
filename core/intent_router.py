"""
core/intent_router.py — Smart AI Intent Router for IP Prime.

Analyzes user queries to classify if they are coding-related, routing to NVIDIA NIM
or Gemini as appropriate.
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
    
    Uses high-speed keyword matching first (fast path).
    If ambiguous, queries a fast Gemini model to classify the intent.
    """
    if not user_message:
        return False
        
    msg_l = user_message.lower().strip()

    # 1. Fast path: Keyword matching
    for keyword in CODING_KEYWORDS:
        if keyword in msg_l:
            logger.info("[Router] Match found for keyword '%s' (Fast Path -> NVIDIA)", keyword)
            return True

    # 2. Ambiguous path: Gemini flash classification
    logger.info("[Router] No keyword matched. Invoking Gemini intent classification...")
    try:
        from google import genai
        from core.session import _get_api_key
        
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )
        
        prompt = f"Reply only YES or NO. Is this message asking for coding help: '{user_message}'"
        
        # Use gemini-2.5-flash or gemini-2.0-flash as a fast classifier
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        ans = response.text.strip().upper()
        logger.info("[Router] Gemini classifier returned: '%s'", ans)
        return "YES" in ans
        
    except Exception as e:
        logger.warning("[Router] Gemini classification query failed: %s. Defaulting to general path.", e)
        
    return False
