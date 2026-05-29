"""
core/nvidia_client.py — OpenAI-compatible NVIDIA NIM API client for IP Prime.

Connects to https://integrate.api.nvidia.com/v1 to stream high-performance code generation
results utilizing environment key NVIDIA_API_KEY.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("ip_prime.nvidia_client")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
MODEL_CONFIG_FILE = CONFIG_DIR / "model_config.json"

DEFAULT_CODING_MODEL = "nvidia/llama-3.1-nemotron-70b-instruct"
SUPPORTED_CODING_MODELS = [
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "meta/codellama-70b",
    "mistralai/codestral-22b-instruct-v0.1",
    "google/codegemma-7b"
]

def _ensure_config_dir():
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error("Failed to ensure config directory: %s", e)

def get_coding_model() -> str:
    """Loads configured coding model or defaults to nemotron."""
    if MODEL_CONFIG_FILE.exists():
        try:
            with open(MODEL_CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("coding_model", DEFAULT_CODING_MODEL)
        except Exception as e:
            logger.error("Failed reading model_config.json coding_model: %s", e)
    return DEFAULT_CODING_MODEL

def set_coding_model_preference(model_name: str) -> bool:
    """Saves coding model preference to configuration."""
    _ensure_config_dir()
    try:
        existing = {}
        if MODEL_CONFIG_FILE.exists():
            with open(MODEL_CONFIG_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        
        existing["coding_model"] = model_name
        with open(MODEL_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=4)
        return True
    except Exception as e:
        logger.error("Failed writing coding model preference: %s", e)
    return False

def ask_nvidia(prompt: str, system_prompt: str = "", model: str = None) -> str:
    """
    Queries NVIDIA NIM API or FreeLLMAPI utilizing streaming chunks for high response speed.
    """
    try:
        with open(CONFIG_DIR / "api_keys.json", "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception:
        config = {}

    provider = config.get("coding_provider", "nvidia").lower()

    if provider == "freellmapi":
        base_url = config.get("coding_base_url", "http://localhost:3000/v1")
        api_key = config.get("coding_api_key") or "freellmapi-key"
        target_model = model or config.get("coding_model", "gemini-2.5-flash")
        logger.info("Routing query to FreeLLMAPI utilizing model: %s", target_model)
    else:
        base_url = "https://integrate.api.nvidia.com/v1"
        api_key = os.environ.get("NVIDIA_API_KEY", "").strip()
        if not api_key:
            api_key = (config.get("coding_api_key") or config.get("gemini_api_key") or "").strip()
        if not api_key:
            raise ValueError("NVIDIA_API_KEY not set. Add it to your environment variables.")
        target_model = model or get_coding_model()
        logger.info("Routing query to NVIDIA NIM utilizing model: %s", target_model)

    try:
        from openai import OpenAI
        client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        completion = client.chat.completions.create(
            model=target_model,
            messages=messages,
            stream=True
        )

        collected_chunks = []
        for chunk in completion:
            content = chunk.choices[0].delta.content
            if content:
                collected_chunks.append(content)
                # Flush chunk dynamically if terminal logging active
                print(content, end="", flush=True)
        
        print() # trailing newline
        return "".join(collected_chunks).strip()

    except Exception as e:
        logger.error("NVIDIA NIM query failed: %s", e)
        raise RuntimeError(f"NVIDIA NIM query error: {e}")
