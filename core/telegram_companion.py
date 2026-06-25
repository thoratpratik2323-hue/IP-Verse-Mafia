import os
import io
import sys
import time
import json
import logging
import threading
import subprocess
import requests
import mss
import PIL.Image
from pathlib import Path

logger = logging.getLogger("saturday.telegram_companion")

ALLOWED_BASE_COMMANDS = {"dir", "ls", "ping", "whoami", "echo", "git status", "git log -n 5", "tasklist", "systeminfo", "type", "cat"}

class TelegramCompanion:
    def __init__(self):
        self._thread = None
        self._stop_event = threading.Event()
        self.base_dir = Path(__file__).resolve().parent.parent
        self.settings_path = self.base_dir / "config" / "settings.json"
        self.last_update_id = 0
        self.companion_start_time = time.time()
        
        # Caching settings file
        self._cached_settings = {}
        self._last_settings_load_time = 0.0
        self._last_settings_mtime = 0.0
        
        # Rate limiting state
        self.command_timestamps = []

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="TelegramCompanionThread")
        self._thread.start()
        logger.info("Telegram Companion Bot thread started.")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("Telegram Companion Bot thread stopped.")

    def _load_settings(self) -> dict:
        if not self.settings_path.exists():
            return {}
            
        now = time.time()
        try:
            mtime = self.settings_path.stat().st_mtime
            # Only hit the disk at most once every 5 seconds, or if file modified time has changed
            if mtime == self._last_settings_mtime and now - self._last_settings_load_time < 5.0:
                return self._cached_settings
                
            self._last_settings_mtime = mtime
            self._last_settings_load_time = now
            data = json.loads(self.settings_path.read_text(encoding="utf-8"))
            self._cached_settings = data
            return data
        except Exception:
            return self._cached_settings

    def _loop(self):
        while not self._stop_event.is_set():
            settings = self._load_settings()
            token = settings.get("telegram_bot_token", "").strip()
            chat_id = settings.get("telegram_chat_id", "").strip()

            if not token or not chat_id:
                # Wait for configuration
                self._stop_event.wait(5.0)
                continue

            try:
                self._poll_updates(token, chat_id)
            except Exception as e:
                logger.error("Error polling Telegram updates: %s", e)
                
            self._stop_event.wait(2.0)

    def _poll_updates(self, token: str, chat_id: str):
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        params = {"offset": self.last_update_id + 1, "timeout": 1}
        try:
            r = requests.get(url, params=params, timeout=5)
            if r.status_code != 200:
                return
            data = r.json()
            if not data.get("ok"):
                return
            
            updates = data.get("result", [])
            for update in updates:
                self.last_update_id = update.get("update_id", self.last_update_id)
                message = update.get("message", {})
                chat = message.get("chat", {})
                from_chat_id = str(chat.get("id", ""))

                # Security check: ignore unauthorized users
                if from_chat_id != str(chat_id):
                    logger.warning("Ignored unauthorized Telegram update from chat: %s", from_chat_id)
                    continue

                text = message.get("text", "").strip()
                if not text:
                    continue

                logger.info("Received Telegram remote command: %s", text)
                self._handle_command(token, chat_id, text)
        except Exception as e:
            logger.debug("Updates request error: %s", e)

    def _handle_command(self, token: str, chat_id: str, text: str):
        # 1. Rate limiting check (max 10 commands per minute)
        now = time.time()
        self.command_timestamps = [t for t in self.command_timestamps if now - t < 60.0]
        if len(self.command_timestamps) >= 10:
            self._send_text(token, chat_id, "⚠️ Rate limit exceeded: maximum 10 commands per minute. Command ignored.")
            return
        self.command_timestamps.append(now)

        # Notify UI on message arrival
        import ui
        ui_inst = ui.get_ui()
        if ui_inst:
            ui_inst.show_custom_alert("Telegram Command", f"Remote command received:\n\n{text}", "telegram")
            ui_inst.write_log(f"SYS: Telegram command received: {text}")

        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        reply = ""
        
        if cmd == "/status":
            import psutil
            import platform
            import main
            
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            
            # Retrieve real session boot time if available
            boot = getattr(main, "BOOT_TIME", self.companion_start_time)
            uptime = int(time.time() - boot)
            hours, remainder = divmod(uptime, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m {seconds}s"
            
            reply = (
                f"📊 *S.A.T.U.R.D.A.Y Status Report*\n\n"
                f"🖥️ *OS:* {platform.system()} ({platform.release()})\n"
                f"🔥 *CPU:* {cpu}%\n"
                f"💾 *RAM:* {mem}%\n"
                f"⏱️ *Uptime:* {uptime_str}\n"
                f"🎙️ *State:* Online"
            )
            self._send_text(token, chat_id, reply)

        elif cmd == "/screen":
            self._send_text(token, chat_id, "📸 Capturing screen...")
            self._send_screenshot(token, chat_id)

        elif cmd == "/find":
            if not args:
                reply = "⚠️ Please specify a search term, e.g., `/find index.html`"
            else:
                reply = self._find_files(args)
            self._send_text(token, chat_id, reply)

        elif cmd == "/cmd":
            if not args:
                reply = "⚠️ Please specify a command, e.g., `/cmd dir`"
            else:
                settings = self._load_settings()
                allow_cmd = settings.get("telegram_allow_cmd", False)
                if not allow_cmd:
                    reply = "❌ Shell command execution blocked: `/cmd` commands are currently disabled in Saturday's settings."
                else:
                    reply = self._run_shell(args)
            self._send_text(token, chat_id, reply)

        elif cmd == "/sticky":
            if not args:
                reply = "⚠️ Please specify text to add, e.g., `/sticky Buy milk`"
            else:
                reply = self._add_sticky(args)
            self._send_text(token, chat_id, reply)

        elif cmd in ["/help", "help", "?"]:
            reply = (
                f"ℹ️ *S.A.T.U.R.D.A.Y Companion Help*\n\n"
                f"Available commands:\n"
                f"📊 `/status` - System resource and session uptime report\n"
                f"📸 `/screen` - Take and send a desktop screenshot\n"
                f"🔍 `/find <term>` - Search files recursively (depth 4 max)\n"
                f"⚡ `/cmd <command>` - Execute a whitelisted terminal command\n"
                f"📝 `/sticky <text>` - Write note to Sticky Notes\n"
                f"ℹ️ `/help` - Show this help menu"
            )
            self._send_text(token, chat_id, reply)

        else:
            reply = (
                f"❓ *Unknown Command: {cmd}*\n\n"
                f"Type `/help` to see the list of available commands."
            )
            self._send_text(token, chat_id, reply)

    def _send_text(self, token: str, chat_id: str, text: str):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=5)
        except Exception as e:
            logger.error("Failed to send text to Telegram: %s", e)

    def _send_screenshot(self, token: str, chat_id: str):
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        try:
            # Cross-platform Wayland / Windows / macOS grab using mss
            with mss.MSS() as sct:
                mon = sct.monitors[1] if len(sct.monitors) >= 2 else sct.monitors[0]
                shot = sct.grab(mon)
                img = PIL.Image.frombytes("RGB", shot.size, shot.rgb)
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()
            
            files = {"photo": ("screenshot.png", img_bytes, "image/png")}
            data = {"chat_id": chat_id, "caption": "Here is Saturday's active window view, sir."}
            requests.post(url, data=data, files=files, timeout=10)
        except Exception as e:
            logger.error("Failed to send screenshot: %s", e)
            self._send_text(token, chat_id, f"❌ Failed to send screenshot: {e}")

    def _find_files(self, term: str) -> str:
        results = []
        start_time = time.time()
        max_depth = 4
        timeout = 3.0
        
        def walk(directory, depth):
            if time.time() - start_time > timeout:
                return
            if len(results) >= 10:
                return
            if depth > max_depth:
                return
                
            try:
                for entry in os.scandir(directory):
                    if entry.name.startswith('.') or any(part in entry.name for part in ["AppData", "node_modules", "__pycache__", "Local Settings", "Templates"]):
                        continue
                    if entry.is_dir():
                        walk(entry.path, depth + 1)
                    elif entry.is_file() and term.lower() in entry.name.lower():
                        results.append(entry.path)
                        if len(results) >= 10:
                            return
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
                
        try:
            walk(str(Path.home()), 1)
            if not results:
                return f"🔍 No files found matching '{term}'."
            
            res_str = f"🔍 *Found files matching '{term}':*\n"
            for r in results:
                res_str += f"`{r}`\n"
            if time.time() - start_time > timeout:
                res_str += "\n⚠️ *Search timed out (limit 3s). Results may be incomplete.*"
            return res_str
        except Exception as e:
            return f"❌ Error searching files: {e}"

    def _run_shell(self, command: str) -> str:
        try:
            # Strict Whitelisting check
            base_cmd = command.strip().split()[0].lower() if command.strip() else ""
            base_cmd = base_cmd.strip("\"'")
            if base_cmd not in ALLOWED_BASE_COMMANDS:
                return f"❌ Shell command blocked: command base '{base_cmd}' is not in the whitelist of allowed safe commands."

            res = subprocess.run(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            out = res.stdout.strip()
            err = res.stderr.strip()
            
            ret = ""
            if out:
                ret += f"*Output:*\n```\n{out}\n```\n"
            if err:
                ret += f"*Error:*\n```\n{err}\n```\n"
            if not ret:
                ret = "Command executed successfully with no output."
            return ret
        except subprocess.TimeoutExpired:
            return "❌ Command execution timed out after 10 seconds."
        except Exception as e:
            return f"❌ Execution error: {e}"

    def _add_sticky(self, text: str) -> str:
        try:
            notes_path = self.base_dir / "memory" / "sticky_notes.txt"
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            existing = ""
            if notes_path.exists():
                existing = notes_path.read_text(encoding="utf-8").strip()
            
            new_content = existing + f"\n- {text}" if existing else f"- {text}"
            notes_path.write_text(new_content, encoding="utf-8")
            
            # Instantly update UI text edit
            import ui
            ui_inst = ui.get_ui()
            if ui_inst and ui_inst._win:
                ui_inst._win._sticky_edit.setText(new_content)
                
            return "📝 Note successfully added to Saturday's Sticky Notes."
        except Exception as e:
            return f"❌ Failed to write note: {e}"
