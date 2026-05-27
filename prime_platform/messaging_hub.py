"""Unified messaging hub — 26+ channel registry and routing."""
from __future__ import annotations

# Channel id → display name → desktop app name for automation fallback
CHANNELS: list[dict] = [
    {"id": "whatsapp", "name": "WhatsApp", "app": "WhatsApp"},
    {"id": "telegram", "name": "Telegram", "app": "Telegram"},
    {"id": "discord", "name": "Discord", "app": "Discord"},
    {"id": "signal", "name": "Signal", "app": "Signal"},
    {"id": "instagram", "name": "Instagram", "app": "Instagram"},
    {"id": "messenger", "name": "Messenger", "app": "Messenger"},
    {"id": "slack", "name": "Slack", "app": "Slack"},
    {"id": "teams", "name": "Microsoft Teams", "app": "Teams"},
    {"id": "matrix", "name": "Element (Matrix)", "app": "Element"},
    {"id": "google_chat", "name": "Google Chat", "app": "Google Chat"},
    {"id": "line", "name": "LINE", "app": "LINE"},
    {"id": "viber", "name": "Viber", "app": "Viber"},
    {"id": "wechat", "name": "WeChat", "app": "WeChat"},
    {"id": "snapchat", "name": "Snapchat", "app": "Snapchat"},
    {"id": "linkedin", "name": "LinkedIn", "app": "LinkedIn"},
    {"id": "twitter", "name": "X (Twitter)", "app": "X"},
    {"id": "bluesky", "name": "Bluesky", "app": "Bluesky"},
    {"id": "mastodon", "name": "Mastodon", "app": "Mastodon"},
    {"id": "reddit", "name": "Reddit", "app": "Reddit"},
    {"id": "zoom", "name": "Zoom", "app": "Zoom"},
    {"id": "skype", "name": "Skype", "app": "Skype"},
    {"id": "imessage", "name": "iMessage", "app": "Messages"},
    {"id": "email", "name": "Email", "app": "Outlook"},
    {"id": "sms", "name": "SMS / Phone Link", "app": "Phone Link"},
    {"id": "google_messages", "name": "Google Messages", "app": "Google Messages"},
    {"id": "threema", "name": "Threema", "app": "Threema"},
    {"id": "wire", "name": "Wire", "app": "Wire"},
]

_ALIASES: dict[str, str] = {}
for ch in CHANNELS:
    _ALIASES[ch["id"]] = ch["id"]
    _ALIASES[ch["name"].lower()] = ch["id"]
    _ALIASES[ch["app"].lower()] = ch["id"]
_ALIASES.update({
    "wp": "whatsapp", "tg": "telegram", "fb": "messenger",
    "ms teams": "teams", "x": "twitter", "gchat": "google_chat",
})


def list_channels() -> str:
    lines = [f"═══ IP PRIME MESSAGING HUB — {len(CHANNELS)} channels ═══", ""]
    for i, ch in enumerate(CHANNELS, 1):
        lines.append(f"  {i:2}. {ch['name']} ({ch['id']})")
    lines.extend([
        "",
        "Use prime_messaging with channel id, receiver, and message.",
        "WhatsApp uses web API; others use desktop automation where available.",
    ])
    return "\n".join(lines)


def resolve_channel(channel: str) -> dict | None:
    key = (channel or "").strip().lower()
    cid = _ALIASES.get(key)
    if not cid:
        for ch in CHANNELS:
            if key in ch["id"] or key in ch["name"].lower():
                return ch
        return None
    return next((c for c in CHANNELS if c["id"] == cid), None)


def send_via_channel(channel: str, receiver: str, message: str, player=None) -> str:
    from actions.send_message import send_message

    ch = resolve_channel(channel)
    if not ch:
        return f"Unknown channel '{channel}'. Say 'list channels' via prime_messaging."

    platform = ch["name"] if ch["id"] != "whatsapp" else "WhatsApp"
    return send_message(
        parameters={
            "receiver": receiver,
            "message_text": message,
            "platform": platform,
        },
        player=player,
    )
