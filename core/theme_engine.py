"""
core/theme_engine.py — JSON-based Theme Engine for IP Prime OS.
Loads themes from themes/*.json and applies them to the desktop.
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("theme_engine")
THEMES_DIR = Path(__file__).resolve().parent.parent / "themes"


class ThemeEngine:
    """Load and apply JSON themes to IP Prime desktop."""

    def __init__(self):
        self._themes: dict[str, dict] = {}
        self._current: str = "Slate Dark"
        self._load_all()

    def _load_all(self):
        THEMES_DIR.mkdir(exist_ok=True)
        for path in sorted(THEMES_DIR.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                name = data.get("name", path.stem)
                self._themes[name] = data
                logger.debug(f"[ThemeEngine] Loaded theme: {name}")
            except Exception as e:
                logger.warning(f"[ThemeEngine] Failed to load {path.name}: {e}")

    def available(self) -> list[str]:
        return list(self._themes.keys())

    def get(self, name: str) -> dict[str, Any]:
        return self._themes.get(name, self._themes.get("Slate Dark", {}))

    def current(self) -> dict[str, Any]:
        return self.get(self._current)

    def switch(self, name: str) -> dict[str, Any]:
        if name in self._themes:
            self._current = name
            logger.info(f"[ThemeEngine] Switched to: {name}")
            return self._themes[name]
        logger.warning(f"[ThemeEngine] Theme '{name}' not found. Available: {self.available()}")
        return self.current()

    def reload(self):
        """Hot-reload themes from disk (no restart needed)."""
        self._themes.clear()
        self._load_all()

    def save_custom(self, name: str, theme_dict: dict):
        """Save a custom theme to themes/ directory."""
        safe_name = name.lower().replace(" ", "_")
        path = THEMES_DIR / f"{safe_name}.json"
        theme_dict["name"] = name
        path.write_text(json.dumps(theme_dict, indent=2))
        self._themes[name] = theme_dict
        logger.info(f"[ThemeEngine] Saved custom theme: {name}")


# Singleton
Themes = ThemeEngine()
