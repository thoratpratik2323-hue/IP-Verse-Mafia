"""
browser_control.py — Premium stealth browser automation engine powered by Playwright and Camoufox.

This is a standard action module for the IP Prime personal assistant suite.
"""

from __future__ import annotations
import sys
# Force console streams to use UTF-8 to prevent charmap Unicode crashes on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass




import asyncio
import concurrent.futures
import os
import platform
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional

from playwright.async_api import (
    async_playwright,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeout,
)
_OS = platform.system()   # "Windows" | "Darwin" | "Linux"

def _normalize_url(url: str) -> str:
    """
    Bare words like "instagram" → "https://instagram.com"
    Domains like "instagram.com" → "https://instagram.com"
    Full URLs pass through unchanged.
    """
    url = url.strip()
    if not url:
        return "about:blank"
    if "://" in url:
        return url
    # No dot at all → assume .com  (e.g. "instagram" → "instagram.com")
    if "." not in url:
        url = url + ".com"
    return "https://" + url


import re
from google import genai
from google.genai import types as gtypes

def _find_element_in_screenshot(image_bytes: bytes, description: str, api_key: str, width: int, height: int) -> tuple[int, int] | None:
    try:
        client = genai.Client(api_key=api_key)
        
        prompt = (
            f"Locate the UI element described as: '{description}'.\n"
            f"Return the exact 2D bounding box of the element as standard normalized coordinates in the form [ymin, xmin, ymax, xmax] on a scale of 0 to 1000 "
            f"(where ymin, xmin, ymax, xmax represent the percentage of height and width from the top-left corner, multiplied by 1000).\n"
            f"Reply with ONLY the coordinates in the format [ymin, xmin, ymax, xmax]. If not found, reply NOT_FOUND."
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                gtypes.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                prompt,
            ],
        )

        text = (response.text or "").strip()
        if "NOT_FOUND" in text.upper():
            return None

        bbox_match = re.search(r"[\[\(]\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[\]\)]", text)
        if bbox_match:
            ymin = int(bbox_match.group(1))
            xmin = int(bbox_match.group(2))
            ymax = int(bbox_match.group(3))
            xmax = int(bbox_match.group(4))
            
            cx = int(((xmin + xmax) / 2.0) / 1000.0 * width)
            cy = int(((ymin + ymax) / 2.0) / 1000.0 * height)
            return cx, cy
    except Exception as e:
        print(f"[Browser] Visual grounding locator exception: {e}")
    return None

