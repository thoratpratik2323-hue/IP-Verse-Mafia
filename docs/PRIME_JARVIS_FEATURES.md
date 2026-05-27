# IP Prime — JARVIS-Inspired Features

Open JARVIS–style capabilities integrated into IP Prime (voice tools + on-device data).

## 1. Local-first framework

- **Config:** `config/prime_features.json` → `local_first`
- **Tool:** `prime_local_first` — status, enable, disable, configure Ollama
- **On-device:** memory archive, LanceDB index, file tools, Docker (local)
- **Voice:** still uses Gemini Live; enable local-first to route `prime_writing` through Ollama

```text
"Prime, local first status dikhao"
"Prime, local first enable karo"
```

## 2. Infinite memory

- **Archive:** `memory/archive/YYYY-MM-DD.jsonl` (every conversation turn)
- **Knowledge base:** `memory/knowledge_base.json`
- **Tool:** `prime_infinite_memory` — recall, store, stats
- Auto-archives on each session turn via `memory_manager`

```text
"Prime, yaad hai humne kal kya discuss kiya?"  → prime_infinite_memory recall
"Prime, remember my server IP is 192.168.1.10" → store + save_memory
```

## 3. Energy & cost dashboard

- **Log:** `memory/usage_metrics.json`
- **Tool:** `prime_energy_dashboard`
- **UI:** footer shows API $ today, est. watts, CPU %
- Tracks estimated tokens/cost per tool call

## 4. Tauri cross-platform desktop (roadmap)

- **Primary UI today:** Python + PyQt6 (`ui_core.py`)
- **Future / optional:** `desktop-tauri/` — Tauri 2 shell talking to IP Prime HTTP API
- See `desktop-tauri/README.md` to scaffold macOS, Linux, Windows builds

## 5. Messaging hub (27 channels)

WhatsApp, Telegram, Discord, Signal, Instagram, Messenger, Slack, Teams, Matrix, Google Chat, LINE, Viber, WeChat, Snapchat, LinkedIn, X, Bluesky, Mastodon, Reddit, Zoom, Skype, iMessage, Email, SMS, Google Messages, Threema, Wire.

- **Tool:** `prime_messaging` — `list` or `send`
- Uses existing `send_message` desktop automation / WhatsApp Web

## 6. Homelab / Docker

- **Tool:** `prime_homelab` — status, list, start, stop, restart, logs, stats, compose
- Requires Docker CLI on PATH

## 7. Media & torrents

- **Tool:** `prime_media` — discover (YouTube + Spotify), torrent status/add
- Torrent add requires a **legal** `magnet:` link you provide

## 8. Writing suite (enhanced)

- **Tool:** `prime_writing` — summarize, translate, write, rewrite, proofread, expand, bullets, email, tone
- Cloud: Gemini Flash | Local: Ollama when local-first is enabled

## 9. Gesture control (Jarvis-GUI style)

- **Tool:** `prime_gesture_control` — start | stop | status | configure
- **UI:** Settings → PRIME VERSE → START GESTURE CONTROL
- **Gestures:** open palm = wake, fist = mute, point = listen, swipe L/R = volume, pinch = click
- **Optional:** `pip install mediapipe` for accurate hand tracking (else motion fallback)

## 10. Advanced monitoring dashboard

- **Tool:** `prime_dashboard` — opens browser HUD at `http://127.0.0.1:18765/`
- **API sidecar:** `python prime_api.py` (for Tauri / external apps)
- **UI:** Settings → PRIME VERSE → OPEN MONITOR DASHBOARD
- Shows: API cost, power estimate, infinite memory stats, Ollama status, Docker

## Settings panel — PRIME VERSE

Gear icon → scroll to **PRIME VERSE**:
- Local-first toggle
- Monitor dashboard button
- Gesture control button
- Memory stats line

---

## Quick voice examples

| Say | Tool |
|-----|------|
| Prime, energy dashboard | prime_energy_dashboard |
| Prime, list messaging channels | prime_messaging list |
| Prime, docker containers | prime_homelab list |
| Prime, translate this to Hindi: … | prime_writing translate |
| Prime, homelab status | prime_homelab status |
| Prime, start gesture control | prime_gesture_control start |
| Prime, open monitoring dashboard | prime_dashboard |
| Prime, expand this text | prime_writing expand |
