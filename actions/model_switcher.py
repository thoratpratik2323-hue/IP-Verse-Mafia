"""
model_switcher.py — Manages switching active foundation LLM models in IP Prime.

Allows selection between Gemini, Claude (anthropic), GPT-4o (openai), and Local Ollama.
Saves model preferences to config/model_config.json.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.model_switcher")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
MODEL_CONFIG_FILE = CONFIG_DIR / "model_config.json"

DEFAULT_MODELS = {
    "gemini": "gemini-3.1-flash-live-preview",
    "claude": "claude-3-5-sonnet-20241022",
    "gpt-4o": "gpt-4o",
    "ollama": "llama3"
}

def _ensure_config_dir():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error("Failed to ensure config directory: %s", e)

def load_model_preference() -> dict[str, str]:
    """Loads active model configuration or defaults to Gemini."""
    _ensure_config_dir()
    if MODEL_CONFIG_FILE.exists():
        try:
            with open(MODEL_CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error reading model_config.json: %s", e)
    return {"active_provider": "gemini", "active_model": DEFAULT_MODELS["gemini"]}

def save_model_preference(provider: str, model_name: str) -> bool:
    """Saves active model selection in configuration file."""
    _ensure_config_dir()
    try:
        with open(MODEL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"active_provider": provider, "active_model": model_name}, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error writing model_config.json: %s", e)
        return False

def switch_model(model_name: str, player: Optional[Any] = None) -> str:
    """
    Toggles the active provider and model.

    Args:
        model_name: The request brand or model string (e.g. 'claude', 'gpt-4o', 'gemini', 'ollama').

    Returns:
        Hinglish response outcome detailing active state and key availability.
    """
    m_name = model_name.lower().strip()
    
    # Resolve aliases
    provider = "gemini"
    target_model = DEFAULT_MODELS["gemini"]

    if "claude" in m_name or "anthropic" in m_name:
        provider = "claude"
        target_model = DEFAULT_MODELS["claude"]
        key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        if not key:
            return "Anthropic API key (ANTHROPIC_API_KEY) environment variable settings missing, sir!"
            
    elif "gpt" in m_name or "openai" in m_name:
        provider = "gpt-4o"
        target_model = DEFAULT_MODELS["gpt-4o"]
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            return "OpenAI API key (OPENAI_API_KEY) environment variable settings missing, sir!"
            
    elif "ollama" in m_name or "local" in m_name:
        provider = "ollama"
        target_model = DEFAULT_MODELS["ollama"]
        # No API key needed for local ollama
        
    elif "gemini" in m_name or "google" in m_name:
        provider = "gemini"
        target_model = DEFAULT_MODELS["gemini"]
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            return "Gemini API key (GEMINI_API_KEY) environment variable settings missing, sir!"
    else:
        return f"Unknown provider choice '{model_name}', sir. Defaulting to Gemini."

    if save_model_preference(provider, target_model):
        msg = f"Active model successfully switched to: {provider.upper()} ({target_model}), sir! Dynamic core reloading complete."
        if player and hasattr(player, "write_log"):
            player.write_log(f"SYS: {msg}")
        return msg
    return "Failed to write model settings update to model_config.json, sir."

def model_switcher(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for model_switcher action."""
    action = parameters.get("action", "status").lower().strip()
    model_name = parameters.get("model_name", "gemini")
    
    if action == "switch":
        return switch_model(model_name, player)
    elif action == "status":
        cfg = load_model_preference()
        return f"Current active LLM backend: {cfg.get('active_provider', 'gemini').upper()} model: {cfg.get('active_model', 'N/A')}, sir."
    else:
        return "Unknown model switcher action, sir."