def _user_agent() -> str:
    if _OS == "Windows":
        return (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    if _OS == "Darwin":
        return (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    return (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )


def _real_profile_dir(browser: str) -> str:
    home  = Path.home()
    local = os.environ.get("LOCALAPPDATA", "")
    roam  = os.environ.get("APPDATA", "")

    candidates: list[Path] = []

    if _OS == "Windows":
        m = {
            "chrome":   [Path(local) / "Google"          / "Chrome"          / "User Data"],
            "edge":     [Path(local) / "Microsoft"        / "Edge"            / "User Data"],
            "brave":    [Path(local) / "BraveSoftware"    / "Brave-Browser"   / "User Data"],
            "vivaldi":  [Path(local) / "Vivaldi"          / "User Data"],
            "opera":    [Path(roam)  / "Opera Software"   / "Opera Stable",
                         Path(local) / "Opera Software"   / "Opera Stable"],
            "operagx":  [Path(roam)  / "Opera Software"   / "Opera GX Stable",
                         Path(local) / "Opera Software"   / "Opera GX Stable"],
        }
        candidates = m.get(browser, [])

    elif _OS == "Darwin":
        lib = home / "Library" / "Application Support"
        m = {
            "chrome":   [lib / "Google"             / "Chrome"],
            "edge":     [lib / "Microsoft Edge"],
            "brave":    [lib / "BraveSoftware"       / "Brave-Browser"],
            "vivaldi":  [lib / "Vivaldi"],
            "opera":    [lib / "com.operasoftware.Opera"],
            "operagx":  [lib / "com.operasoftware.OperaGX"],
        }
        candidates = m.get(browser, [])

    elif _OS == "Linux":
        cfg = home / ".config"
        m = {
            "chrome":   [cfg / "google-chrome", cfg / "chromium"],
            "edge":     [cfg / "microsoft-edge"],
            "brave":    [cfg / "BraveSoftware" / "Brave-Browser"],
            "vivaldi":  [cfg / "vivaldi"],
            "opera":    [cfg / "opera"],
            "operagx":  [cfg / "opera-gx"],
        }
        candidates = m.get(browser, [])

    for p in candidates:
        if p.exists():
            print(f"[Browser] [OK] Real profile found for {browser}: {p}")
            return str(p)

    fallback = home / ".ip_ray_profiles" / browser
    fallback.mkdir(parents=True, exist_ok=True)
    print(f"[Browser] [WARN] Real profile not found for {browser}, using: {fallback}")
    return str(fallback)

def _firefox_profile_dir() -> Optional[str]:
    home = Path.home()

    if _OS == "Windows":
        base = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox"
    elif _OS == "Darwin":
        base = home / "Library" / "Application Support" / "Firefox"
    else:
        base = home / ".mozilla" / "firefox"

    ini = base / "profiles.ini"
    if not ini.exists():
        return None

    current: dict[str, str] = {}
    default_path: Optional[str] = None

    for line in ini.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("["):
            p = current.get("Path", "")
            if p and current.get("Default") == "1":
                is_rel = current.get("IsRelative", "1") == "1"
                default_path = str(base / p) if is_rel else p
            current = {}
        elif "=" in line:
            k, _, v = line.partition("=")
            current[k.strip()] = v.strip()

    p = current.get("Path", "")
    if p and current.get("Default") == "1":
        is_rel = current.get("IsRelative", "1") == "1"
        default_path = str(base / p) if is_rel else p

    if default_path and Path(default_path).exists():
        print(f"[Browser] Firefox real profile: {default_path}")
        return default_path
    return None

def _find_opera_windows() -> Optional[str]:
    local  = os.environ.get("LOCALAPPDATA", "")
    prog   = os.environ.get("PROGRAMFILES", "")
    prog86 = os.environ.get("PROGRAMFILES(X86)", "")

    candidates = [
        Path(local)  / "Programs" / "Opera"    / "opera.exe",
        Path(local)  / "Programs" / "Opera GX" / "opera.exe",
        Path(prog)   / "Opera"    / "opera.exe",
        Path(prog86) / "Opera"    / "opera.exe",
    ]
    for p in candidates:
        if p.exists():
            print(f"[Browser] Opera found at: {p}")
            return str(p)

    try:
        import winreg
        keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\opera.exe",
            r"SOFTWARE\Clients\StartMenuInternet\OperaStable\shell\open\command",
            r"SOFTWARE\Clients\StartMenuInternet\OperaGXStable\shell\open\command",
            r"SOFTWARE\Clients\StartMenuInternet\opera\shell\open\command",
        ]
        for key_path in keys:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    k   = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(k, None)
                    winreg.CloseKey(k)
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        print(f"[Browser] Opera found via registry: {exe}")
                        return exe
                except Exception:
                    continue
    except Exception:
        pass

    return shutil.which("opera") or None

_WINDOWS_EXE = {
    "edge": "msedge.exe",
    "firefox": "firefox.exe",
    "chrome": "chrome.exe",
    "brave": "brave.exe",
    "vivaldi": "vivaldi.exe",
}


def _find_exe_windows(browser: str) -> Optional[str]:
    browser = _ALIASES.get(browser.lower().strip(), browser.lower().strip())
    exe_name = _WINDOWS_EXE.get(browser, f"{browser}.exe")

    if browser == "edge":
        for p in (
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Microsoft/Edge/Application/msedge.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Microsoft/Edge/Application/msedge.exe",
        ):
            if p.exists():
                return str(p)
    if browser == "firefox":
        for p in (
            Path(os.environ.get("PROGRAMFILES", "")) / "Mozilla Firefox/firefox.exe",
            Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Mozilla Firefox/firefox.exe",
        ):
            if p.exists():
                return str(p)

    found = shutil.which(exe_name.replace(".exe", "")) or shutil.which(exe_name)
    if found:
        return found

    try:
        import winreg
        paths_to_try = [
            rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}",
            rf"SOFTWARE\Clients\StartMenuInternet\{browser}\shell\open\command",
        ]
        if browser == "edge":
            paths_to_try.append(r"SOFTWARE\Clients\StartMenuInternet\MSEdgeHTM\shell\open\command")
        if browser == "firefox":
            paths_to_try.append(r"SOFTWARE\Clients\StartMenuInternet\FirefoxURL\shell\open\command")
        for key_path in paths_to_try:
            for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    k = winreg.OpenKey(hive, key_path)
                    val = winreg.QueryValue(k, None)
                    winreg.CloseKey(k)
                    exe = val.strip().strip('"').split('"')[0].split(" --")[0].strip()
                    if exe and Path(exe).exists():
                        return exe
                except Exception:
                    continue
    except Exception:
        pass
    return None


