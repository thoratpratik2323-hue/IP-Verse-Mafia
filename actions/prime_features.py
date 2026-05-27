"""Voice-tool entry points for IP Prime JARVIS-inspired platform features."""
from __future__ import annotations


def prime_local_first(parameters: dict, player=None) -> str:
    from prime_platform.local_first import get_local_status, set_local_first

    action = (parameters or {}).get("action", "status").lower()
    if action == "enable":
        return set_local_first(enabled=True)
    if action == "disable":
        return set_local_first(enabled=False)
    if action == "configure":
        return set_local_first(
            ollama_url=parameters.get("ollama_url"),
            model=parameters.get("model"),
        )
    return get_local_status()


def prime_infinite_memory(parameters: dict, player=None) -> str:
    from prime_platform.infinite_memory import (
        recall_memory,
        recall_by_date,
        store_knowledge,
        store_dated_note,
        list_archive_dates,
        get_memory_stats,
    )

    action = (parameters or {}).get("action", "recall").lower()
    if action == "store":
        date = (parameters.get("date") or "").strip()
        content = parameters.get("content", "")
        topic = parameters.get("topic", "")
        if date:
            return store_dated_note(date, content, topic=topic)
        return store_knowledge(
            topic=topic,
            content=content,
            tags=parameters.get("tags"),
        )
    if action in ("recall_by_date", "by_date", "date"):
        return recall_by_date(
            date=parameters.get("date", ""),
            query=parameters.get("query", ""),
            limit=int(parameters.get("limit", 30)),
        )
    if action in ("timeline", "calendar", "dates"):
        days = list_archive_dates(int(parameters.get("limit", 30)))
        if not days:
            return "No conversation days archived yet."
        return "Days with saved conversations:\n  • " + "\n  • ".join(days)
    if action == "stats":
        s = get_memory_stats()
        return (
            f"Infinite memory: {s['kb_entries']} KB entries, "
            f"{s['archive_turns']} archived turns across {s['archive_days']} days."
        )
    return recall_memory(
        query=parameters.get("query", ""),
        limit=int(parameters.get("limit", 12)),
        date=parameters.get("date", ""),
    )


def prime_energy_dashboard(parameters: dict, player=None) -> str:
    from prime_platform.energy_metrics import get_energy_dashboard

    return get_energy_dashboard()


def prime_messaging(parameters: dict, player=None) -> str:
    from prime_platform.messaging_hub import list_channels, send_via_channel

    action = (parameters or {}).get("action", "send").lower()
    if action in ("list", "channels"):
        return list_channels()
    return send_via_channel(
        channel=parameters.get("channel", "whatsapp"),
        receiver=parameters.get("receiver", ""),
        message=parameters.get("message", parameters.get("message_text", "")),
        player=player,
    )


def prime_homelab(parameters: dict, player=None) -> str:
    from prime_platform.homelab import (
        docker_status,
        list_containers,
        container_action,
        compose_action,
    )

    action = (parameters or {}).get("action", "status").lower()
    if action == "status":
        return docker_status()
    if action in ("list", "ps"):
        return list_containers(all_containers=bool(parameters.get("all")))
    if action == "compose":
        return compose_action(
            parameters.get("compose_action", "ps"),
            parameters.get("project_path", ""),
        )
    return container_action(
        action=action,
        name=parameters.get("container", parameters.get("name", "")),
    )


def prime_media(parameters: dict, player=None) -> str:
    from prime_platform.media_hub import discover_media, torrent_action

    action = (parameters or {}).get("action", "discover").lower()
    if action == "torrent":
        return torrent_action(
            parameters.get("torrent_action", "status"),
            parameters.get("magnet", parameters.get("magnet_or_name", "")),
        )
    return discover_media(
        query=parameters.get("query", ""),
        media_type=parameters.get("media_type", "any"),
    )


def prime_writing_tool(parameters: dict, player=None) -> str:
    from prime_platform.writing_suite import prime_writing

    return prime_writing(
        action=parameters.get("action", "summarize"),
        text=parameters.get("text", ""),
        target_language=parameters.get("target_language", "English"),
        style=parameters.get("style", "clear"),
        topic=parameters.get("topic", ""),
    )


def prime_gesture_control(parameters: dict, player=None) -> str:
    from prime_platform.gesture_control import gesture_control, configure_gesture

    action = (parameters or {}).get("action", "status").lower()
    if action == "configure":
        return configure_gesture(
            use_mediapipe=parameters.get("use_mediapipe"),
            cooldown_sec=parameters.get("cooldown_sec"),
            camera_index=parameters.get("camera_index"),
        )
    cam = parameters.get("camera_index")
    return gesture_control(action=action, player=player, camera_index=cam)


def prime_dashboard(parameters: dict, player=None) -> str:
    from prime_platform.dashboard_server import start_dashboard, stop_dashboard

    action = (parameters or {}).get("action", "start").lower()
    if action in ("stop", "off"):
        return stop_dashboard()
    port = parameters.get("port")
    open_br = parameters.get("open_browser", True)
    if isinstance(open_br, str):
        open_br = open_br.lower() not in ("false", "0", "no")
    return start_dashboard(port=port, open_browser=bool(open_br))
