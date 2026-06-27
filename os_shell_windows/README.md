# SaturdayOS Mode — Windows-Native Kiosk

This is the **correct** version of what you actually wanted: SATURDAY
becomes its own "OS" feeling, running entirely inside Windows — no VM,
no dual-boot, no separate Linux session. One press of **F9** and:

- Windows taskbar disappears
- SATURDAY takes the entire screen, borderless
- Any time SATURDAY would normally open a website (YouTube, WhatsApp
  Web, a Google search, etc.), it now opens **inside SATURDAY's own
  screen** instead of launching real Chrome/Edge on top of it

Press **F9** again (or **Esc**) and Windows comes back exactly as it was.

> Note: the `os_shell/` folder from earlier (Openbox/Linux session) is
> no longer needed for this goal — that was solving a different problem
> (a real separate OS). You can ignore or delete it. This folder,
> `os_shell_windows/`, is the one that matters now.

## How it works

```
You press F9
      │
      ▼
ui.py: _toggle_saturday_os_mode()
      │
      ├──▶ os_shell_windows/kiosk.py
      │      • hides the real Windows taskbar (Win32 API)
      │      • makes the SATURDAY window frameless + fullscreen
      │
      └──▶ os_shell_windows/browser_bridge.py
             • monkey-patches webbrowser.open()/get() for the
               whole app, so every existing action
               (open_app.py, youtube_video.py, ...) that would
               open a URL now routes here instead
                      │
                      ▼
             os_shell_windows/embedded_browser.py
             • SATURDAY's own browser screen (Chromium via
               QWebEngineView), shown as an overlay inside the
               SATURDAY window itself
```

Nothing about how SATURDAY decides *what* to open changed — "open
YouTube," "search for X," etc. all still work exactly as Pratik wrote
them. We only intercepted *where* the result is displayed.

## Install (on your real Windows PC — no VM needed)

```bash
cd sat
pip install PyQt6-WebEngine
```

(Already added to `requirements.txt` for next time you do a fresh
`pip install -r requirements.txt`.)

## Try it

```bash
python main.py
```

Once SATURDAY's console is open and running normally, press **F9**.
The taskbar should vanish and the window should go fullscreen. Say
"open YouTube" (or whatever wakes/triggers that action in your setup)
— it should open inside SATURDAY's own screen, with a small
"✕ Back to SATURDAY" button at the top instead of a real browser
window.

Press **F9** or **Esc** to leave SaturdayOS Mode.

## Known limitations (honest list, v1)

- Taskbar-hide uses the Windows API (`Shell_TrayWnd`) — Windows only.
  On macOS/Linux this is currently a no-op (fullscreen still works,
  taskbar/dock hiding doesn't — different mechanism per OS, not built
  yet).
- The embedded browser is a single screen/tab — no multi-tab browsing
  yet. Good enough for "open YouTube and play a song," not meant to
  replace your daily-driver browser.
- If `PyQt6-WebEngine` isn't installed, the panel shows a friendly
  "install this" message instead of crashing — SaturdayOS Mode (taskbar
  hide + fullscreen) still works, you just won't see real pages yet.
- We didn't get to test this on a real Windows machine in this session
  (the sandbox we built it in is Linux-only) — the Win32 calls in
  `kiosk.py` use the standard, well-documented `Shell_TrayWnd` /
  `ShowWindow` pattern, but **please test carefully** the first time.
  If F9 ever leaves you stuck, **Alt+Tab** then **right-click the
  taskbar area → Task Manager → End Task** on SATURDAY's process will
  always get you back to a normal desktop.

## Files

| File | Purpose |
|---|---|
| `kiosk.py` | Hides/shows the Windows taskbar, makes the window fullscreen+borderless |
| `embedded_browser.py` | SATURDAY's own in-window browser screen (QWebEngineView) |
| `browser_bridge.py` | Redirects existing `webbrowser.open()` calls into the panel while kiosk mode is on |

## What changed in the existing code

- `ui.py` — added an **F9** shortcut (+ **Esc** as a safety exit),
  three small helper methods on `MainWindow`, and one line inside the
  existing `resizeEvent` so the browser panel resizes with the window.
  Nothing else was touched; normal windowed use of SATURDAY is
  unaffected until you press F9.
- `requirements.txt` — added `PyQt6-WebEngine`.