def launch_native_browser(browser_name: str, url: str = "") -> str:
    """Open Edge/Firefox/Chrome as a normal desktop app (no Playwright profile lock)."""
    name = _ALIASES.get((browser_name or "").lower().strip(), (browser_name or "chrome").lower().strip())
    target_url = _normalize_url(url) if (url or "").strip() else ""

    if _OS == "Windows":
        exe = _find_exe_windows(name)
        if exe:
            args = [exe]
            if target_url and target_url != "about:blank":
                args.append(target_url)
            subprocess.Popen(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if target_url and target_url != "about:blank":
                return f"Opened {name} at {target_url}"
            return f"Opened {name}, Sir."
        return f"Could not find {name} on this PC. Is it installed?"

    if _OS == "Darwin":
        app_map = {
            "chrome": "Google Chrome",
            "edge": "Microsoft Edge",
            "firefox": "Firefox",
            "safari": "Safari",
            "brave": "Brave Browser",
        }
        app = app_map.get(name, browser_name)
        cmd = ["open", "-a", app]
        if target_url and target_url != "about:blank":
            cmd.append(target_url)
        subprocess.Popen(cmd)
        return f"Opened {app}."

    exe = shutil.which(name) or shutil.which(_WINDOWS_EXE.get(name, name))
    if exe:
        args = [exe]
        if target_url and target_url != "about:blank":
            args.append(target_url)
        subprocess.Popen(args)
        return f"Opened {name}."
    return f"Could not find browser: {browser_name}"

_BROWSER_SPECS: dict[str, dict] = {
    "Windows": {
        "chrome":   {"engine": "chromium", "channel": "chrome",  "bins": []},
        "edge":     {"engine": "chromium", "channel": "msedge",  "bins": []},
        "firefox":  {"engine": "firefox",  "channel": None,      "bins": ["firefox.exe"]},
        "opera":    {"engine": "chromium", "channel": None,      "bins": ["opera.exe"],  "special": "opera_windows"},
        "operagx":  {"engine": "chromium", "channel": None,      "bins": [],             "special": "opera_windows"},
        "brave":    {"engine": "chromium", "channel": None,      "bins": ["brave.exe"]},
        "vivaldi":  {"engine": "chromium", "channel": None,      "bins": ["vivaldi.exe"]},
        "safari":   None,
    },
    "Darwin": {
        "chrome":   {"engine": "chromium", "channel": "chrome",  "bins": []},
        "edge":     {"engine": "chromium", "channel": "msedge",  "bins": ["microsoft-edge"]},
        "firefox":  {"engine": "firefox",  "channel": None,      "bins": ["firefox"]},
        "opera":    {"engine": "chromium", "channel": None,      "bins": ["opera"]},
        "operagx":  {"engine": "chromium", "channel": None,      "bins": ["opera"]},
        "brave":    {"engine": "chromium", "channel": None,      "bins": ["brave browser", "brave"]},
        "vivaldi":  {"engine": "chromium", "channel": None,      "bins": ["vivaldi"]},
        "safari":   {"engine": "webkit",   "channel": None,      "bins": []},
    },
    "Linux": {
        "chrome":   {"engine": "chromium", "channel": None,
                     "bins": ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]},
        "edge":     {"engine": "chromium", "channel": None,
                     "bins": ["microsoft-edge", "microsoft-edge-stable"]},
        "firefox":  {"engine": "firefox",  "channel": None, "bins": ["firefox"]},
        "opera":    {"engine": "chromium", "channel": None, "bins": ["opera", "opera-stable"]},
        "operagx":  {"engine": "chromium", "channel": None, "bins": ["opera", "opera-stable"]},
        "brave":    {"engine": "chromium", "channel": None, "bins": ["brave-browser", "brave"]},
        "vivaldi":  {"engine": "chromium", "channel": None, "bins": ["vivaldi-stable", "vivaldi"]},
        "safari":   None,
    },
}

_ALIASES: dict[str, str] = {
    "google chrome":   "chrome",
    "google-chrome":   "chrome",
    "microsoft edge":  "edge",
    "ms edge":         "edge",
    "msedge":          "edge",
    "mozilla firefox": "firefox",
    "opera gx":        "operagx",
    "opera_gx":        "operagx",
}


def _resolve_browser(name: str) -> dict | None:
    name   = _ALIASES.get(name.lower().strip(), name.lower().strip())
    os_map = _BROWSER_SPECS.get(_OS, {})
    spec   = os_map.get(name)
    if spec is None:
        return None

    engine  = spec["engine"]
    channel = spec.get("channel")
    bins    = spec.get("bins", [])
    exe     = None

    if spec.get("special") == "opera_windows":
        exe = _find_opera_windows()
        if not exe:
            print("[Browser] [WARN] Opera executable not found on Windows.")
        return {"engine": engine, "exe": exe, "channel": channel}

    for b in bins:
        found = shutil.which(b)
        if found:
            exe = found
            break

    if not exe and _OS == "Darwin":
        app_names = {
            "chrome":  ["Google Chrome.app"],
            "edge":    ["Microsoft Edge.app"],
            "firefox": ["Firefox.app"],
            "opera":   ["Opera.app", "Opera GX.app"],
            "brave":   ["Brave Browser.app"],
            "vivaldi": ["Vivaldi.app"],
        }
        for app in app_names.get(name, []):
            app_dir = Path("/Applications") / app / "Contents" / "MacOS"
            if app_dir.exists():
                found_bins = list(app_dir.iterdir())
                if found_bins:
                    exe = str(found_bins[0])
                    break

    if not exe and _OS == "Windows" and not channel:
        exe = _find_exe_windows(name)

    if exe and "WindowsApps" in exe:
        exe = None

    return {"engine": engine, "exe": exe, "channel": channel}


def _detect_default_browser() -> str:
    try:
        if _OS == "Windows":
            import winreg
            k = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\Shell\Associations"
                r"\UrlAssociations\http\UserChoice",
            )
            prog_id = winreg.QueryValueEx(k, "ProgId")[0].lower()
            winreg.CloseKey(k)
            for kw in ("edge", "firefox", "opera", "brave", "vivaldi", "chrome"):
                if kw in prog_id:
                    return kw
        elif _OS == "Darwin":
            out = subprocess.run(
                ["defaults", "read",
                 "com.apple.LaunchServices/com.apple.launchservices.secure",
                 "LSHandlers"],
                capture_output=True, text=True, timeout=5,
            ).stdout.lower()
            for kw in ("firefox", "opera", "brave", "vivaldi", "safari", "chrome", "edge"):
                if kw in out:
                    return kw
        elif _OS == "Linux":
            out = subprocess.run(
                ["xdg-settings", "get", "default-web-browser"],
                capture_output=True, text=True, timeout=5,
            ).stdout.lower()
            for kw in ("firefox", "opera", "brave", "vivaldi", "chrome", "edge"):
                if kw in out:
                    return kw
    except Exception:
        pass
    return "chrome"
def _load_stealth_config() -> dict:
    try:
        import sys
        import json
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "api_keys.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[Browser] Error loading config: {e}")
    return {}

