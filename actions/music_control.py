import pyautogui
import webbrowser
from typing import Any

def music_control(parameters: dict[str, Any], player=None) -> str:
    """Controls media playback and opens music streams for focus or hacking vibes."""
    action = parameters.get("action", "play_pause").lower().strip()
    vibe = parameters.get("vibe", "synthwave").lower().strip()

    if action == "play_pause" or action == "toggle":
        try:
            pyautogui.press("playpause")
            return "Toggled media playback, sir."
        except Exception as e:
            return f"Failed to toggle media playback: {e}"

    elif action == "next" or action == "skip":
        try:
            pyautogui.press("nexttrack")
            return "Skipped to the next track, sir."
        except Exception as e:
            return f"Failed to skip track: {e}"

    elif action == "prev" or action == "previous":
        try:
            pyautogui.press("prevtrack")
            return "Playing the previous track, sir."
        except Exception as e:
            return f"Failed to play previous track: {e}"

    elif action == "play_vibe" or action == "play":
        query = parameters.get("query", "").strip()
        if query:
            try:
                from actions.youtube_video import _scrape_first_video_url
                url = _scrape_first_video_url(query)
                if url:
                    webbrowser.open(url)
                    return f"Opening your requested track '{query}' on YouTube, sir!"
                else:
                    from urllib.parse import quote_plus
                    fallback_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                    webbrowser.open(fallback_url)
                    return f"I couldn't find a direct match, but I opened YouTube search for '{query}', sir!"
            except Exception as e:
                from urllib.parse import quote_plus
                fallback_url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
                try:
                    webbrowser.open(fallback_url)
                    return f"Opened YouTube search for '{query}', sir!"
                except Exception as ex:
                    return f"Failed to open music search: {ex}"
        else:
            # Cyberpunk focus playlists
            urls = {
                "synthwave": "https://www.youtube.com/watch?v=4xDzrJKXOOY",  # Synthwave / Retro / Cyberpunk
                "lofi": "https://www.youtube.com/watch?v=jfKfPfyJRdk",       # Lo-Fi Beats
                "cyberpunk": "https://www.youtube.com/watch?v=EtV0T2E_bHE",  # Dark Synthwave / Cyberpunk
            }
            
            url = urls.get(vibe, urls["synthwave"])
                
            try:
                webbrowser.open(url)
                return f"Opening your favorite {vibe} focus vibe stream, sir!"
            except Exception as e:
                return f"Failed to open music stream: {e}"

    else:
        return "Unknown media control action, sir."
