"""Shared config loader for Prime platform features."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
CONFIG_PATH = BASE_DIR / "config" / "prime_features.json"

_DEFAULT = {
    "local_first": {
        "enabled": False,
        "ollama_url": "http://127.0.0.1:11434",
        "preferred_local_model": "llama3.2",
        "fallback_to_cloud": True,
    },
    "infinite_memory": {
        "enabled": True,
        "max_archive_mb": 512,
        "prompt_recall_turns": 8,
    },
    "realtime": {
        "lean_prompt": True,
        "session_turns_in_prompt": 6,
        "calendar_days_in_prompt": 5,
        "mic_chunk_size": 1024,
        "play_buffer_samples": 1024,
        "low_latency_playback": True,
        "interruption_threshold": 2000,
        "disable_voice_interruption": False,
        "voice_gain": 1.8,
        "preferred_voice": "david",
        "speech_rate": 190,
    },
    "energy_metrics": {
        "enabled": True,
        "gemini_flash_per_1m_tokens_usd": 0.15,
        "gemini_pro_per_1m_tokens_usd": 1.25,
        "estimate_tokens_per_tool_call": 800,
    },
    "messaging": {
        "default_channel": "whatsapp",
    },
    "homelab": {
        "docker_path": "docker",
    },
    "media": {
        "torrent_client": "auto",
    },
    "tauri_desktop": {
        "enabled": False,
        "api_port": 18765,
        "note": "PyQt6 remains primary UI; see desktop-tauri/README.md",
    },
    "workspace": {
        "root": r"C:\\Users\\thora\\.gemini\\antigravity\\scratch\\IP Prime\\CODING PROJECTS",
        "auto_save_all": True,
    },
}


def load_prime_config() -> dict:
    if not CONFIG_PATH.exists():
        save_prime_config(_DEFAULT)
        return json.loads(json.dumps(_DEFAULT))
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        merged = json.loads(json.dumps(_DEFAULT))
        for key, val in data.items():
            if isinstance(val, dict) and isinstance(merged.get(key), dict):
                merged[key].update(val)
            else:
                merged[key] = val
        return merged
    except Exception:
        return json.loads(json.dumps(_DEFAULT))


def save_prime_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
