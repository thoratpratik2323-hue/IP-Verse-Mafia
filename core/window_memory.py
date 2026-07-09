"""
core/window_memory.py — Persistent Window Position & Size Memory.
Saves all GlassWindow positions/sizes to memory/window_layout.json.
Windows restore their last position on startup.

Usage:
    from core.window_memory import WindowMemory
    # On close: WindowMemory.save(windows_dict)
    # On arrange: WindowMemory.restore(windows_dict) -> True if positions loaded
"""

from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("window_memory")
LAYOUT_PATH = Path("memory/window_layout.json")


class _WindowMemory:
    """Persist and restore window positions across sessions."""

    def __init__(self):
        LAYOUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict:
        try:
            if LAYOUT_PATH.exists():
                return json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            logger.debug(f"[WindowMemory] Load failed: {e}")
        return {}

    def save(self, windows: dict) -> None:
        """
        Snapshot all current window positions and sizes.
        Call this when the app is closing or user moves a window.

        Args:
            windows: dict of {key: GlassWindow} from desktop.windows
        """
        layout: dict[str, dict] = {}
        for key, win in windows.items():
            if win is None:
                continue
            try:
                pos  = win.pos()
                size = win.size()
                layout[key] = {
                    "x": pos.x(),
                    "y": pos.y(),
                    "w": size.width(),
                    "h": size.height(),
                    "visible": win.isVisible(),
                }
            except Exception:
                pass
        self._data = layout
        try:
            LAYOUT_PATH.write_text(json.dumps(layout, indent=2), encoding="utf-8")
            logger.debug(f"[WindowMemory] Saved {len(layout)} windows.")
        except Exception as e:
            logger.warning(f"[WindowMemory] Save failed: {e}")

    def restore(self, windows: dict) -> bool:
        """
        Restore saved positions/sizes to glass windows.
        Returns True if any positions were restored.

        Args:
            windows: dict of {key: GlassWindow}
        """
        if not self._data:
            return False
        restored = 0
        for key, win in windows.items():
            if win is None or key not in self._data:
                continue
            try:
                d = self._data[key]
                win.move(d["x"], d["y"])
                win.resize(d["w"], d["h"])
                # Restore visibility
                if not d.get("visible", True):
                    win.hide_window()
                restored += 1
            except Exception as e:
                logger.debug(f"[WindowMemory] Restore failed for '{key}': {e}")
        logger.info(f"[WindowMemory] Restored {restored}/{len(windows)} windows.")
        return restored > 0

    def has_saved_layout(self) -> bool:
        return bool(self._data)

    def clear(self) -> None:
        """Delete saved layout (resets to default positions)."""
        self._data = {}
        try:
            LAYOUT_PATH.unlink(missing_ok=True)
        except Exception:
            pass


# Singleton
WindowMemory = _WindowMemory()
