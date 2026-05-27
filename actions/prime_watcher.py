# actions/prime_watcher.py
"""
IP Prime — Live File Watcher Daemon
Watches a project directory for .py file saves.
On every save: runs py_compile, and if syntax errors are found,
auto-fixes them using Gemini. Shows live feedback in the web HUD.
"""

import json
import sys
import time
import threading
import subprocess
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
        return config.get("coding_api_key") or config["gemini_api_key"]


def _log_hud(msg: str, player=None):
    print(f"[PrimeWatcher] {msg}")
    try:
        from actions.web_hud import log_event
        log_event(f"[Watcher] {msg}")
    except Exception:
        pass
    if player:
        try:
            player.write_log(f"[Watcher] {msg}")
        except Exception:
            pass


def _compile_check(file_path: Path) -> tuple[bool, str]:
    """Returns (ok, error_message)."""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(file_path)],
        capture_output=True, text=True,
        encoding="utf-8", errors="replace"
    )
    if result.returncode == 0:
        return True, ""
    err = (result.stderr or result.stdout or "Unknown compilation error").strip()
    return False, err


def _auto_fix_file(file_path: Path, error: str, player=None) -> bool:
    """Uses Gemini to fix syntax errors in a file. Returns True if fixed."""
    try:
        code = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        _log_hud(f"Cannot read {file_path.name} for fix: {e}", player)
        return False

    _log_hud(f"🔧 Auto-fixing {file_path.name}...", player)

    try:
        from google import genai
        client = genai.Client(api_key=_get_api_key())

        prompt = f"""You are an expert Python debugger. The following file has a syntax error. Fix it.
Return ONLY the complete fixed code — no markdown, no backticks, no explanation.

File: {file_path.name}
Syntax Error:
{error}

Broken Code:
{code}

Fixed Code:"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        import re
        fixed = response.text.strip()
        fixed = re.sub(r"^```[a-zA-Z]*\n?", "", fixed)
        fixed = re.sub(r"\n?```$", "", fixed)
        fixed = fixed.strip()

        if not fixed:
            _log_hud(f"⚠️ Gemini returned empty fix for {file_path.name}", player)
            return False

        # Verify the fix compiles before writing
        try:
            compile(fixed, str(file_path), "exec")
        except SyntaxError as e:
            _log_hud(f"⚠️ Generated fix still has syntax error: {e}", player)
            return False

        file_path.write_text(fixed, encoding="utf-8")
        _log_hud(f"✅ {file_path.name} auto-fixed and saved!", player)
        return True

    except Exception as e:
        _log_hud(f"❌ Auto-fix failed for {file_path.name}: {e}", player)
        return False


class PrimeFileWatcher:
    """Watchdog-free file watcher using polling. No extra dependencies needed."""

    def __init__(self, watch_path: str, auto_fix: bool = True, auto_test: bool = False, player=None):
        self.watch_path = Path(watch_path).resolve()
        self.auto_fix   = auto_fix
        self.auto_test  = auto_test
        self.player     = player
        self._running   = False
        self._thread: threading.Thread | None = None
        self._file_mtimes: dict[Path, float] = {}
        self._fix_cooldown: dict[Path, float] = {}  # prevent fix-loop
        self._COOLDOWN_SEC = 5.0

    def _scan_initial(self):
        """Record current mtimes of all .py files."""
        self._file_mtimes.clear()
        for f in self.watch_path.rglob("*.py"):
            try:
                self._file_mtimes[f] = f.stat().st_mtime
            except Exception:
                pass

    def _get_changed_files(self) -> list[Path]:
        changed = []
        try:
            current_files = list(self.watch_path.rglob("*.py"))
        except Exception:
            return []

        for f in current_files:
            try:
                mtime = f.stat().st_mtime
            except Exception:
                continue
            if mtime != self._file_mtimes.get(f):
                self._file_mtimes[f] = mtime
                changed.append(f)

        return changed

    def _handle_file_change(self, f: Path):
        _log_hud(f"📝 Modified: {f.name}", self.player)

        ok, error = _compile_check(f)
        if ok:
            _log_hud(f"✅ {f.name} — syntax OK", self.player)
        else:
            _log_hud(f"❌ {f.name} — syntax error: {error[:120]}", self.player)
            if self.auto_fix:
                now = time.time()
                last_fix = self._fix_cooldown.get(f, 0)
                if now - last_fix > self._COOLDOWN_SEC:
                    self._fix_cooldown[f] = now
                    fixed = _auto_fix_file(f, error, self.player)
                    if fixed:
                        # Re-check after fix
                        ok2, err2 = _compile_check(f)
                        if ok2:
                            _log_hud(f"✅ {f.name} — fix verified, syntax clean!", self.player)
                        else:
                            _log_hud(f"⚠️ {f.name} — fix applied but still has issues: {err2[:80]}", self.player)
                else:
                    _log_hud(f"⏳ {f.name} — cooldown active, skipping auto-fix", self.player)

        if self.auto_test:
            self._run_tests(f)

    def _run_tests(self, f: Path):
        """Run pytest for the modified file's test counterpart if it exists."""
        try:
            stem = f.stem
            project_root = self.watch_path
            test_candidates = list(project_root.rglob(f"test_{stem}.py")) + \
                              list(project_root.rglob(f"{stem}_test.py"))
            if not test_candidates:
                return
            test_file = test_candidates[0]
            _log_hud(f"🧪 Running tests: {test_file.name}", self.player)
            result = subprocess.run(
                [sys.executable, "-m", "pytest", str(test_file), "--tb=short", "-q"],
                capture_output=True, text=True, timeout=30,
                encoding="utf-8", errors="replace",
                cwd=str(project_root)
            )
            output = (result.stdout + result.stderr).strip()
            short = output[-500:] if len(output) > 500 else output
            _log_hud(f"🧪 Test result: {short}", self.player)
        except Exception as e:
            _log_hud(f"⚠️ Test run failed: {e}", self.player)

    def _poll_loop(self):
        _log_hud(f"👁️ Watching: {self.watch_path}", self.player)
        self._scan_initial()
        while self._running:
            time.sleep(0.8)
            changed = self._get_changed_files()
            for f in changed:
                try:
                    self._handle_file_change(f)
                except Exception as e:
                    _log_hud(f"⚠️ Error handling {f.name}: {e}", self.player)

        _log_hud("🛑 Watcher stopped.", self.player)

    def start(self):
        if self._running:
            return
        if not self.watch_path.exists():
            raise FileNotFoundError(f"Path not found: {self.watch_path}")
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="PrimeWatcher")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None