def _parse_proxy_string(proxy_str: str) -> dict | None:
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None
    from urllib.parse import urlparse
    try:
        if not (proxy_str.startswith("http://") or proxy_str.startswith("https://") or proxy_str.startswith("socks5://") or proxy_str.startswith("socks4://")):
            parsed = urlparse("http://" + proxy_str)
        else:
            parsed = urlparse(proxy_str)
        
        netloc = parsed.netloc
        if "@" in netloc:
            auth, _, host = netloc.rpartition("@")
            username, _, password = auth.partition(":")
        else:
            host = netloc
            username, password = None, None
        
        scheme = parsed.scheme or "http"
        server = f"{scheme}://{host}"
        p = {"server": server}
        if username:
            p["username"] = username
        if password:
            p["password"] = password
        return p
    except Exception as e:
        print(f"[Browser] Proxy parse error for '{proxy_str}': {e}")
        return None


class _BrowserSession:
    """
    Bir tarayıcı örneği için tam oturum.
    Tüm tarayıcılar launch_persistent_context ile gerçek profil üzerinde açılır.
    """

    def __init__(self, browser_name: str):
        self.browser_name = browser_name
        self._spec        = _resolve_browser(browser_name)

        self._loop:    asyncio.AbstractEventLoop | None = None
        self._thread:  threading.Thread | None          = None
        self._ready    = threading.Event()

        self._pw:      Playwright     | None = None
        self._context: BrowserContext | None = None
        self._page:    Page           | None = None
        self._camou_manager = None


    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name=f"BrowserThread-{self.browser_name}",
        )
        self._thread.start()
        self._ready.wait(timeout=20)

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._async_init())
        self._ready.set()
        self._loop.run_forever()

    async def _async_init(self):
        self._pw = await async_playwright().start()

    def run(self, coro, timeout: int = 60) -> str:
        if not self._loop:
            raise RuntimeError(f"Session for '{self.browser_name}' not started.")
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=timeout)

    def close(self):
        if self._loop:
            try:
                asyncio.run_coroutine_threadsafe(self._async_close(), self._loop).result(10)
            except Exception as e:
                print(f"[Browser] Close async error: {e}")
            finally:
                # Stop the event loop so the daemon thread exits cleanly
                try:
                    self._loop.call_soon_threadsafe(self._loop.stop)
                except Exception:
                    pass

    async def _async_close(self):
        if hasattr(self, "_camou_manager") and self._camou_manager:
            try:
                await self._camou_manager.__aexit__(None, None, None)
            except Exception:
                pass
            self._camou_manager = None
            self._context = self._page = None
            return

        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
        if self._pw:
            try:
                await self._pw.stop()
            except Exception:
                pass
        self._context = self._page = None

    async def _launch(self):
        """
        Tarayıcıyı gerçek kullanıcı profiliyle başlatır.
        Context zaten açıksa hiçbir şey yapmaz.
        """
        if self._context is not None:
            return

        cfg = _load_stealth_config()
        use_camou = cfg.get("use_camoufox", False)
        use_cloak = cfg.get("use_cloakbrowser", False)

        if use_cloak:
            cloak_path = cfg.get("cloakbrowser_path", "")
            if cloak_path and os.path.exists(cloak_path):
                try:
                    engine_obj = self._pw.chromium
                    profile = str(Path.home() / ".ipprime_cloakbrowser_profile")
                    Path(profile).mkdir(parents=True, exist_ok=True)
                    
                    proxy_str = cfg.get("cloakbrowser_proxy", "")
                    proxy_dict = _parse_proxy_string(proxy_str) if proxy_str else None
                    
                    kwargs = {
                        "headless":    cfg.get("cloakbrowser_headless", False),
                        "slow_mo":     0,
                        "viewport":    None,
                        "no_viewport": True,
                        "executable_path": cloak_path,
                        "args": [
                            "--start-maximized",
                            "--disable-blink-features=AutomationControlled",
                            "--no-first-run",
                            "--disable-default-apps",
                            "--no-default-browser-check",
                        ],
                    }
                    if proxy_dict:
                        kwargs["proxy"] = proxy_dict
                        
                    print(f"[Browser] [STEALTH] Launching CloakBrowser (stealth Chromium) from: {cloak_path}")
                    self._context = await engine_obj.launch_persistent_context(profile, **kwargs)
                    await asyncio.sleep(0.5)
                    self._page = await self._context.new_page()
                    print("[Browser] [STEALTH] CloakBrowser launched successfully!")
                    return
                except Exception as e:
                    print(f"[Browser] [WARN] CloakBrowser launch failed: {e}. Falling back to standard browser.")
            else:
                print(f"[Browser] [WARN] CloakBrowser path empty or not found: '{cloak_path}'. Falling back.")

        if use_camou:
            try:
                from camoufox.async_api import AsyncCamoufox
                
                headless = cfg.get("camoufox_headless", False)
                os_spoof = cfg.get("camoufox_os", "random")
                if os_spoof not in ("windows", "macos", "linux"):
                    os_spoof = "random"
                
                block_assets = cfg.get("camoufox_block_assets", False)
                humanize = cfg.get("camoufox_human_mimic", True)
                proxy_str = cfg.get("camoufox_proxy", "")
                
                proxy_dict = _parse_proxy_string(proxy_str) if proxy_str else None
                
                # Load advanced stealth options
                block_webrtc = cfg.get("camoufox_block_webrtc", True)
                allow_webgl = cfg.get("camoufox_allow_webgl", False)
                geoip = cfg.get("camoufox_geoip", True)
                addons_path_str = cfg.get("camoufox_addons_path", "")
                
                # Scan add-ons path if specified
                addons_list = []
                if addons_path_str:
                    try:
                        addons_dir = Path(addons_path_str)
                        if addons_dir.exists() and addons_dir.is_dir():
                            for item in addons_dir.iterdir():
                                if item.is_dir() and (item / "manifest.json").exists():
                                    addons_list.append(str(item.resolve()))
                            if (addons_dir / "manifest.json").exists():
                                addons_list.append(str(addons_dir.resolve()))
                    except Exception as ae:
                        print(f"[Browser] Error scanning addons directory: {ae}")
                
                profile = str(Path.home() / ".ipprime_camoufox_profile")
                Path(profile).mkdir(parents=True, exist_ok=True)
                
                print(f"[Browser] [STEALTH] Launching Camoufox (headless={headless}, os={os_spoof}, block_images={block_assets}, humanize={humanize}, proxy={proxy_str}, block_webrtc={block_webrtc}, allow_webgl={allow_webgl}, geoip={geoip}, addons={len(addons_list)} found)...")
                
                self._camou_manager = AsyncCamoufox(
                    persistent_context=True,
                    user_data_dir=profile,
                    headless=headless,
                    os=os_spoof,
                    block_images=block_assets,
                    humanize=humanize,
                    proxy=proxy_dict,
                    geoip=geoip,
                    block_webrtc=block_webrtc,
                    allow_webgl=allow_webgl,
                    addons=addons_list if addons_list else None,
                )
                self._context = await self._camou_manager.__aenter__()
                await asyncio.sleep(0.5)
                self._page = await self._context.new_page()
                print("[Browser] [STEALTH] Camoufox launched successfully!")
                return
            except ImportError:
                print("[Browser] [WARN] Camoufox package not installed. Falling back to standard browser.")
            except Exception as e:
                print(f"[Browser] [WARN] Camoufox launch failed: {e}. Falling back to standard browser.")

        if self._spec is None:
            raise RuntimeError(
                f"'{self.browser_name}' bu platformda ({_OS}) desteklenmiyor."
            )


        engine_name = self._spec["engine"]
        exe         = self._spec["exe"]
        channel     = self._spec["channel"]
        engine_obj  = getattr(self._pw, engine_name)

        if engine_name == "firefox":
            profile = _firefox_profile_dir() or str(
                Path.home() / ".ip_ray_profiles" / "firefox"
            )
            kwargs: dict = {
                "headless":    False,
                "slow_mo":     0,
                "viewport":    None,
                "no_viewport": True,
            }
            if exe:
                kwargs["executable_path"] = exe
            try:
                self._context = await engine_obj.launch_persistent_context(profile, **kwargs)
            except Exception as e:
                print(f"[Browser] Firefox real profile failed ({e}), using IP PRIME profile")
                ip_ray = str(Path.home() / ".ip_ray_profiles" / "firefox_ip_ray")
                Path(ip_ray).mkdir(parents=True, exist_ok=True)
                self._context = await engine_obj.launch_persistent_context(ip_ray, **kwargs)

            await asyncio.sleep(0.5)  
            self._page = await self._context.new_page()
            try:
                from playwright_stealth import Stealth
                await Stealth().apply_stealth_async(self._page)
            except Exception as se:
                print(f"[Browser] Stealth applied (non-critical): {se}")
            print("[Browser] [OK] Firefox launched")
            return

        if engine_name == "webkit":
            safari_profile = str(Path.home() / ".ip_ray_profiles" / "safari")
            Path(safari_profile).mkdir(parents=True, exist_ok=True)
            kwargs = {
                "headless":    False,
                "slow_mo":     0,
                "viewport":    None,
                "no_viewport": True,
            }
            self._context = await engine_obj.launch_persistent_context(safari_profile, **kwargs)
            await asyncio.sleep(0.5)
            self._page = await self._context.new_page()
            try:
                from playwright_stealth import Stealth
                await Stealth().apply_stealth_async(self._page)
            except Exception as se:
                print(f"[Browser] Stealth applied (non-critical): {se}")
            print("[Browser] [OK] Safari launched")
            return

        try:
            from prime_platform.ip_given_workspace import browser_profiles_dir
            profile = str(browser_profiles_dir() / self.browser_name)
        except Exception:
            profile = str(Path.home() / ".ip_ray_profiles" / self.browser_name)
        Path(profile).mkdir(parents=True, exist_ok=True)

        kwargs = {
            "headless":    False,
            "slow_mo":     0,
            "viewport":    None,
            "no_viewport": True,
            "args": [
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--disable-default-apps",
                "--no-default-browser-check",
            ],
        }

        if exe:
            kwargs["executable_path"] = exe
        elif channel:
            kwargs["channel"] = channel

        label = (
            f"{self.browser_name}"
            + (f"/{channel}" if channel else "")
            + (f" @ {exe}" if exe else "")
        )

        try:
            self._context = await engine_obj.launch_persistent_context(profile, **kwargs)
            await asyncio.sleep(0.5)
            self._page = await self._context.new_page()
            try:
                from playwright_stealth import Stealth
                await Stealth().apply_stealth_async(self._page)
            except Exception as se:
                print(f"[Browser] Stealth applied (non-critical): {se}")
            print(f"[Browser] [OK] Launched [{label}] CODING PROJECTS profile={profile}")
            return
        except Exception as e:
            print(f"[Browser] [WARN] CODING PROJECTS profile failed for {label}: {e}")

        real_profile = _real_profile_dir(self.browser_name)
        try:
            self._context = await engine_obj.launch_persistent_context(real_profile, **kwargs)
            await asyncio.sleep(0.5)
            self._page = await self._context.new_page()
            print(f"[Browser] [OK] Launched [{label}] real profile={real_profile}")
            return
        except Exception as e:
            print(f"[Browser] [WARN] Real profile failed for {label}: {e}")

        ip_ray_profile = str(Path.home() / ".ip_ray_profiles" / self.browser_name)
        Path(ip_ray_profile).mkdir(parents=True, exist_ok=True)
        print(f"[Browser] Retrying with IP PRIME profile: {ip_ray_profile}")

        try:
            self._context = await engine_obj.launch_persistent_context(ip_ray_profile, **kwargs)
            await asyncio.sleep(0.5)
            self._page = await self._context.new_page()
            try:
                from playwright_stealth import Stealth
                await Stealth().apply_stealth_async(self._page)
            except Exception as se:
                print(f"[Browser] Stealth applied (non-critical): {se}")
            print(f"[Browser] [OK] Launched [{label}] with IP PRIME profile")
        except Exception as e2:
            raise RuntimeError(f"Could not launch {self.browser_name}: {e2}") from e2


    async def _apply_stealth(self):
        if self._context:
            try:
                evasions = """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [
                    { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer' },
                    { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer' }
                ]});
                """
                await self._context.add_init_script(evasions)
                try:
                    from playwright_stealth import Stealth
                    if self._page:
                        await Stealth().apply_stealth_async(self._page)
                except Exception:
                    pass
            except Exception as e:
                print(f"[Browser] Custom stealth setup failed: {e}")

    async def _get_page(self) -> Page:
        await self._launch()
        # If somehow page got closed, open a fresh one
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
            await asyncio.sleep(0.2)
        await self._apply_stealth()
        return self._page

    async def go_to(self, url: str) -> str:

        url      = _normalize_url(url)
        page     = await self._get_page()
        prev_url = page.url

        async def _do_goto(p: Page) -> str:
            """Attempt navigation and return the resulting URL (may still be blank)."""
            try:
                await p.goto(url, wait_until="domcontentloaded", timeout=30_000)
                await asyncio.sleep(0.3)
            except PlaywrightTimeout:
                pass   # page may have partially loaded — check URL below
            except Exception as e:
                print(f"[Browser] goto exception (non-fatal): {e}")
            return p.url

        result_url = await _do_goto(page)

        if result_url in ("about:blank", "", None, prev_url) and prev_url in ("about:blank", "", None):
            print(f"[Browser] Still blank after goto — retrying on new tab: {url}")
            try:
                new_page   = await self._context.new_page()
                self._page = new_page
                result_url = await _do_goto(new_page)
            except Exception as e:
                print(f"[Browser] New-tab retry failed: {e}")

        if result_url and result_url not in ("about:blank", "", None):
            return f"Opened: {result_url}"
        return f"Could not open: {url}"

    async def search(self, query: str, engine: str = "google") -> str:
        _engines = {
            "google":     "https://www.google.com/search?q=",
            "bing":       "https://www.bing.com/search?q=",
            "duckduckgo": "https://duckduckgo.com/?q=",
            "yandex":     "https://yandex.com/search/?text=",
        }
        base = _engines.get(engine.lower(), _engines["google"])
        return await self.go_to(base + query.replace(" ", "+"))

    async def click(self, selector: str = None, text: str = None) -> str:
        page = await self._get_page()
        try:
            if text:
                await page.get_by_text(text, exact=False).first.click(timeout=8_000)
                return f"Clicked text: '{text}'"
            if selector:
                await page.click(selector, timeout=8_000)
                return f"Clicked selector: {selector}"
            return "No selector or text provided."
        except PlaywrightTimeout:
            return "Element not found (timeout)."
        except Exception as e:
            return f"Click error: {e}"

    async def type_text(self, selector: str = None, text: str = "",
                        clear_first: bool = True) -> str:
        page = await self._get_page()
        try:
            el = page.locator(selector).first if selector else page.locator(":focus")
            if clear_first:
                await el.clear()
            await el.type(text, delay=50)
            return "Text typed."
        except Exception as e:
            return f"Type error: {e}"

    async def scroll(self, direction: str = "down", amount: int = 500) -> str:
        page = await self._get_page()
        try:
            y = amount if direction == "down" else -amount
            await page.mouse.wheel(0, y)
            return f"Scrolled {direction}."
        except Exception as e:
            return f"Scroll error: {e}"

    async def press(self, key: str) -> str:
        page = await self._get_page()
        try:
            await page.keyboard.press(key)
            return f"Pressed: {key}"
        except Exception as e:
            return f"Key error: {e}"

    async def get_text(self) -> str:
        page = await self._get_page()
        try:
            text = await page.inner_text("body")
            return text[:4_000]
        except Exception as e:
            return f"Could not get page text: {e}"

    async def get_url(self) -> str:
        page = await self._get_page()
        return page.url

    async def fill_form(self, fields: dict) -> str:
        page    = await self._get_page()
        results = []
        for selector, value in fields.items():
            try:
                el = page.locator(selector).first
                await el.clear()
                await el.type(str(value), delay=40)
                results.append(f"✓ {selector}")
            except Exception as e:
                results.append(f"✗ {selector}: {e}")
        return "Form filled: " + ", ".join(results)

    async def smart_click(self, description: str) -> str:
        page = await self._get_page()
        for role in ("button", "link", "searchbox", "textbox", "menuitem", "tab"):
            try:
                loc = page.get_by_role(role, name=description)
                if await loc.count() > 0:
                    await loc.first.click(timeout=3_000)
                    return f"Clicked ({role}): '{description}'"
            except Exception:
                pass
        for attempt in (
            lambda: page.get_by_text(description, exact=False).first.click(timeout=3_000),
            lambda: page.get_by_placeholder(description, exact=False).first.click(timeout=3_000),
            lambda: page.locator(
                f'[alt*="{description}" i],[title*="{description}" i],'
                f'[aria-label*="{description}" i]'
            ).first.click(timeout=3_000),
        ):
            try:
                await attempt()
                return f"Clicked: '{description}'"
            except Exception:
                pass

        # 2-Stage Visual Grounding Fallback Click
        try:
            from actions.computer_control import _get_api_key
            api_key = _get_api_key()
            if api_key:
                print(f"[Browser] Locators failed for '{description}'. Running Visual Grounding Clicker...")
                png_bytes = await page.screenshot(type="png")
                vp = page.viewport_size or {"width": 1280, "height": 720}
                coords = _find_element_in_screenshot(png_bytes, description, api_key, vp["width"], vp["height"])
                if coords:
                    cx, cy = coords
                    await page.mouse.click(cx, cy)
                    return f"Visually located and clicked '{description}' at ({cx}, {cy}) inside browser tab, sir."
        except Exception as ve:
            print(f"[Browser] Visual clicker fallback failed: {ve}")

        return f"Could not find element: '{description}'"

    async def smart_type(self, description: str, text: str) -> str:
        page = await self._get_page()
        candidates = [
            ("placeholder", page.get_by_placeholder(description, exact=False)),
            ("label",       page.get_by_label(description, exact=False)),
            ("role",        page.get_by_role("textbox", name=description)),
            ("searchbox",   page.get_by_role("searchbox")),
            ("combobox",    page.get_by_role("combobox", name=description)),
        ]
        for method, loc in candidates:
            try:
                el = loc.first
                if await el.count() == 0:
                    continue
                await el.clear()
                await el.type(text, delay=50)
                return f"Typed into ({method}): '{description}'"
            except Exception:
                continue

        # 2-Stage Visual Grounding Fallback Type
        try:
            from actions.computer_control import _get_api_key
            api_key = _get_api_key()
            if api_key:
                print(f"[Browser] Locators failed for typing '{description}'. Running Visual Grounding Typer...")
                png_bytes = await page.screenshot(type="png")
                vp = page.viewport_size or {"width": 1280, "height": 720}
                coords = _find_element_in_screenshot(png_bytes, description, api_key, vp["width"], vp["height"])
                if coords:
                    cx, cy = coords
                    await page.mouse.click(cx, cy)
                    await asyncio.sleep(0.2)
                    await page.keyboard.press("Control+A")
                    await page.keyboard.press("Delete")
                    await page.keyboard.type(text, delay=40)
                    return f"Visually focused and typed '{text}' into '{description}' at ({cx}, {cy}) inside browser tab, sir."
        except Exception as ve:
            print(f"[Browser] Visual typing fallback failed: {ve}")

        return f"Could not find input: '{description}'"

    async def new_tab(self, url: str = "") -> str:
        page = await self._get_page()
        ctx  = page.context
        new  = await ctx.new_page()
        self._page = new
        if url:
            return await self.go_to(url)
        return "New tab opened."

    async def close_tab(self) -> str:
        page = self._page
        if page and not page.is_closed():
            ctx   = page.context
            await page.close()
            pages = ctx.pages
            self._page = pages[-1] if pages else None
            return "Tab closed."
        return "No active tab to close."

    async def screenshot(self, path: str = None) -> str:
        page = await self._get_page()
        try:
            if not path:
                try:
                    from prime_platform.ip_given_workspace import resolve_save_path
                    path = str(resolve_save_path("", category="screenshots", extension=".png"))
                except Exception:
                    path = str(Path.home() / "Desktop" / "ipprime_screenshot.png")
            save_path = path
            await page.screenshot(path=save_path, full_page=False)
            return f"Screenshot saved: {save_path}"
        except Exception as e:
            return f"Screenshot error: {e}"

    async def back(self) -> str:
        page = await self._get_page()
        try:
            await page.go_back(timeout=10_000)
            return f"Navigated back: {page.url}"
        except Exception as e:
            return f"Back error: {e}"

    async def forward(self) -> str:
        page = await self._get_page()
        try:
            await page.go_forward(timeout=10_000)
            return f"Navigated forward: {page.url}"
        except Exception as e:
            return f"Forward error: {e}"

    async def reload(self) -> str:
        page = await self._get_page()
        try:
            await page.reload(timeout=15_000)
            return f"Page reloaded: {page.url}"
        except Exception as e:
            return f"Reload error: {e}"

    async def close_browser(self) -> str:
        await self._async_close()
        return f"{self.browser_name} closed."

