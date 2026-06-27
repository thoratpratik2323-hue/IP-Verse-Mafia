"""
os_shell_windows/kiosk.py
===========================
"SaturdayOS Mode" — turns the SATURDAY console you already built into a
full, taskbar-free "operating system" experience, WITHOUT touching
Windows itself. No VM. No dual-boot. No second OS. Just this one window
taking over the entire screen so it *feels* like SATURDAY booted its own
world inside your PC.

Toggle with F9 (bound in ui.py). Calling enter()/exit() again reverses it.

Safety first: there is always a way out.
  - Pressing F9 again (or Esc, also bound) restores Windows exactly as
    it was.
  - `atexit` guarantees the taskbar comes back even if SATURDAY crashes
    while SaturdayOS Mode is on — you're never left with a permanently
    hidden taskbar.
"""

from __future__ import annotations

import sys
import atexit

_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import ctypes

    _user32 = ctypes.windll.user32
    _SW_HIDE = 0
    _SW_SHOW = 5

    def _taskbar_hwnd():
        return _user32.FindWindowW("Shell_TrayWnd", None)

    def hide_taskbar() -> bool:
        hwnd = _taskbar_hwnd()
        if hwnd:
            _user32.ShowWindow(hwnd, _SW_HIDE)
            return True
        return False

    def show_taskbar() -> bool:
        hwnd = _taskbar_hwnd()
        if hwnd:
            _user32.ShowWindow(hwnd, _SW_SHOW)
            return True
        return False
else:
    # macOS/Linux use different mechanisms (Dock hiding / WM hints) —
    # out of scope for this Windows-first pass. Calls are safe no-ops.
    def hide_taskbar() -> bool:
        return False

    def show_taskbar() -> bool:
        return False


_active = False


def _failsafe_restore():
    if _active:
        show_taskbar()


atexit.register(_failsafe_restore)


def enter(window) -> None:
    """Turn `window` (SATURDAY's MainWindow) into a fullscreen, borderless,
    taskbar-free 'OS'. Pair with exit(window) to undo."""
    global _active
    from PyQt6.QtCore import Qt

    window._kiosk_prev_flags = window.windowFlags()
    window.setWindowFlags(
        window.windowFlags()
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.WindowStaysOnTopHint
    )
    window.show()  # Qt requires re-showing after a flag change
    window.showFullScreen()
    hide_taskbar()
    _active = True


def exit(window) -> None:
    """Restore Windows to normal — taskbar back, window framed again."""
    global _active
    show_taskbar()
    window.showNormal()
    prev_flags = getattr(window, "_kiosk_prev_flags", None)
    if prev_flags is not None:
        window.setWindowFlags(prev_flags)
        window.show()
    _active = False


def is_active() -> bool:
    return _active