# Module-level registry so start/stop can be called from tool dispatcher
_active_watchers: dict[str, PrimeFileWatcher] = {}
_watchers_lock = threading.Lock()


def prime_watcher(parameters: dict, player=None) -> str:
    """Main tool entry point called from main.py dispatcher."""
    p      = parameters or {}
    action = p.get("action", "start").lower().strip()
    path   = p.get("path", "").strip()
    auto_fix  = bool(p.get("auto_fix", True))
    auto_test = bool(p.get("auto_test", False))

    if action == "start":
        if not path:
            return "Please provide a project directory path to watch, sir."
        resolved = str(Path(path).resolve())
        with _watchers_lock:
            if resolved in _active_watchers:
                return f"Watcher is already active on: {resolved}"
            try:
                w = PrimeFileWatcher(
                    watch_path=resolved,
                    auto_fix=auto_fix,
                    auto_test=auto_test,
                    player=player
                )
                w.start()
                _active_watchers[resolved] = w
                opts = []
                if auto_fix:  opts.append("auto-fix enabled")
                if auto_test: opts.append("auto-test enabled")
                opts_str = " | ".join(opts) if opts else "monitoring only"
                return (
                    f"✅ Live File Watcher started on: {resolved}\n"
                    f"Options: {opts_str}\n"
                    f"Every .py save → instant syntax check{' + Gemini auto-fix' if auto_fix else ''}. "
                    f"Live logs in web HUD terminal."
                )
            except Exception as e:
                return f"Failed to start watcher: {e}"

    elif action == "stop":
        with _watchers_lock:
            if not _active_watchers:
                return "No active file watchers to stop, sir."
            if path:
                resolved = str(Path(path).resolve())
                w = _active_watchers.pop(resolved, None)
                if w:
                    w.stop()
                    return f"Watcher stopped for: {resolved}"
                return f"No active watcher found for: {resolved}"
            else:
                stopped = []
                for key, w in list(_active_watchers.items()):
                    w.stop()
                    stopped.append(key)
                _active_watchers.clear()
                return f"Stopped {len(stopped)} watcher(s)."

    elif action == "status":
        with _watchers_lock:
            if not _active_watchers:
                return "No active file watchers running, sir."
            lines = [f"Active file watchers ({len(_active_watchers)}):"]
            for path_key, w in _active_watchers.items():
                status = "🟢 Running" if w._running else "🔴 Stopped"
                lines.append(f"  {status} — {path_key}")
            return "\n".join(lines)

    else:
        return f"Unknown watcher action: '{action}'. Use start, stop, or status."
