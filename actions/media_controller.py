"""
media_controller.py — Controls media keys, sound outputs, and desktop players.

This is a standard action module for the IP Prime personal assistant suite.
"""

import sys
import asyncio
import pyautogui

# Try to import winsdk for advanced native Windows Media session manager controls
WINSDK_AVAILABLE = False
try:
    if sys.platform == "win32":
        from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as SessionManager
        from winsdk.windows.media import MediaPlaybackStatus
        WINSDK_AVAILABLE = True
except Exception:
    pass

def _run_async(coro):
    """Helper to run an async coroutine synchronously on a new event loop or using standard asyncio loop."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    except Exception as e:
        print(f"[Media Controller] Async helper exception: {e}")
        return None

async def _get_native_media_info():
    """Extracts media title, artist, and album using native Windows Runtime APIs."""
    if not WINSDK_AVAILABLE:
        return None
        
    try:
        manager = await SessionManager.request_async()
        session = manager.get_current_session()
        if not session:
            return None
            
        props = await session.try_get_media_properties_async()
        info = {
            "title": props.title if props else "Unknown Title",
            "artist": props.artist if props else "Unknown Artist",
            "album": props.album_title if props else "Unknown Album"
        }
        
        # Determine playback status
        info["status"] = "Unknown"
        playback_info = session.get_playback_info()
        if playback_info:
            status = playback_info.playback_status
            if status == MediaPlaybackStatus.PLAYING:
                info["status"] = "Playing"
            elif status == MediaPlaybackStatus.PAUSED:
                info["status"] = "Paused"
            elif status == MediaPlaybackStatus.STOPPED:
                info["status"] = "Stopped"
                
        return info
    except Exception as e:
        print(f"[Media Controller] Native media info extraction failed: {e}")
        return None

async def _send_native_media_command(command: str) -> bool:
    """Sends native media player commands using native Windows Runtime APIs."""
    if not WINSDK_AVAILABLE:
        return False
        
    try:
        manager = await SessionManager.request_async()
        session = manager.get_current_session()
        if not session:
            return False
            
        cmd = command.lower().strip()
        if cmd == "play":
            await session.try_play_async()
        elif cmd == "pause":
            await session.try_pause_async()
        elif cmd == "next":
            await session.try_skip_next_async()
        elif cmd == "prev":
            await session.try_skip_previous_async()
        else:
            return False
        return True
    except Exception as e:
        print(f"[Media Controller] Native command {command} execution failed: {e}")
        return False

def get_now_playing() -> str:
    """Returns a user-friendly string of the currently playing media."""
    if WINSDK_AVAILABLE:
        info = _run_async(_get_native_media_info())
        if info:
            status_symbol = "🟢" if info.get("status") == "Playing" else "⏸️"
            return (
                f"### {status_symbol} Now Playing\n"
                f"- **Title**: {info['title']}\n"
                f"- **Artist**: {info['artist']}\n"
                f"- **Album**: {info['album']}\n"
                f"- **Status**: {info['status']}"
            )
            
    return "### ⏸️ Media Status\nNo active Windows Media session detected or playback is inactive."

def execute_media_control(action: str) -> str:
    """Executes media commands (play, pause, next, prev, volume_up, volume_down)."""
    action_clean = action.lower().strip()
    
    # Try native command first (for play/pause/next/prev)
    native_success = False
    if WINSDK_AVAILABLE and action_clean in ["play", "pause", "next", "prev"]:
        success = _run_async(_send_native_media_command(action_clean))
        if success:
            native_success = True
            
    # Fallback to simulate hardware multimedia keyboard inputs (perfect cross-player compatibility!)
    if not native_success:
        try:
            if action_clean == "play" or action_clean == "pause":
                pyautogui.press("playpause")
            elif action_clean == "next":
                pyautogui.press("nexttrack")
            elif action_clean == "prev":
                pyautogui.press("prevtrack")
            elif action_clean == "volume_up":
                pyautogui.press("volumeup")
            elif action_clean == "volume_down":
                pyautogui.press("volumedown")
            else:
                return f"Error: Unknown media control action '{action}'."
        except Exception as e:
            return f"Failed to execute keyboard media control: {e}"
            
    # Return context-aware response
    if action_clean == "now_playing":
        return get_now_playing()
        
    return f"Successfully executed media control: **{action_clean.upper()}**."
