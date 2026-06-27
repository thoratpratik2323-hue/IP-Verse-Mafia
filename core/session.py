"""
core/session.py — IP Prime Gemini session helpers.

Contains the core session utilities extracted from main.py:
  - _get_api_key()          : reads Gemini API key from env var or config file
  - _load_system_prompt()   : builds the full system prompt from prompt.txt + personality.json
  - _clean_transcript()     : sanitises raw transcript text from the live API stream
"""

from __future__ import annotations

import json
import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger("ip_prime.session")

from actions.prime_utils import load_env_file
load_env_file()


# ---------------------------------------------------------------------------
# Path helpers (avoid circular import from path_config by resolving locally)
# ---------------------------------------------------------------------------

def _get_base_dir() -> Path:
    """Return the project root directory, works both frozen and dev mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE_DIR: Path = _get_base_dir()
_API_CONFIG_PATH: Path = _BASE_DIR / "config" / "api_keys.json"
_PROMPT_PATH: Path = _BASE_DIR / "core" / "prompt.txt"
_PERSONALITY_PATH: Path = _BASE_DIR / "config" / "personality.json"

# Compile once — matches stray control tags like <ctrl3>
_CTRL_RE: re.Pattern = re.compile(r"<ctrl\d+>", re.IGNORECASE)


# ---------------------------------------------------------------------------
# API Key
# ---------------------------------------------------------------------------

def _get_api_key() -> str:
    """
    Return the Gemini API key.

    Resolution order:
      1. ``GEMINI_API_KEY`` environment variable (recommended for production)
      2. ``gemini_api_key`` field in ``config/api_keys.json`` (legacy / local dev)

    Raises:
        RuntimeError: If neither source provides a non-empty key.

    Returns:
        The Gemini API key string.
    """
    # Priority 1: Environment variable
    env_key: str = os.environ.get("GEMINI_API_KEY", "").strip()
    if env_key:
        logger.debug("Using GEMINI_API_KEY from environment variable.")
        return env_key

    # Priority 2: config/api_keys.json
    if _API_CONFIG_PATH.exists():
        try:
            with open(_API_CONFIG_PATH, "r", encoding="utf-8") as f:
                data: dict = json.load(f)
            key_from_file: str = data.get("gemini_api_key", "").strip()
            if key_from_file:
                logger.debug("Using gemini_api_key from config/api_keys.json.")
                return key_from_file
        except Exception as e:
            logger.error("Failed to read api_keys.json: %s", e)

    raise RuntimeError(
        "Gemini API key not found. "
        "Set the GEMINI_API_KEY environment variable or add 'gemini_api_key' "
        "to config/api_keys.json."
    )


# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

def _load_system_prompt() -> str:
    """
    Build and return the full system prompt string for the Gemini live session.

    Steps:
      1. Load the base prompt from ``core/prompt.txt``.
      2. Load personality sliders from ``config/personality.json``.
      3. Substitute the AI name throughout the base prompt.
      4. Build an English-only directives block from personality values.
      5. Return the assembled prompt string.

    Returns:
        Full system prompt as a single string.
    """
    # 1. Load base prompt
    base_prompt: str = ""
    try:
        base_prompt = _PROMPT_PATH.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Could not load prompt.txt (%s). Using built-in fallback.", e)
        base_prompt = (
            "You are IP Prime, an advanced personal AI assistant. Your owner is Pratik Thorat. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

    # 2. Load personality configuration
    name: str = "IP Prime"
    humour: int = 50
    energy: int = 60
    sarcasm: int = 30
    prof: int = 80
    creat: int = 75

    if _PERSONALITY_PATH.exists():
        try:
            p_data: dict = json.loads(_PERSONALITY_PATH.read_text(encoding="utf-8"))
            name   = p_data.get("name",            "IP Prime")
            humour = p_data.get("humour",           50)
            energy = p_data.get("energy",           60)
            sarcasm = p_data.get("sarcasm",         30)
            prof   = p_data.get("professionalism",  80)
            creat  = p_data.get("creativity",       75)
        except Exception as e:
            logger.warning("Could not load personality.json (%s). Using defaults.", e)

    # 3. Replace "IP Prime" with the configured name throughout the base prompt
    base_prompt = re.sub(r"\bIP\s+Prime\b", name, base_prompt, flags=re.IGNORECASE)

    # 4. Build English-only personality directives block
    directives: list[str] = []
    directives.append(f"Your custom synthesised core name is: {name}.")
    
    # Check if hacker mode is active
    hacker_mode = False
    try:
        from actions.model_switcher import load_model_preference
        pref = load_model_preference()
        hacker_mode = pref.get("hacker_mode", False)
    except Exception:
        pass
        
    if hacker_mode:
        directives.append(
            "==================================================\n"
            "💀 [HACKER MODE ACTIVE]\n"
            "You are now in Hacker Mode. You are an expert ethical hacker and "
            "cybersecurity professional. You think like an attacker to defend better. "
            "You know CEH, OSCP, and bug bounty methodology. You explain security "
            "concepts clearly, suggest attack vectors on systems the user owns, help "
            "with CTF challenges, and always remind the user that hacking without "
            "permission is illegal. Your tone becomes more technical and precise. "
            "You reference tools like nmap, Burp Suite, Metasploit, Wireshark, and "
            "Kali Linux naturally in your explanations.\n"
            "=================================================="
        )

    directives.append(
        "SPEECH STYLE (MANDATORY): Never say 'ahem', 'ahem ahem', throat-clearing, or dramatic "
        "opening fillers. Start replies directly. No theatrical intros, no 'galaxy-class' hype unless asked."
    )

    # Humour
    if humour > 70:
        directives.append(
            "Humour Level (HIGH): You have an exceptional sense of humour. Be witty, share subtle jokes, "
            "and use light-hearted puns where appropriate. Do not be dry."
        )
    elif humour < 30:
        directives.append(
            "Humour Level (LOW): Your tone must be strictly serious and literal. "
            "No jokes, no puns — maintain absolute literal focus."
        )
    else:
        directives.append(
            f"Humour Level (MODERATE: {humour}%): Balance humour naturally, keeping responses pleasant but focused."
        )

    # Energy
    if energy > 70:
        directives.append(
            "Energy Level (HIGH): Be enthusiastic and helpful, but remain direct — "
            "no filler words, no theatrical intros."
        )
    elif energy < 30:
        directives.append(
            "Energy Level (LOW): You are soft-spoken, calm, composed, and understated. "
            "Maintain a low-energy, serene, stoic demeanour."
        )
    else:
        directives.append(
            f"Energy Level (MODERATE: {energy}%): Maintain a steady, helpful, and pleasant tone."
        )

    # Sarcasm
    if sarcasm > 70:
        directives.append(
            "Sarcasm Level (HIGH): You are exceptionally sarcastic and cheeky! "
            "Deliver clever, playful, and sharp responses — keep it friendly and non-offensive. Use dry wit."
        )
    elif sarcasm < 20:
        directives.append(
            "Sarcasm Level (LOW): You are clean, straightforward, and completely transparent. "
            "No sarcasm, no double-meanings, no irony."
        )
    else:
        directives.append(
            f"Sarcasm Level (MODERATE: {sarcasm}%): Occasional dry wit or playful teasing is fine, "
            "but stay helpful."
        )

    # Professionalism
    if prof > 80:
        directives.append(
            "Professionalism Level (HIGH): You are ultra-professional, structured, refined, and highly respectful. "
            "Treat the user with utmost executive deference."
        )
    elif prof < 40:
        directives.append(
            "Professionalism Level (LOW): Avoid formal styles. Be casual, friendly, "
            "and speak like a peer to the user. No corporate-speak."
        )
    else:
        directives.append(
            f"Professionalism Level (MODERATE: {prof}%): Polite, supportive, and balanced."
        )

    # Creativity
    if creat > 80:
        directives.append(
            "Creativity Level (HIGH): You are immensely creative and a lateral thinker. "
            "Offer unique perspectives, poetic or clever solutions, and highly imaginative brainstorming."
        )
    elif creat < 30:
        directives.append(
            "Creativity Level (LOW): You are strictly logical, methodical, direct, and factual. "
            "Focus only on the most linear, simple, and proven path."
        )
    else:
        directives.append(
            f"Creativity Level (MODERATE: {creat}%): Balanced between creative suggestions and practical execution."
        )

    directives_block: str = "\n".join(directives)

    second_brain_dir = Path.home() / "Documents" / "SecondBrain"
    second_brain_context = ""
    if second_brain_dir.exists():
        try:
            soul_file = second_brain_dir / "SOUL.md"
            user_file = second_brain_dir / "USER.md"
            memory_file = second_brain_dir / "MEMORY.md"
            
            vault_parts = []
            if soul_file.exists():
                vault_parts.append(f"=== SOUL/PERSONA CONFIG ===\n{soul_file.read_text(encoding='utf-8')}\n")
            if user_file.exists():
                vault_parts.append(f"=== USER PROFILE ===\n{user_file.read_text(encoding='utf-8')}\n")
            if memory_file.exists():
                vault_parts.append(f"=== LONG-TERM MEMORY LEDGER ===\n{memory_file.read_text(encoding='utf-8')}\n")
                
            # Load today's log if it exists
            import datetime
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            daily_file = second_brain_dir / "daily" / f"{today_str}.md"
            if daily_file.exists():
                vault_parts.append(f"=== TODAY'S SESSION LOG ({today_str}) ===\n{daily_file.read_text(encoding='utf-8')}\n")
                
            if vault_parts:
                second_brain_context = "\n" + "\n".join(vault_parts)
        except Exception as e:
            logger.warning("Could not load Second Brain files: %s", e)

    # 5. Compile final prompt
    final_prompt: str = (
        "==================================================\n"
        "[DYNAMIC PERSONALITY CORE ACTIVE]\n"
        f"{directives_block}\n"
        "==================================================\n\n"
        f"{base_prompt}"
    )
    if second_brain_context:
        final_prompt += f"\n\n==================================================\n[ACTIVE SECOND BRAIN VAULT CONTEXT]{second_brain_context}==================================================\n"
    return final_prompt


# ---------------------------------------------------------------------------
# Transcript Cleaner
# ---------------------------------------------------------------------------

def _clean_transcript(text: str) -> str:
    """
    Sanitise raw transcript text received from the Gemini live audio stream.

    Removes:
      - Control tags (e.g. ``<ctrl3>``)
      - Raw non-printable ASCII control characters (0x00–0x08, 0x0b–0x1f)
      - Repeated "ahem" throat-clearing artefacts

    Args:
        text: Raw transcript string from the API.

    Returns:
        Cleaned, stripped string.
    """
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    text = re.sub(r"\b(ahem[\s,]*)+", "", text, flags=re.IGNORECASE)
    return text.strip()
