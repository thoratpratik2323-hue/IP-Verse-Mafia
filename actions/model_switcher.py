"""
model_switcher.py — Manages switching active foundation LLM models and smart routing settings in IP Prime.

Allows selection between Gemini, Claude (anthropic), GPT-4o (openai), and Local Ollama,
as well as configuring NVIDIA NIM smart routing overrides.
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
    "ollama": "llama3",
    "freellmapi": "gemini-2.5-flash"
}

def _ensure_config_dir():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error("Failed to ensure config directory: %s", e)

def load_model_preference() -> dict[str, Any]:
    """Loads active model configuration or defaults to Gemini with smart routing configuration."""
    _ensure_config_dir()
    default_data = {
        "active_provider": "gemini",
        "active_model": DEFAULT_MODELS["gemini"],
        "routing_mode": "auto",
        "coding_model": "nvidia/llama-3.1-nemotron-70b-instruct"
    }
    if MODEL_CONFIG_FILE.exists():
        try:
            with open(MODEL_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in default_data.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception as e:
            logger.error("Error reading model_config.json: %s", e)
    return default_data

def save_model_preference_dict(data: dict[str, Any]) -> bool:
    """Saves complete model selection dictionary in configuration file."""
    _ensure_config_dir()
    try:
        with open(MODEL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logger.error("Error writing model_config.json: %s", e)
        return False

def save_model_preference(provider: str, model_name: str) -> bool:
    """Saves active model selection in configuration file."""
    cfg = load_model_preference()
    cfg["active_provider"] = provider
    cfg["active_model"] = model_name
    return save_model_preference_dict(cfg)

def force_nvidia(player: Optional[Any] = None) -> str:
    """Forces all query responses through NVIDIA NIM models until reset."""
    cfg = load_model_preference()
    cfg["routing_mode"] = "nvidia"
    if save_model_preference_dict(cfg):
        msg = "IP Prime will now route all queries to NVIDIA NIM, sir!"
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: Routing mode forced to NVIDIA.")
        if player and hasattr(player, "set_router_badge"):
            player.set_router_badge("NVIDIA")
        return msg
    return "Failed to save configuration update, sir."

def force_freellmapi(player: Optional[Any] = None) -> str:
    """Forces all query responses through FreeLLMAPI until reset."""
    cfg = load_model_preference()
    cfg["routing_mode"] = "freellmapi"
    if save_model_preference_dict(cfg):
        msg = "IP Prime will now route all queries to FreeLLMAPI, sir!"
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: Routing mode forced to FreeLLMAPI.")
        if player and hasattr(player, "set_router_badge"):
            player.set_router_badge("FREELLM")
        return msg
    return "Failed to save configuration update, sir."

def force_gemini(player: Optional[Any] = None) -> str:
    """Forces all query responses through Gemini until reset."""
    cfg = load_model_preference()
    cfg["routing_mode"] = "gemini"
    if save_model_preference_dict(cfg):
        msg = "IP Prime will now route all queries to Gemini, sir."
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: Routing mode forced to Gemini.")
        if player and hasattr(player, "set_router_badge"):
            player.set_router_badge("Gemini")
        return msg
    return "Failed to save configuration update, sir."

def auto_route(player: Optional[Any] = None) -> str:
    """Restores smart automatic routing mode."""
    cfg = load_model_preference()
    cfg["routing_mode"] = "auto"
    if save_model_preference_dict(cfg):
        msg = "Smart automatic routing successfully restored, sir!"
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: Smart routing mode enabled.")
        if player and hasattr(player, "set_router_badge"):
            player.set_router_badge("Gemini")
        return msg
    return "Failed to save configuration update, sir."

def set_coding_model(model_name: str, player: Optional[Any] = None) -> str:
    """Changes which NVIDIA model is used for coding."""
    clean_model = model_name.strip()
    
    # Check if a simple name was passed, map it
    mapping = {
        "codellama": "meta/codellama-70b",
        "codestral": "mistralai/codestral-22b-instruct-v0.1",
        "codegemma": "google/codegemma-7b",
        "nemotron": "nvidia/llama-3.1-nemotron-70b-instruct",
        "llama": "nvidia/llama-3.1-nemotron-70b-instruct"
    }
    
    resolved = clean_model
    for k, v in mapping.items():
        if k in clean_model.lower():
            resolved = v
            break
            
    cfg = load_model_preference()
    cfg["coding_model"] = resolved
    if save_model_preference_dict(cfg):
        msg = f"NVIDIA coding model changed to: {resolved}, sir!"
        if player and hasattr(player, "write_log"):
            player.write_log(f"SYS: Coding model updated: {resolved}")
        return msg
    return "Failed to save coding model preferences, sir."

def switch_model(model_name: str, player: Optional[Any] = None) -> str:
    """
    Toggles the active provider and model.
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
        
    elif "freellmapi" in m_name or "freeapi" in m_name:
        provider = "freellmapi"
        target_model = DEFAULT_MODELS["freellmapi"]
        if "/" in model_name:
            target_model = model_name.split("/", 1)[1]
            
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

def enable_hacker_mode(player: Optional[Any] = None) -> str:
    """Activates Hacker Mode personality and status overlays."""
    cfg = load_model_preference()
    cfg["hacker_mode"] = True
    if save_model_preference_dict(cfg):
        msg = "💀 Hacker Mode successfully activated, sir! Security protocols engaged."
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: Hacker Mode enabled.")
        if player and hasattr(player, "set_router_badge"):
            player.set_router_badge("HACKER")
        if player and hasattr(player, "trigger_personality_reload_and_greeting"):
            player.trigger_personality_reload_and_greeting()
        return msg
    return "Failed to save configuration update, sir."

def disable_hacker_mode(player: Optional[Any] = None) -> str:
    """Deactivates Hacker Mode personality and restores default settings."""
    cfg = load_model_preference()
    cfg["hacker_mode"] = False
    if save_model_preference_dict(cfg):
        msg = "Hacker Mode deactivated, sir. Back to standard operations."
        if player and hasattr(player, "write_log"):
            player.write_log("SYS: Hacker Mode disabled.")
        if player and hasattr(player, "set_router_badge"):
            player.set_router_badge("Gemini")
        if player and hasattr(player, "trigger_personality_reload_and_greeting"):
            player.trigger_personality_reload_and_greeting()
        return msg
    return "Failed to save configuration update, sir."

def model_switcher(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for model_switcher action."""
    action = parameters.get("action", "status").lower().strip()
    model_name = parameters.get("model_name", "gemini")
    
    if action == "switch":
        return switch_model(model_name, player)
    elif action == "status":
        cfg = load_model_preference()
        return f"Current active LLM backend: {cfg.get('active_provider', 'gemini').upper()} model: {cfg.get('active_model', 'N/A')}, sir."
    elif action == "force_nvidia":
        return force_nvidia(player)
    elif action == "force_freellmapi" or action == "force_free":
        return force_freellmapi(player)
    elif action == "force_gemini":
        return force_gemini(player)
    elif action == "auto_route":
        return auto_route(player)
    elif action == "set_coding_model":
        return set_coding_model(model_name, player)
    elif action == "enable_hacker":
        return enable_hacker_mode(player)
    elif action == "disable_hacker":
        return disable_hacker_mode(player)
    else:
        return "Unknown model switcher action, sir."
