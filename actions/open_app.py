"""
open_app.py — System search utility that boots and opens applications on command.

This is a standard action module for the IP Prime personal assistant suite.
"""

import time
import subprocess
import platform
import shutil

_SYSTEM = platform.system()

_APP_ALIASES: dict[str, dict[str, str]] = {

    "chrome":             {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "google chrome":      {"Windows": "chrome",                  "Darwin": "Google Chrome",        "Linux": "google-chrome"},
    "firefox":            {"Windows": "firefox",                 "Darwin": "Firefox",              "Linux": "firefox"},
    "edge":               {"Windows": "msedge",                  "Darwin": "Microsoft Edge",       "Linux": "microsoft-edge"},
    "brave":              {"Windows": "brave",                   "Darwin": "Brave Browser",        "Linux": "brave-browser"},
    "safari":             {"Windows": "firefox",                 "Darwin": "Safari",               "Linux": "firefox"},
    "opera":              {"Windows": "opera",                   "Darwin": "Opera",                "Linux": "opera"},
    "whatsapp":           {"Windows": "WhatsApp",                "Darwin": "WhatsApp",             "Linux": "whatsapp"},
    "telegram":           {"Windows": "Telegram",                "Darwin": "Telegram",             "Linux": "telegram"},
    "discord":            {"Windows": "Discord",                 "Darwin": "Discord",              "Linux": "discord"},
    "slack":              {"Windows": "Slack",                   "Darwin": "Slack",                "Linux": "slack"},
    "zoom":               {"Windows": "Zoom",                    "Darwin": "zoom.us",              "Linux": "zoom"},
    "teams":              {"Windows": "msteams",                 "Darwin": "Microsoft Teams",      "Linux": "teams"},
    "skype":              {"Windows": "skype",                   "Darwin": "Skype",                "Linux": "skype"},
    "signal":             {"Windows": "signal",                  "Darwin": "Signal",               "Linux": "signal"},
    "spotify":            {"Windows": "Spotify",                 "Darwin": "Spotify",              "Linux": "spotify"},
    "vlc":                {"Windows": "vlc",                     "Darwin": "VLC",                  "Linux": "vlc"},
    "netflix":            {"Windows": "firefox",                 "Darwin": "Netflix",              "Linux": "firefox"},
    "vscode":             {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "visual studio code": {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "code":               {"Windows": "code",                    "Darwin": "Visual Studio Code",   "Linux": "code"},
    "terminal":           {"Windows": "wt",                      "Darwin": "Terminal",             "Linux": "gnome-terminal"},
    "cmd":                {"Windows": "cmd.exe",                 "Darwin": "Terminal",             "Linux": "bash"},
    "powershell":         {"Windows": "powershell.exe",          "Darwin": "Terminal",             "Linux": "bash"},
    "postman":            {"Windows": "Postman",                 "Darwin": "Postman",              "Linux": "postman"},
    "git":                {"Windows": "git-bash",                "Darwin": "Terminal",             "Linux": "bash"},
    "figma":              {"Windows": "Figma",                   "Darwin": "Figma",                "Linux": "figma"},
    "blender":            {"Windows": "blender",                 "Darwin": "Blender",              "Linux": "blender"},
    "word":               {"Windows": "winword",                 "Darwin": "Microsoft Word",       "Linux": "libreoffice --writer"},
    "excel":              {"Windows": "excel",                   "Darwin": "Microsoft Excel",      "Linux": "libreoffice --calc"},
    "powerpoint":         {"Windows": "powerpnt",                "Darwin": "Microsoft PowerPoint", "Linux": "libreoffice --impress"},
    "libreoffice":        {"Windows": "soffice",                 "Darwin": "LibreOffice",          "Linux": "libreoffice"},
    "notepad":            {"Windows": "notepad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "textedit":           {"Windows": "notepad.exe",             "Darwin": "TextEdit",             "Linux": "gedit"},
    "explorer":           {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "file explorer":      {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "finder":             {"Windows": "explorer.exe",            "Darwin": "Finder",               "Linux": "nautilus"},
    "task manager":       {"Windows": "taskmgr.exe",             "Darwin": "Activity Monitor",     "Linux": "gnome-system-monitor"},
    "settings":           {"Windows": "ms-settings:",            "Darwin": "System Preferences",   "Linux": "gnome-control-center"},
    "calculator":         {"Windows": "calc.exe",                "Darwin": "Calculator",           "Linux": "gnome-calculator"},
    "paint":              {"Windows": "mspaint.exe",             "Darwin": "Preview",              "Linux": "gimp"},
    "instagram":          {"Windows": "firefox",                 "Darwin": "Instagram",            "Linux": "firefox"},
    "tiktok":             {"Windows": "firefox",                 "Darwin": "TikTok",               "Linux": "firefox"},
    "notion":             {"Windows": "Notion",                  "Darwin": "Notion",               "Linux": "notion"},
    "obsidian":           {"Windows": "Obsidian",                "Darwin": "Obsidian",             "Linux": "obsidian"},
    "capcut":             {"Windows": "CapCut",                  "Darwin": "CapCut",               "Linux": "capcut"},
    "steam":              {"Windows": "steam",                   "Darwin": "Steam",                "Linux": "steam"},
    "epic":               {"Windows": "EpicGamesLauncher",       "Darwin": "Epic Games Launcher",  "Linux": "legendary"},
    "epic games":         {"Windows": "EpicGamesLauncher",       "Darwin": "Epic Games Launcher",  "Linux": "legendary"},
}


def _normalize(raw: str) -> str:
    key = raw.lower().strip()

    if key in _APP_ALIASES:
        return _APP_ALIASES[key].get(_SYSTEM, raw)

    for alias_key, os_map in _APP_ALIASES.items():
        if alias_key in key or key in alias_key:
            return os_map.get(_SYSTEM, raw)

    return raw  

def _windows_browser_exe(browser: str) -> str | None:
    import os
    low = browser.lower().strip()
    if low in ("edge", "msedge", "microsoft edge"):
        candidates = [
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return shutil.which("msedge") or shutil.which("msedge.exe")
    if low in ("firefox", "mozilla firefox"):
        candidates = [
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Mozilla Firefox", "firefox.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Mozilla Firefox", "firefox.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        return shutil.which("firefox") or shutil.which("firefox.exe")
    return None


_COMMON_WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://www.github.com",
    "gmail": "https://mail.google.com",
    "outlook": "https://outlook.live.com",
    "chatgpt": "https://chatgpt.com",
    "stackoverflow": "https://stackoverflow.com",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com"
}

def _find_windows_app_path(app_name: str) -> str | None:
    import winreg
    import os
    
    app_name_lower = app_name.lower().strip()
    candidates = [app_name_lower, f"{app_name_lower}.exe"]
    
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths"
        try:
            with winreg.OpenKey(hive, path) as key:
                num_subkeys = winreg.QueryInfoKey(key)[0]
                # 1. Exact match pass
                for i in range(num_subkeys):
                    subkey_name = winreg.EnumKey(key, i)
                    if subkey_name.lower() in candidates or subkey_name.lower().split(".")[0] == app_name_lower:
                        try:
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                val = winreg.QueryValue(subkey, "")
                                if val and os.path.exists(val):
                                    return val
                        except Exception:
                            pass
                
                # 2. Substring match pass
                for i in range(num_subkeys):
                    subkey_name = winreg.EnumKey(key, i)
                    if app_name_lower in subkey_name.lower():
                        try:
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                val = winreg.QueryValue(subkey, "")
                                if val and os.path.exists(val):
                                    return val
                        except Exception:
                            pass
        except Exception:
            pass
    return None

def _find_start_menu_lnk(app_name: str) -> str | None:
    import os
    from pathlib import Path
    
    search_paths = [
        Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    ]
    
    app_name_lower = app_name.lower().strip()
    
    # 1. Exact match pass
    for sp in search_paths:
        if sp.exists() and sp.is_dir():
            for root, dirs, files in os.walk(sp):
                for file in files:
                    if file.endswith(".lnk"):
                        name_without_ext = Path(file).stem.lower()
                        if app_name_lower == name_without_ext:
                            return os.path.join(root, file)
                            
    # 2. Substring match pass
    for sp in search_paths:
        if sp.exists() and sp.is_dir():
            for root, dirs, files in os.walk(sp):
                for file in files:
                    if file.endswith(".lnk"):
                        name_without_ext = Path(file).stem.lower()
                        if app_name_lower in name_without_ext:
                            return os.path.join(root, file)
                            
    return None

def _launch_windows(app_name: str) -> bool:
    import os
    low = app_name.lower().strip()
    
    # 1. Check if it's a known website or matches a website pattern
    is_url = False
    target_url = None
    if low in _COMMON_WEBSITES:
        is_url = True
        target_url = _COMMON_WEBSITES[low]
    elif "." in app_name and ("/" in app_name or len(app_name.split(".")[-1]) >= 2):
        is_url = True
        target_url = app_name if "://" in app_name else f"https://{app_name}"
    elif "://" in app_name or app_name.startswith("www."):
        is_url = True
        target_url = app_name if "://" in app_name else f"https://{app_name}"

    if is_url and target_url:
        try:
            import webbrowser
            webbrowser.open(target_url)
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] Default browser launch failed for URL {target_url}: {e}")

    # 2. Try App Path Registry
    reg_path = _find_windows_app_path(app_name)
    if reg_path:
        try:
            os.startfile(reg_path)
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] Launch via App Path failed: {e}")

    # 3. Try Start Menu Shortcuts (.lnk files)
    lnk_path = _find_start_menu_lnk(app_name)
    if lnk_path:
        try:
            os.startfile(lnk_path)
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] Launch via Start Menu LNK failed: {e}")

    # 4. Try standard shutil.which / subprocess launch
    if shutil.which(app_name) or shutil.which(app_name.split(".")[0]):
        try:
            subprocess.Popen(
                app_name,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(1.0)
            return True
        except Exception as e:
            print(f"[open_app] shutil.which launch failed: {e}")

    # 5. Try standard protocol start (like ms-settings: or UWP app protocols)
    if ":" in app_name or low in ("calculator", "paint", "settings", "photos", "weather", "store", "microsoft store", "whatsapp"):
        proto_map = {
            "calculator": "calc:",
            "paint": "mspaint:",
            "settings": "ms-settings:",
            "photos": "ms-photos:",
            "weather": "bingweather:",
            "store": "ms-windows-store:",
            "microsoft store": "ms-windows-store:",
            "whatsapp": "whatsapp:"
        }
        proto = proto_map.get(low, app_name if ":" in app_name else f"{low}:")
        try:
            os.startfile(proto)
            time.sleep(1.0)
            return True
        except Exception:
            pass

    return False


def _launch_macos(app_name: str) -> bool:

    try:
        result = subprocess.run(
            ["open", "-a", app_name],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["open", "-a", f"{app_name}.app"],
            capture_output=True, timeout=8
        )
        if result.returncode == 0:
            time.sleep(1.0)
            return True
    except Exception:
        pass

    binary = shutil.which(app_name) or shutil.which(app_name.lower())
    if binary:
        try:
            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        import pyautogui
        pyautogui.hotkey("command", "space")
        time.sleep(0.6)
        pyautogui.write(app_name, interval=0.05)
        time.sleep(0.8)
        pyautogui.press("enter")
        time.sleep(1.5)
        return True
    except Exception as e:
        print(f"[open_app] Spotlight failed: {e}")

    return False


def _launch_linux(app_name: str) -> bool:

    binary = (
        shutil.which(app_name) or
        shutil.which(app_name.lower()) or
        shutil.which(app_name.lower().replace(" ", "-")) or
        shutil.which(app_name.lower().replace(" ", "_"))
    )
    if binary:
        try:
            subprocess.Popen(
                [binary],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.0)
            return True
        except Exception:
            pass

    try:
        subprocess.run(
            ["xdg-open", app_name],
            capture_output=True, timeout=5
        )
        return True
    except Exception:
        pass

    for desktop_name in [
        app_name.lower(),
        app_name.lower().replace(" ", "-"),
        app_name.lower().replace(" ", ""),
    ]:
        try:
            result = subprocess.run(
                ["gtk-launch", desktop_name],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

    return False


_OS_LAUNCHERS = {
    "Windows": _launch_windows,
    "Darwin":  _launch_macos,
    "Linux":   _launch_linux,
}

def open_app(
    parameters=None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    app_name = (parameters or {}).get("app_name", "").strip()

    if not app_name:
        return "No application name provided."

    launcher = _OS_LAUNCHERS.get(_SYSTEM)
    if launcher is None:
        return f"Unsupported operating system: {_SYSTEM}"

    normalized = _normalize(app_name)
    print(f"[open_app] Launching: '{app_name}' → '{normalized}' ({_SYSTEM})")

    if player:
        player.write_log(f"[open_app] {app_name}")

    try:
        if launcher(normalized):
            return f"Opened {app_name}."
        if normalized.lower() != app_name.lower():
            if launcher(app_name):
                return f"Opened {app_name}."
        return (
            f"Could not confirm that {app_name} launched. "
            f"It may still be loading, or it might not be installed."
        )
    except Exception as e:
        print(f"[open_app] Error: {e}")
        return f"Failed to open {app_name}: {e}"