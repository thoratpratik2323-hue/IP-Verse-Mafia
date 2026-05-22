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
            "### 🎵 Spotify Web Search\n"
            "⚠️ Spotify Client ID & Secret are not configured in your settings, so Web Search is inactive.\n\n"
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
            
        output = [f"### 🎧 Spotify Web Search Results for: '{query}'\n"]
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
    """Routes a music/spotify request. Controls native playback if action is a command, or queries Web API if search is requested."""
    action_clean = action.lower().strip()
    
    if action_clean == "search" and query:
        return search_spotify_track(query)
        
    # Route playback actions to Windows Native WinRT Media Controller
    return execute_media_control(action_clean)
