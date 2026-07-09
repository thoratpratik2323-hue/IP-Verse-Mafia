"""
core/config.py — Central configuration manager for IP Prime OS.
Single source of truth for all settings and API keys.
"""

from __future__ import annotations
import json
import os
import sys
from pathlib import Path
from typing import Any


def _get_base() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


class _Config:
    """
    Singleton config accessor.
    Lazily loads api_keys.json and settings.json on first access.
    Falls back to environment variables if keys are missing from file.
    """

    def __init__(self):
        self._base = _get_base()
        self._keys_path = self._base / "config" / "api_keys.json"
        self._settings_path = self._base / "config" / "settings.json"
        self._keys: dict = {}
        self._settings: dict = {}
        self._loaded = False

    def _load(self):
        if self._loaded:
            return
        try:
            if self._keys_path.exists():
                self._keys = json.loads(self._keys_path.read_text(encoding="utf-8"))
        except Exception:
            self._keys = {}
        try:
            if self._settings_path.exists():
                self._settings = json.loads(self._settings_path.read_text(encoding="utf-8"))
        except Exception:
            self._settings = {}
        self._loaded = True

    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting or API key by name. Falls back to env var then default."""
        self._load()
        # Check api_keys first
        if key in self._keys:
            return self._keys[key]
        # Check settings
        if key in self._settings:
            return self._settings[key]
        # Check env variable
        env_val = os.environ.get(key.upper())
        if env_val:
            return env_val
        return default

    def set_setting(self, key: str, value: Any) -> None:
        """Persist a setting to settings.json."""
        self._load()
        self._settings[key] = value
        try:
            self._settings_path.parent.mkdir(exist_ok=True)
            self._settings_path.write_text(
                json.dumps(self._settings, indent=2), encoding="utf-8"
            )
        except Exception as e:
            print(f"[Config] Failed to save setting '{key}': {e}")

    def reload(self):
        """Force reload config from disk."""
        self._loaded = False
        self._load()

    @property
    def base_dir(self) -> Path:
        return self._base

    @property
    def gemini_key(self) -> str:
        return self.get("gemini_api_key", "")

    @property
    def openrouter_key(self) -> str:
        return self.get("openrouter_api_key", "")

    @property
    def nvidia_key(self) -> str:
        return self.get("nvidia_api_key", "")

    @property
    def elevenlabs_key(self) -> str:
        return self.get("elevenlabs_api_key", "")

    @property
    def volume_multiplier(self) -> float:
        return float(self.get("volume_multiplier", 2.0))


# Singleton instance
Config = _Config()