class _SessionRegistry:
    """Tüm aktif tarayıcı oturumlarını yönetir."""

    def __init__(self):
        self._sessions:       dict[str, _BrowserSession] = {}
        self._active_browser: str                        = ""
        self._lock            = threading.Lock()

    def _get_or_create(self, browser_name: str) -> _BrowserSession:
        with self._lock:
            if browser_name not in self._sessions:
                sess = _BrowserSession(browser_name)
                sess.start()
                self._sessions[browser_name] = sess
                print(f"[Registry] New session: {browser_name}")
            return self._sessions[browser_name]

    def get(self, browser_name: str | None = None) -> _BrowserSession:
        if not browser_name:
            browser_name = self._active_browser or _detect_default_browser()
        browser_name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
        sess = self._get_or_create(browser_name)
        self._active_browser = browser_name
        return sess

    def switch(self, browser_name: str) -> str:
        browser_name = _ALIASES.get(browser_name.lower().strip(), browser_name.lower().strip())
        self._get_or_create(browser_name)
        self._active_browser = browser_name
        return f"Active browser → {browser_name}"

    def close_one(self, browser_name: str) -> str:
        with self._lock:
            sess = self._sessions.pop(browser_name, None)
        if sess:
            sess.close()
            if self._active_browser == browser_name:
                self._active_browser = ""
            return f"{browser_name} closed."
        return f"No active session for: {browser_name}"

    def close_all(self) -> str:
        with self._lock:
            names    = list(self._sessions.keys())
            sessions = list(self._sessions.values())
            self._sessions.clear()
            self._active_browser = ""
        for s in sessions:
            try:
                s.close()
            except Exception:
                pass
        return "All browsers closed: " + (", ".join(names) if names else "none")

    def list_sessions(self) -> str:
        with self._lock:
            if not self._sessions:
                return "No active browser sessions."
            lines = []
            for name in self._sessions:
                marker = " ◀ active" if name == self._active_browser else ""
                lines.append(f"  • {name}{marker}")
            return "Open browsers:\n" + "\n".join(lines)


