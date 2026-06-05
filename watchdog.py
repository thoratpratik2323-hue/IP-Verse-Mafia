"""
watchdog.py — IP Prime Self-Healing Process Manager

Runs as a separate process and monitors main.py.
If IP Prime crashes → automatically restarts it.
Logs all crashes with timestamps.
Shows Windows desktop notification on crash/restart.
"""

import subprocess
import sys
import time
import os
import json
import threading
from pathlib import Path
from datetime import datetime

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR        = Path(__file__).resolve().parent
LOG_FILE        = BASE_DIR / "logs" / "watchdog.log"
CRASH_LOG_FILE  = BASE_DIR / "logs" / "crash_history.json"
MAIN_SCRIPT     = BASE_DIR / "main.py"
PYTHON_EXE      = sys.executable

MAX_RESTARTS        = 10          # Max restarts before giving up
RESTART_COOLDOWN    = 5           # Seconds between restarts
HEALTH_CHECK_EVERY  = 30          # Seconds between health checks
CRASH_WINDOW        = 120         # If crash in < 120s, count as fast crash

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    bat_str = ""
    try:
        import psutil
        bat = psutil.sensors_battery()
        if bat:
            bat_str = f" [Battery: {bat.percent}% {'Charging' if bat.power_plugged else 'Discharging'}]"
    except Exception:
        pass
    line = f"[{timestamp}]{bat_str} {msg}"
    try:
        print(line)
    except UnicodeEncodeError:
        try:
            print(line.encode("ascii", errors="replace").decode("ascii"))
        except Exception:
            pass
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_crash_history() -> list:
    if CRASH_LOG_FILE.exists():
        try:
            with open(CRASH_LOG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_crash(reason: str, restart_count: int):
    history = load_crash_history()
    history.append({
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "restart_number": restart_count
    })
    # Keep only last 50 crashes
    history = history[-50:]
    with open(CRASH_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def notify_windows(title: str, message: str):
    """Show a Windows toast notification (non-blocking)."""
    try:
        from winotify import Notification, audio
        toast = Notification(
            app_id="IP Prime",
            title=title,
            msg=message,
            icon=str(BASE_DIR / "assets" / "logo.png")
        )
        toast.set_audio(audio.Default, loop=False)
        toast.show()
    except ImportError:
        # Fallback: print to console if winotify not installed
        log(f"[NOTIFY] {title}: {message}")
    except Exception as e:
        log(f"[NOTIFY ERROR] {e}")


def notify_email_on_crash(restart_count: int, reason: str):
    """Send crash alert email if email_ai is configured."""
    try:
        sys.path.insert(0, str(BASE_DIR))
        from actions.email_ai import send_email_alert
        subject = f"⚠️ IP Prime Crashed & Restarted (#{restart_count})"
        body = (
            f"IP Prime crashed and was automatically restarted.\n\n"
            f"Restart #{restart_count}\n"
            f"Reason: {reason}\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"The watchdog has automatically recovered the system."
        )
        send_email_alert(subject, body)
        log(f"[WATCHDOG] 📧 Crash alert email sent.")
    except Exception as e:
        log(f"[WATCHDOG] Email alert failed: {e}")


# ── Main Watchdog Loop ────────────────────────────────────────────────────────
class IPPrimeWatchdog:
    def __init__(self):
        self.restart_count   = 0
        self.process         = None
        self.running         = True
        self.start_time      = None

    def start_prime(self) -> subprocess.Popen:
        """Launches main.py as a subprocess."""
        log(f"[WATCHDOG] 🚀 Starting IP Prime (attempt #{self.restart_count + 1})...")
        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["IP_PRIME_WATCHDOG"] = "1"   # So main.py knows it's being watched

        proc = subprocess.Popen(
            [PYTHON_EXE, str(MAIN_SCRIPT)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=None,   # Let output flow to terminal
            stderr=None,
        )
        self.start_time = time.time()
        log(f"[WATCHDOG] ✅ IP Prime PID: {proc.pid}")
        return proc

    def run(self):
        log("=" * 60)
        log("[WATCHDOG] 🛡️ IP Prime Watchdog started.")
        log(f"[WATCHDOG] Monitoring: {MAIN_SCRIPT}")
        log("=" * 60)

        notify_windows("IP Prime Watchdog", "🛡️ Self-healing monitor active!")

        while self.running:
            # ── Launch ──────────────────────────────────────────────────
            self.process = self.start_prime()

            # ── Wait for process to finish ───────────────────────────────
            self.process.wait()
            exit_code  = self.process.returncode
            uptime_sec = time.time() - self.start_time

            # ── Clean exit (user closed it) ──────────────────────────────
            if exit_code == 0:
                log("[WATCHDOG] 👋 IP Prime exited cleanly (code 0). Stopping watchdog.")
                break

            # ── Crash detected ───────────────────────────────────────────
            self.restart_count += 1
            reason = f"Exit code {exit_code} after {uptime_sec:.1f}s uptime"
            log(f"[WATCHDOG] 💥 CRASH DETECTED! {reason}")
            save_crash(reason, self.restart_count)

            notify_windows(
                "⚠️ IP Prime Crashed!",
                f"Auto-restarting... (attempt #{self.restart_count})"
            )

            # Send email alert in background thread
            threading.Thread(
                target=notify_email_on_crash,
                args=(self.restart_count, reason),
                daemon=True
            ).start()

            # ── Give up if too many crashes ──────────────────────────────
            if self.restart_count >= MAX_RESTARTS:
                log(f"[WATCHDOG] ❌ Max restarts ({MAX_RESTARTS}) reached. Giving up.")
                notify_windows(
                    "❌ IP Prime Failed",
                    f"Could not recover after {MAX_RESTARTS} attempts. Manual restart needed."
                )
                break

            # ── Cooldown before restart ──────────────────────────────────
            log(f"[WATCHDOG] ⏳ Waiting {RESTART_COOLDOWN}s before restart...")
            time.sleep(RESTART_COOLDOWN)

        log("[WATCHDOG] 🔴 Watchdog stopped.")


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    watchdog = IPPrimeWatchdog()
    try:
        watchdog.run()
    except KeyboardInterrupt:
        log("[WATCHDOG] ⌨️ Stopped by user (Ctrl+C).")
        if watchdog.process and watchdog.process.poll() is None:
            watchdog.process.terminate()
            log("[WATCHDOG] IP Prime process terminated.")
