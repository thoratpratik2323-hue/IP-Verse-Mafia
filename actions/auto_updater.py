"""
auto_updater.py — IP Prime Self-Update Engine

IP Prime checks GitHub for updates daily at 3 AM.
If updates found → git pull → restart via watchdog.
Fully autonomous — no human needed!
"""

import subprocess
import sys
import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime, date

BASE_DIR        = Path(__file__).resolve().parent.parent
LOG_FILE        = BASE_DIR / "logs" / "updater.log"
LAST_CHECK_FILE = BASE_DIR / "data" / "last_update_check.json"
UPDATE_HOUR     = 3   # 3 AM daily check


def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [AutoUpdater] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _load_last_check() -> str:
    try:
        if LAST_CHECK_FILE.exists():
            with open(LAST_CHECK_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("last_check_date", "")
    except Exception:
        pass
    return ""


def _save_last_check():
    LAST_CHECK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LAST_CHECK_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_check_date": str(date.today())}, f)


def _run_git(args: list) -> tuple[int, str, str]:
    """Run a git command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["git"] + args,
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def check_for_updates() -> bool:
    """Returns True if remote has new commits ahead of local."""
    try:
        # Fetch remote without merging
        code, out, err = _run_git(["fetch", "origin", "main", "--quiet"])
        if code != 0:
            log(f"⚠️ git fetch failed: {err}")
            return False

        # Compare local HEAD with origin/main
        code, behind, _ = _run_git(["rev-list", "HEAD..origin/main", "--count"])
        if code != 0:
            return False

        commits_behind = int(behind) if behind.isdigit() else 0
        if commits_behind > 0:
            log(f"🔔 {commits_behind} new commit(s) available on GitHub!")
            return True
        else:
            log("✅ Already up to date.")
            return False
    except Exception as e:
        log(f"Error checking updates: {e}")
        return False


def apply_update() -> bool:
    """Pulls latest code from GitHub. Returns True on success."""
    try:
        log("⬇️ Pulling latest code from GitHub...")
        code, out, err = _run_git(["pull", "origin", "main", "--rebase"])
        if code == 0:
            log(f"✅ Update applied successfully!\n{out}")
            return True
        else:
            log(f"❌ git pull failed: {err}")
            return False
    except Exception as e:
        log(f"Error applying update: {e}")
        return False


def install_new_dependencies() -> bool:
    """Installs any new requirements after an update."""
    req_file = BASE_DIR / "requirements-windows.txt"
    if not req_file.exists():
        req_file = BASE_DIR / "requirements.txt"
    if not req_file.exists():
        return True   # No req file, skip

    try:
        log("📦 Checking for new dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            log("✅ Dependencies up to date.")
            return True
        else:
            log(f"⚠️ pip install warning: {result.stderr[:200]}")
            return True   # Non-fatal
    except Exception as e:
        log(f"Dependency install error: {e}")
        return False


def restart_prime():
    """Asks the watchdog to restart by killing the current main process."""
    log("🔄 Requesting restart via watchdog...")
    try:
        # Write a restart signal file that watchdog can detect
        signal_file = BASE_DIR / "CODING PROJECTS" / "ip_prime_ipc.json"
        if signal_file.exists():
            with open(signal_file, "w", encoding="utf-8") as f:
                json.dump({"command": "restart", "reason": "auto_update"}, f)
            log("✅ Restart signal sent to watchdog.")
        else:
            # Fallback: exit current process — watchdog will restart
            log("⚠️ IPC not found. Exiting for watchdog to restart...")
            time.sleep(2)
            os._exit(0)
    except Exception as e:
        log(f"Restart signal error: {e}")


def run_update_cycle() -> str:
    """Full update cycle: check → pull → deps → restart. Returns status string."""
    log("🔍 Starting daily update check...")

    if not check_for_updates():
        _save_last_check()
        return "✅ IP Prime is already up to date."

    if not apply_update():
        return "❌ Update download failed. Will retry tomorrow."

    install_new_dependencies()
    _save_last_check()

    log("🚀 Update complete! Restarting IP Prime...")
    threading.Thread(target=restart_prime, daemon=True).start()
    return "✅ Update applied! IP Prime restarting with latest version."


def start_background_scheduler():
    """Runs in background — checks for updates daily at UPDATE_HOUR (3 AM)."""
    def _loop():
        log("🕐 Auto-update scheduler started (checks daily at 3 AM).")
        while True:
            now = datetime.now()
            last_check = _load_last_check()

            # Run at UPDATE_HOUR if we haven't checked today
            if now.hour == UPDATE_HOUR and str(date.today()) != last_check:
                run_update_cycle()

            time.sleep(60 * 30)   # Check every 30 minutes

    t = threading.Thread(target=_loop, daemon=True, name="AutoUpdater")
    t.start()
    return t


# ── Standalone tool function for dispatcher ───────────────────────────────────
def auto_update(force: bool = False) -> str:
    """
    Tool function: Check and apply updates on demand.
    Called by voice: 'Prime, update yourself'
    """
    last_check = _load_last_check()
    if not force and str(date.today()) == last_check:
        return "✅ Already checked for updates today. Say 'force update' to check again."
    return run_update_cycle()


if __name__ == "__main__":
    result = auto_update(force=True)
    print(result)
