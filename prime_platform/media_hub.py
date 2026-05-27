"""Media discovery and torrent management integration."""
from __future__ import annotations

import subprocess

from prime_platform.config import load_prime_config


def discover_media(query: str, media_type: str = "any") -> str:
    """Search public metadata (no piracy hosting)."""
    query = (query or "").strip()
    if not query:
        return "Provide a search query for media discovery."

    lines = [f"═══ MEDIA DISCOVERY: {query} ═══", ""]

    try:
        from actions.youtube_video import youtube_video
        yt = youtube_video(parameters={"action": "play", "query": query}, player=None)
        lines.append(f"YouTube: {yt[:400]}")
    except Exception as e:
        lines.append(f"YouTube: unavailable ({e})")

    try:
        from actions.spotify_helper import search_spotify_track
        sp = search_spotify_track(query=query)
        lines.append(f"Spotify: {sp[:400]}")
    except Exception as e:
        lines.append(f"Spotify: unavailable ({e})")

    lines.extend([
        "",
        "For library servers (Plex/Jellyfin), open your server URL in browser_control.",
        "Torrent actions require a magnet link you already have the rights to use.",
    ])
    return "\n".join(lines)


def _find_torrent_cli() -> str | None:
    cfg = load_prime_config()
    pref = cfg.get("media", {}).get("torrent_client", "auto")
    candidates = []
    if pref and pref != "auto":
        candidates.append(pref)
    candidates.extend(["transmission-cli", "transmission-remote", "aria2c"])
    import shutil
    for c in candidates:
        if shutil.which(c):
            return c
    return None


def torrent_action(action: str, magnet_or_name: str = "") -> str:
    action = (action or "").strip().lower()
    magnet = (magnet_or_name or "").strip()

    if action == "status":
        cli = _find_torrent_cli()
        if not cli:
            return "No torrent client CLI found. Install transmission-cli or aria2."
        if "aria2" in cli:
            return "aria2c: use 'aria2c -S' in terminal for session list (configure RPC for full HUD)."
        try:
            r = subprocess.run(
                [cli, "-l"],
                capture_output=True, text=True, timeout=15,
            )
            return (r.stdout or r.stderr or "No output").strip() or "Torrent list empty."
        except Exception as e:
            return f"torrent status failed: {e}"

    if action == "add":
        if not magnet or not magnet.startswith("magnet:"):
            return "Provide a valid magnet: URI for torrent add (legal content only)."
        cli = _find_torrent_cli()
        if not cli:
            return "No torrent client CLI found. Install transmission-cli or aria2c."
        try:
            if "aria2" in cli:
                r = subprocess.run(
                    [cli, magnet],
                    capture_output=True, text=True, timeout=30,
                )
            else:
                r = subprocess.run(
                    [cli, "-a", magnet],
                    capture_output=True, text=True, timeout=30,
                )
            if r.returncode == 0:
                return f"Added torrent via {cli}."
            return f"Add failed: {(r.stderr or r.stdout or '').strip()}"
        except Exception as e:
            return f"torrent add failed: {e}"

    return (
        "torrent actions: status | add\n"
        "  add — requires magnet: link\n"
        "  status — list active downloads"
    )
