"""
os_shell_windows/browser_bridge.py
=====================================
Makes every `webbrowser.open(url)` / `webbrowser.get('firefox').open(url)`
call already in the SATURDAY codebase (actions/open_app.py,
actions/youtube_video.py, and anything else that opens a URL the normal
way) land inside SATURDAY's own EmbeddedBrowserPanel — instead of
launching a real system browser window that would float on top of
SaturdayOS Mode and break the "this is its own world" illusion.

This is a small, deliberate monkey-patch of the stdlib `webbrowser`
module, scoped to only be active while SaturdayOS Mode is on:
  - install()   called when entering kiosk mode (os_shell_windows/kiosk.py)
  - uninstall() called when leaving it

Normal windowed use of SATURDAY (the app you already had) is completely
unaffected — every action file keeps calling webbrowser.open() exactly
as Pratik wrote it; only the destination changes while kiosk mode is on.
"""

from __future__ import annotations

import webbrowser

_panel_callback = None
_installed = False
_original_get = webbrowser.get
_original_open = webbrowser.open


class _SaturdayController(webbrowser.BaseBrowser):
    def open(self, url, new=0, autoraise=True):
        if _panel_callback is not None:
            _panel_callback(url)
            return True
        return _original_open(url, new, autoraise)


_controller = _SaturdayController()


def register_panel(show_url_callback) -> None:
    """Called once by the UI integration (ui.py), passing a function
    that takes a URL string and displays it in the EmbeddedBrowserPanel."""
    global _panel_callback
    _panel_callback = show_url_callback


def install() -> None:
    """Redirect webbrowser.open()/get().open() into SATURDAY's own panel."""
    global _installed
    if _installed:
        return
    webbrowser.get = lambda using=None: _controller
    webbrowser.open = lambda url, new=0, autoraise=True: _controller.open(url, new, autoraise)
    _installed = True


def uninstall() -> None:
    """Restore normal system-browser behaviour (called when leaving kiosk mode)."""
    global _installed
    webbrowser.get = _original_get
    webbrowser.open = _original_open
    _installed = False


def is_installed() -> bool:
    return _installed
