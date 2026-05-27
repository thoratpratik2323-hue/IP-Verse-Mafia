"""
telegram_bot.py — Background Telegram bot remote desktop controller for IP Prime.

Allows remote query status, shell commands, screenshots, and text outputs via Telegram.
Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (for owner validation) environment variables.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.telegram_bot")

BASE_DIR = Path(__file__).resolve().parent.parent

# Global pointer to active bot thread to avoid duplicate runners
_ACTIVE_BOT_THREAD: Optional[threading.Thread] = None
_STOP_SIGNAL: bool = False

def send_telegram_message(message: str) -> str:
    """Dispatches a text notification to the configured owner chat ID."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        logger.warning("Telegram Bot Token or Chat ID environment parameters missing.")
        return f"Simulated Telegram push message: '{message}' (Configuration missing)."

    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
        res = requests.post(url, json=payload, timeout=8)
        if res.status_code == 200:
            return "Telegram push message successfully sent, sir!"
        else:
            return f"Telegram API returned status code: {res.status_code}."
    except Exception as e:
        logger.error("Failed to send telegram notification message: %s", e)
        return f"Telegram connection error occurred: {e}."

def get_telegram_updates() -> str:
    """Manually polls for pending updates from Telegram API servers."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return "Telegram bot token is not configured, sir."

    try:
        import requests
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            updates = res.json().get("result", [])
            return f"Fetched {len(updates)} pending updates successfully, sir!"
    except Exception as e:
        logger.error("Error polling Telegram updates: %s", e)
    return "Error occurred while polling live Telegram API updates, sir."

def _bot_polling_loop(token: str, chat_id: str, player: Optional[Any] = None):
    """Background polling worker that processes owner commands."""
    global _STOP_SIGNAL
    logger.info("Starting Telegram Bot Background polling daemon...")
    offset = 0
    
    import requests
    from actions.computer_settings import computer_settings
    
    while not _STOP_SIGNAL:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=5"
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                updates = res.json().get("result", [])
                for u in updates:
                    update_id = u.get("update_id", 0)
                    offset = update_id + 1
                    
                    message_obj = u.get("message", {})
                    sender_chat = message_obj.get("chat", {})
                    sender_id = str(sender_chat.get("id", ""))
                    
                    # Validate owner access
                    if sender_id != chat_id:
                        logger.warning("Unauthenticated Telegram contact attempt from chat ID: %s", sender_id)
                        continue
                        
                    text = message_obj.get("text", "").strip()
                    if not text:
                        continue
                        
                    logger.info("Received Telegram remote command: %s", text)
                    reply_text = ""
                    
                    # Command Parsing
                    if text.startswith("/status"):
                        import psutil
                        cpu = psutil.cpu_percent()
                        ram = psutil.virtual_memory().percent
                        reply_text = f"⚙️ *IP Prime Desktop Status*:\n• CPU: {cpu}%\n• RAM: {ram}%\n• Systems fully operational, sir!"
                        
                    elif text.startswith("/say"):
                        phrase = text.replace("/say", "", 1).strip()
                        if phrase:
                            if player and hasattr(player, "write_log"):
                                player.write_log(f"💬 [Telegram Bot Remote]: {phrase}")
                            reply_text = f"Speaking: '{phrase}', sir!"
                        else:
                            reply_text = "Please specify text e.g. `/say Hello World`"
                            
                    elif text.startswith("/volume"):
                        val_str = text.replace("/volume", "", 1).strip()
                        try:
                            vol = int(val_str)
                            computer_settings({"action": "set_volume", "value": str(vol)})
                            reply_text = f"🔊 System volume set successfully to {vol}%, sir!"
                        except Exception:
                            reply_text = "Volume format error. Use `/volume 50`"
                            
                    elif text.startswith("/screenshot"):
                        # Take screenshot and push photo
                        try:
                            import mss
                            photo_path = BASE_DIR / "data" / "tele_screen.png"
                            photo_path.parent.mkdir(parents=True, exist_ok=True)
                            with mss.mss() as sct:
                                sct.shot(output=str(photo_path))
                                
                            # Upload photo via telegram multipart API
                            send_url = f"https://api.telegram.org/bot{token}/sendPhoto"
                            with open(photo_path, "rb") as photo_file:
                                files = {"photo": photo_file}
                                data = {"chat_id": chat_id, "caption": "🖥️ Current screen capture, sir!"}
                                requests.post(send_url, data=data, files=files, timeout=12)
                            continue  # Replied with photo, skip sendMessage
                        except Exception as sc_err:
                            reply_text = f"Failed to capture screen: {sc_err}"
                            
                    elif text.startswith("/run"):
                        cmd = text.replace("/run", "", 1).strip()
                        if cmd:
                            import subprocess
                            try:
                                proc = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=8)
                                out = proc.stdout or ""
                                err = proc.stderr or ""
                                reply_text = f"💻 *Shell Output*:\n```\n{out[:800]}\n{err[:400]}\n```"
                            except Exception as exec_err:
                                reply_text = f"Shell execution error: {exec_err}"
                        else:
                            reply_text = "Please specify a shell command, e.g. `/run dir`"
                    else:
                        reply_text = (
                            "🤖 *IP Prime Bot Online*\n"
                            "Supported commands:\n"
                            "• `/status` — System load diagnostics\n"
                            "• `/screenshot` — Capture main monitor display\n"
                            "• `/say [text]` — Force speech log output\n"
                            "• `/volume [0-100]` — Set audio volume\n"
                            "• `/run [cmd]` — Execute shell commands"
                        )
                        
                    # Send response back
                    if reply_text:
                        send_url = f"https://api.telegram.org/bot{token}/sendMessage"
                        payload = {"chat_id": chat_id, "text": reply_text, "parse_mode": "Markdown"}
                        requests.post(send_url, json=payload, timeout=8)
                        
        except Exception as e:
            logger.error("Error in telegram bot polling thread loop: %s", e)
            time.sleep(5)
        time.sleep(1.5)

def start_bot_daemon(player: Optional[Any] = None) -> str:
    """Spawns the background bot listener thread if not already running."""
    global _ACTIVE_BOT_THREAD, _STOP_SIGNAL
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    
    if not token or not chat_id:
        return "Telegram credentials missing in env, cannot initiate daemon bot, sir."
        
    if _ACTIVE_BOT_THREAD and _ACTIVE_BOT_THREAD.is_alive():
        return "Telegram remote control daemon is already active, sir."

    _STOP_SIGNAL = False
    _ACTIVE_BOT_THREAD = threading.Thread(
        target=_bot_polling_loop,
        args=(token, chat_id, player),
        daemon=True,
        name="TelegramBotDaemon"
    )
    _ACTIVE_BOT_THREAD.start()
    return "Telegram remote control bot daemon initiated in background successfully, sir!"

def stop_bot_daemon() -> str:
    """Signals the background bot listener thread to terminate."""
    global _STOP_SIGNAL
    _STOP_SIGNAL = True
    return "Telegram remote control bot daemon stopped successfully, sir!"

def telegram_bot(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for telegram_bot action."""
    action = parameters.get("action", "start").lower().strip()
    message = parameters.get("message", "")
    
    if action == "start":
        return start_bot_daemon(player)
    elif action == "stop":
        return stop_bot_daemon()
    elif action == "send":
        return send_telegram_message(message)
    elif action == "poll":
        return get_telegram_updates()
    else:
        return "Unknown Telegram Bot action parameter, sir."
