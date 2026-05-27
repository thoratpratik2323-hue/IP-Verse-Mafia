"""
spotify_helper.py — Integrates Spotify desktop player control and plays mood-based tracks.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import json
import base64
from pathlib import Path
import requests
from actions.media_controller import execute_media_control

BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_spotify_config() -> tuple[str | None, str | None]:
    try:
        if API_KEYS_PATH.exists():
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg.get("spotify_client_id"), cfg.get("spotify_client_secret")
    except Exception:
        pass
    return None, None

def get_spotify_access_token() -> str | None:
    """Uses client credentials flow to get a temporary access token for searching Spotify's catalog."""
    client_id, client_secret = _get_spotify_config()
    if not client_id or not client_secret:
        return None
        
    try:
        auth_str = f"{client_id}:{client_secret}"
        b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")
        
        headers = {
            "Authorization": f"Basic {b64_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"grant_type": "client_credentials"}
        
        res = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data, timeout=5)
        if res.status_code == 200:
            return res.json().get("access_token")
    except Exception as e:
        print(f"[Spotify] Error getting token: {e}")
    return None

def search_spotify_track(query: str) -> str:
    """Searches Spotify catalog for a track and returns details and links, or falls back to WinRT if no API key is configured."""
    token = get_spotify_access_token()
    if not token:
        # Graceful fallback: tell them about WinRT fallback and execute a standard play/pause command
        return (
            "### [SEARCH] Spotify Web Search\n"
            "[WARNING] Spotify Client ID & Secret are not configured in your settings, so Web Search is inactive.\n\n"
            "*Falling back to native media controller...*\n"
            f"{execute_media_control('now_playing')}"
        )
        
    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {"q": query, "type": "track", "limit": 3}
        
        res = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params, timeout=5)
        if res.status_code != 200:
            return f"Spotify Search API returned error code: {res.status_code}"
            
        tracks = res.json().get("tracks", {}).get("items", [])
        if not tracks:
            return f"No tracks found on Spotify for query: '{query}'"
            
        output = [f"### [SEARCH] Spotify Web Search Results for: '{query}'\n"]
        for idx, track in enumerate(tracks, 1):
            name = track["name"]
            artists = ", ".join([artist["name"] for artist in track["artists"]])
            album = track["album"]["name"]
            link = track["external_urls"].get("spotify", "")
            duration_ms = track["duration_ms"]
            duration_min = f"{int(duration_ms / 60000)}:{int((duration_ms % 60000)/1000):02d}"
            
            output.append(
                f"**{idx}. [{name}]({link})** by *{artists}*\n"
                f"- **Album**: {album}\n"
                f"- **Duration**: {duration_min}\n"
            )
            
        return "\n".join(output)
    except Exception as e:
        return f"Error executing Spotify search: {e}"

def execute_spotify_command(action: str, query: str = "") -> str:
    """Routes a music/spotify request. Controls native playback if action is a command, queries Web API, or activates DJ Mode."""
    action_clean = action.lower().strip()
    
    if action_clean == "search" and query:
        return search_spotify_track(query)
    elif action_clean == "dj_mode":
        mood_param = query if query else "auto"
        return spotify_dj_mode(mood=mood_param)
        
    # Route playback actions to Windows Native WinRT Media Controller
    return execute_media_control(action_clean)

def get_mood_based_playlist_query(mood: str) -> str:
    """Maps a user's emotional state to a curated Spotify search query."""
    m = mood.lower().strip()
    mapping = {
        "happy": "happy upbeat hits 2024",
        "sad": "sad melancholy indie",
        "stressed": "lo-fi study beats calm",
        "focused": "deep focus instrumental coding",
        "tired": "energetic morning workout",
        "excited": "party hype anthems",
        "neutral": "chill vibes playlist"
    }
    return mapping.get(m, "top hits 2024")

def spotify_dj_mode(mood: str = "auto", player=None) -> str:
    """Intelligent DJ Mode: Captures user's webcam mood or uses parameter, and queues the optimal playlist."""
    detected_mood = "focused" # default
    source = "default profile"
    
    if mood == "auto":
        # First try to read the most recent logged mood from history
        try:
            from actions.webcam_mood import MOOD_HISTORY_FILE
            if MOOD_HISTORY_FILE.exists():
                with open(MOOD_HISTORY_FILE, "r", encoding="utf-8") as f:
                    history_data = json.load(f)
                    history = history_data.get("history", [])
                    if history:
                        detected_mood = history[-1].get("mood", "focused")
                        source = "latest camera telemetry"
        except Exception:
            pass
    else:
        detected_mood = mood
        source = "voice instruction"
        
    playlist_query = get_mood_based_playlist_query(detected_mood)
    
    # Search for matching songs to present
    search_results = search_spotify_track(playlist_query)
    
    # Launch local Spotify desktop application
    spotify_started = False
    try:
        # Launching via Windows URI protocol 'spotify:' is robust and fast
        os.system("start spotify:")
        spotify_started = True
    except Exception as e:
        print(f"[SpotifyDJ] Error starting Spotify app: {e}")
        
    status_suffix = "\n*(Launched Spotify desktop app to start playing, sir)*" if spotify_started else ""
    
    return (
        f"### [DJ] Spotify AI DJ Mode Active\n"
        f"Pratik Sir, I detected your mood is **{detected_mood.upper()}** (via {source}).\n"
        f"Mapping this to ambient playlist query: *\"{playlist_query}\"*\n\n"
        f"{search_results}{status_suffix}\n\n"
        "Let the beats flow, sir!"
    )

