"""
IP Prime — Clean Minimal HUD (Simple Glass UI).

Uses ui_simple — a lean, glassmorphic left-orb + right-chat layout.
Default theme: cobalt blue (theme_idx 0).
"""
from __future__ import annotations

import json

from ui_simple import CONFIG_DIR, IPRayUI as _SimpleIPRayUI, _load_theme

# 0 = cobalt blue · 4 = neon cyan-blue (electric orb)
BLUE_THEME_IDX = 0


def _apply_blue_theme() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "theme.json").write_text(
        json.dumps({"theme_idx": BLUE_THEME_IDX}, indent=2),
        encoding="utf-8",
    )
    _load_theme()


class IPRayUI(_SimpleIPRayUI):
    """Public facade for main.py — same API as ui_simple.IPRayUI."""

    def __init__(self, face_path: str, size=None):
        _apply_blue_theme()
        super().__init__(face_path, size)

    def set_speaking_volume(self, vol: float) -> None:
        try:
            self._win.hud.set_voice_level(vol)
        except Exception:
            pass


__all__ = ["IPRayUI"]