_registry = _SessionRegistry()

def browser_control(
    parameters:    dict = None,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    params  = parameters or {}
    action  = params.get("action", "").lower().strip()
    browser = params.get("browser", "").lower().strip() or None
    result  = "Unknown action."

    if action == "switch":
        target = browser or params.get("target", "").lower().strip()
        result = _registry.switch(target) if target else "Please specify a browser."
        _log(player, result)
        return result

    if action == "list_browsers":
        result = _registry.list_sessions()
        _log(player, result)
        return result

    if action == "close_all":
        result = _registry.close_all()
        _log(player, result)
        return result

    if action in ("launch", "open", "start"):
        target = browser or params.get("browser", "") or _detect_default_browser()
        result = launch_native_browser(target, params.get("url", ""))
        _log(player, result)
        return result

    try:
        sess = _registry.get(browser)
    except Exception as e:
        native = launch_native_browser(browser or "chrome", params.get("url", ""))
        if "Could not find" not in native:
            result = f"{native} (Playwright unavailable: {e})"
        else:
            result = f"Could not start browser session: {e}"
        _log(player, result)
        return result

    try:
        if action == "go_to":
            try:
                result = sess.run(sess.go_to(params.get("url", "")))
            except Exception as e:
                native = launch_native_browser(sess.browser_name, params.get("url", ""))
                result = native if "Could not find" not in native else f"Navigation failed: {e}"
        elif action == "search":
            result = sess.run(sess.search(params.get("query", ""), params.get("engine", "google")))
        elif action == "click":
            result = sess.run(sess.click(params.get("selector"), params.get("text")))
        elif action == "type":
            result = sess.run(sess.type_text(
                params.get("selector"), params.get("text", ""), params.get("clear_first", True)))
        elif action == "scroll":
            result = sess.run(sess.scroll(params.get("direction", "down"), int(params.get("amount", 500))))
        elif action == "fill_form":
            result = sess.run(sess.fill_form(params.get("fields", {})))
        elif action == "smart_click":
            result = sess.run(sess.smart_click(params.get("description", "")))
        elif action == "smart_type":
            result = sess.run(sess.smart_type(params.get("description", ""), params.get("text", "")))
        elif action == "get_text":
            result = sess.run(sess.get_text())
        elif action == "get_url":
            result = sess.run(sess.get_url())
        elif action == "press":
            result = sess.run(sess.press(params.get("key", "Enter")))
        elif action == "new_tab":
            result = sess.run(sess.new_tab(params.get("url", "")))
        elif action == "close_tab":
            result = sess.run(sess.close_tab())
        elif action == "screenshot":
            result = sess.run(sess.screenshot(params.get("path")))
        elif action == "back":
            result = sess.run(sess.back())
        elif action == "forward":
            result = sess.run(sess.forward())
        elif action == "reload":
            result = sess.run(sess.reload())
        elif action == "close":
            target = browser or _registry._active_browser
            result = _registry.close_one(target) if target else "No browser specified."
        else:
            result = f"Unknown browser action: '{action}'"

    except concurrent.futures.TimeoutError:
        result = f"Browser action '{action}' timed out (60s)."
    except Exception as e:
        result = f"Browser error ({action}): {e}"

    _log(player, result)
    return result


def _log(player, text: str):
    short = str(text)[:80]
    short = short.encode("ascii", errors="replace").decode("ascii")
    print(f"[Browser] {short}")
    if player:
        player.write_log(f"[browser] {short[:60]}")
        if hasattr(player, "write_thought"):
            player.write_thought(f"Browser: {short[:90]}")
