"""
IP Prime — Clean Minimal HUD (Simple Glass UI).

Uses ui_simple — a lean, glassmorphic left-orb + right-chat layout.
Default theme: cobalt blue (theme_idx 0).
"""
from __future__ import annotations

import json
import sys
import atexit

from ui_simple import CONFIG_DIR, _load_theme

# 0 = cobalt blue · 4 = neon cyan-blue (electric orb)
BLUE_THEME_IDX = 0


def _apply_blue_theme() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "theme.json").write_text(
        json.dumps({"theme_idx": BLUE_THEME_IDX}, indent=2),
        encoding="utf-8",
    )
    _load_theme()


# Dynamically select UI skin
if "--sat-mode" in sys.argv or "--orb-skin" in sys.argv:
    from ui_sat import IPRayUI as _SelectedIPRayUI
    print("[IP PRIME] 🔮 Loading Saturday Orb UI skin...")
else:
    from ui_simple import IPRayUI as _SelectedIPRayUI


class IPRayUI(_SelectedIPRayUI):
    """Public facade for main.py — same API as ui_simple.IPRayUI."""

    def __init__(self, face_path: str, size=None):
        _apply_blue_theme()
        super().__init__(face_path, size)
        
        # Check if launching in OS mode
        if "--os-mode" in sys.argv or "--os" in sys.argv:
            try:
                from os_shell.desktop import IPPrimeOSDesktop
                from os_shell.shell_manager import show_windows_taskbar
                
                print("[IP PRIME] 🖥️ Booting in IP Prime OS Shell mode...")
                # Pass self (the IPRayUI instance) so desktop can control/toggle system states
                self._os_desktop = IPPrimeOSDesktop(face_path, ui_facade=self)
                self._os_desktop.show()
                
                # Ensure taskbar is restored on shutdown
                atexit.register(show_windows_taskbar)
            except Exception as e:
                print(f"[IP PRIME OS Error] Failed to boot OS shell: {e}")
                import traceback
                traceback.print_exc()

    def set_state(self, state: str):
        super().set_state(state)
        # Update the desktop orb visual state
        if hasattr(self, "_os_desktop") and self._os_desktop:
            self._os_desktop.set_orb_state(state)

    def set_speaking_volume(self, vol: float) -> None:
        try:
            self._win.hud.set_voice_level(vol)
        except Exception:
            pass

    def write_log(self, text: str):
        super().write_log(text)
        if hasattr(self, "_os_desktop") and self._os_desktop:
            clean_text = text.strip()
            if not clean_text:
                return
            
            if clean_text.startswith("You (Quiet Mode Command):"):
                msg = clean_text[len("You (Quiet Mode Command):"):].strip()
                self._os_desktop.add_conversation_line("User", msg)
            elif clean_text.startswith("You:"):
                msg = clean_text[len("You:"):].strip()
                self._os_desktop.add_conversation_line("User", msg)
            elif clean_text.startswith("IP Prime"):
                parts = clean_text.split(":", 1)
                if len(parts) > 1:
                    self._os_desktop.add_conversation_line("Prime", parts[1].strip())
                else:
                    self._os_desktop.add_conversation_line("Prime", clean_text)
            elif clean_text.startswith("SYS:"):
                msg = clean_text[len("SYS:"):].strip()
                if not msg.startswith("Fallback Engine"):
                    self._os_desktop.add_conversation_line("System", msg)
            else:
                self._os_desktop.add_conversation_line("System", clean_text)


def get_ui():
    try:
        import ui_sat
        return ui_sat.get_ui()
    except Exception:
        return None


def get_main_window():
    u = get_ui()
    if u and hasattr(u, "_win"):
        return u._win
    return None


__all__ = ["IPRayUI", "get_ui", "get_main_window"]


