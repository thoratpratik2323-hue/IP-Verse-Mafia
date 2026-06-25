import logging
import psutil
import json
import threading
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_PATH = BASE_DIR / "config" / "settings.json"

COMMON_GAME_PROCESSES = {
    "gta5.exe", "cyberpunk2077.exe", "minecraft.exe", "javaw.exe", "valorant.exe", 
    "csgo.exe", "cs2.exe", "fortniteclient-win64-shipping.exe", "fifa.exe", 
    "overwatch.exe", "r5apex.exe", "eldenring.exe", "witcher3.exe", "leagueoflegends.exe", 
    "dota2.exe", "genshinimpact.exe", "starrail.exe", "steam_app"
}

_monitor_thread = None
_stop_monitor = threading.Event()

def is_game_running() -> tuple[bool, str | None]:
    """Scans running processes to detect if a game is active."""
    try:
        for proc in psutil.process_iter(['name']):
            name = proc.info['name']
            if name and name.lower() in COMMON_GAME_PROCESSES:
                return True, name
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return False, None

def _run_monitoring_loop(player):
    last_status = False
    while not _stop_monitor.is_set():
        running, game_name = is_game_running()
        if running != last_status:
            last_status = running
            # Update settings
            try:
                settings = {}
                if SETTINGS_PATH.exists():
                    try:
                        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                            settings = json.load(f)
                    except Exception as _exc:  # noqa: BLE001
                        logging.debug("[%s] Suppressed: %s", __name__, _exc)
                
                settings["game_mode_active"] = running
                if running:
                    settings["active_game"] = game_name
                else:
                    settings.pop("active_game", None)
                    
                with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=4)
                    
                if running and player:
                    # Minimize UI window to save resources and avoid covering the game
                    player._win.showMinimized()
                    player.write_log(f"SYS: Game detected ({game_name}). Game Mode Enabled.")
                elif player:
                    player.write_log("SYS: Game closed. Normal mode restored.")
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
        time.sleep(10)

def game_mode(parameters: dict, player=None) -> str:
    global _monitor_thread
    action = parameters.get("action", "check").lower().strip()
    
    if action == "start":
        if _monitor_thread and _monitor_thread.is_alive():
            return "Game Mode process monitor is already running, sir."
            
        _stop_monitor.clear()
        _monitor_thread = threading.Thread(
            target=_run_monitoring_loop, 
            args=(player,), 
            daemon=True,
            name="GameModeMonitor"
        )
        _monitor_thread.start()
        return "Game Mode process monitor started. Saturday will now auto-detect active games, sir."
        
    elif action == "stop":
        _stop_monitor.set()
        # Clear game mode state
        try:
            settings = {}
            if SETTINGS_PATH.exists():
                with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                    settings = json.load(f)
            settings["game_mode_active"] = False
            settings.pop("active_game", None)
            with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=4)
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
        return "Game Mode process monitor stopped, sir."
        
    elif action == "status" or action == "check":
        running, game_name = is_game_running()
        if running:
            return f"Game Mode is ACTIVE. Detected running game: {game_name}, sir."
        else:
            return "Game Mode is INACTIVE. No games detected, sir."
            
    else:
        return "Unknown game mode action, sir."
