"""
IP Prime — native PyQt HUD (reactive star orb + neural layout).

Uses ui_core HudCanvas — morphing blob orb from ip-ray.
Default theme: cobalt blue (theme_idx 0).
"""
from __future__ import annotations

import json

from ui_core import CONFIG_DIR, IPRayUI as _CoreIPRayUI, _load_theme

# 0 = cobalt blue · 4 = neon cyan-blue (electric orb)
BLUE_THEME_IDX = 0


def _apply_blue_theme() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "theme.json").write_text(
        json.dumps({"theme_idx": BLUE_THEME_IDX}, indent=2),
        encoding="utf-8",
    )
    _load_theme()


class IPRayUI(_CoreIPRayUI):
    """Public facade for main.py — same API as ui_core.IPRayUI."""

    def __init__(self, face_path: str, size=None):
        _apply_blue_theme()
        super().__init__(face_path, size)

    def set_speaking_volume(self, vol: float) -> None:
        try:
            self._win.hud.set_voice_level(vol)
        except Exception:
            pass


__all__ = ["IPRayUI"]
