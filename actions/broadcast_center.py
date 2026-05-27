"""
broadcast_center.py — Central audio/visual notification broadcast hub.

This is a standard action module for the IP Prime personal assistant suite.
"""

import json
import threading
from pathlib import Path
from actions.prime_utils import get_base_dir

BASE_DIR = get_base_dir()

def load_broadcast_config() -> dict:
    config_file = BASE_DIR / "config" / "broadcast.json"
    default_config = {
        "whatsapp": {"enabled": True, "group_link": ""},
        "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
        "desktop": {"enabled": True}
    }
    if not config_file.exists():
        return default_config
    try:
        return json.loads(config_file.read_text(encoding="utf-8"))
    except Exception:
        return default_config

def broadcast_notification(title: str, message: str) -> bool:
    """
    Sends unified push notifications to WhatsApp group link, Telegram bot, and desktop alerts.
    """
    config = load_broadcast_config()
    sent_any = False
    
    # 1. Desktop Notification Fallback
    if config.get("desktop", {}).get("enabled", True):
        print(f"[BROADCAST ALERT] {title}: {message}")
        sent_any = True
        
    # 2. Telegram Bot Broadcast
    tg_cfg = config.get("telegram", {})
    if tg_cfg.get("enabled", False):
        token = tg_cfg.get("bot_token", "").strip()
        chat_id = tg_cfg.get("chat_id", "").strip()
        if token and chat_id:
            def _send_tg():
                try:
                    import urllib.request
                    import json
                    url = f"https://api.telegram.org/bot{token}/sendMessage"
                    payload = {
                        "chat_id": chat_id,
                        "text": f"🔔 *{title}*\n\n{message}",
                        "parse_mode": "Markdown"
                    }
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode('utf-8'),
                        headers={'Content-Type': 'application/json'}
                    )
                    with urllib.request.urlopen(req, timeout=8) as response:
                        response.read()
                except Exception as e:
                    print(f"[Telegram Push Error] {e}")
            threading.Thread(target=_send_tg, daemon=True).start()
            sent_any = True
            
    # 3. WhatsApp Group Broadcast
    wa_cfg = config.get("whatsapp", {})
    if wa_cfg.get("enabled", False):
        group_link = wa_cfg.get("group_link", "").strip()
        if group_link:
            def _send_wa():
                try:
                    # Resolve contact or send message using active whatsapp bot listener
                    from actions.whatsapp_listener import WhatsAppListenerService
                    bot = WhatsAppListenerService.instance()
                    full_text = f"🔔 *{title}*\n\n{message}"
                    # If active selenium session is running, push the message dynamically
                    if bot and bot._running and hasattr(bot, "send_group_message"):
                        bot.send_group_message(group_link, full_text)
                    else:
                        # Otherwise fall back to desktop control or write-log
                        print(f"[WhatsApp Pending Bot Active] Group Link: {group_link} -> {full_text}")
                except Exception as e:
                    print(f"[WhatsApp Push Error] {e}")
            threading.Thread(target=_send_wa, daemon=True).start()
            sent_any = True
            
    return sent_any
