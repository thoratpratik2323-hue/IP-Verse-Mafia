import asyncio
import re
import threading
import json
import sys
import traceback
import warnings

warnings.filterwarnings("ignore", category=FutureWarning, module="google")

from pathlib import Path
import time
import numpy as np

# Force console streams to use UTF-8 to prevent charmap Unicode crashes on Windows
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

import sounddevice as sd
from google import genai
from google.genai import types
from ui import IPRayUI
from memory.memory_manager import (
    load_memory, update_memory, format_memory_for_prompt,
    append_session_turn, format_session_for_prompt,
    save_shutdown_summary, format_last_session_for_prompt,
)

from actions.file_processor import file_processor
from actions.flight_finder     import flight_finder
from actions.open_app          import open_app
from actions.weather_report    import weather_action
from actions.send_message      import send_message
from actions.reminder          import reminder
from actions.computer_settings import computer_settings
from actions.screen_processor  import screen_process
from actions.youtube_video     import youtube_video
from actions.desktop           import desktop_control
from actions.browser_control   import browser_control
from actions.file_controller   import file_controller
from actions.code_helper       import code_helper
from actions.web_hud           import web_hud
from actions.dev_agent         import dev_agent
from actions.web_search        import web_search as web_search_action
from actions.design_extractor  import design_extractor as design_extractor_action
from actions.computer_control  import computer_control
from actions.game_updater      import game_updater
from actions.screen_processor  import screen_clicker, screen_explainer, clipboard_action
from actions.dev_agent         import dev_bootstrap, git_assistant, refactor_code, focus_mode
from actions.premium_utilities import (
    meeting_notetaker, browser_news_reader, morning_briefing,
    expense_logger, wifi_file_share, notification_dispatcher,
    drag_drop_converter, spotify_ambient_dj, smart_light_control,
    voice_alarm_suite
)
from actions.warp_helper import warp_helper
from actions import ghost_coder
from actions import smart_drop_zone

# Premium Actions Suite 2026
from actions.task_planner import task_planner
from actions.morning_briefer import morning_briefer
from actions.screenshot_code_gen import screenshot_code_gen
from actions.live_code_reviewer import live_code_reviewer
from actions.webcam_mood import webcam_mood
from actions.email_summarizer import email_summarizer
from actions.mobile_telekinesis import mobile_telekinesis
from actions.smart_home import smart_home_enhanced
from actions.anus_cli_helper import anus_cli_helper
from actions.soap2soap_helper import soap2soap_remaker
from actions.file_explorer import file_explorer
from actions.hermes_agent import hermes_agent
from actions.code_companion import code_companion
from actions.git_terminal_companion import git_terminal_companion
from actions.project_debug_companion import project_debug_companion
from actions.multimodal_perception import multimodal_perception
from actions.autonomous_autopilot import autonomous_autopilot
from actions.advanced_communicator import advanced_communicator
from actions.token_juice import token_juice




def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LIVE_MODEL          = "models/gemini-2.5-flash-native-audio-preview-12-2025"
CHANNELS            = 1
SEND_SAMPLE_RATE    = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE          = 1024   # smaller = lower mic→API latency (~64ms @ 16kHz)
PLAY_BUFFER_SAMPLES = 1024   # smaller = voice starts sooner (~43ms @ 24kHz)
VOICE_OUTPUT_GAIN   = 3.0
LOW_LATENCY_PLAYBACK = True  # stream TTS chunks immediately (overridden by config)

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    import json
    import re
    
    # 1. Load base prompt
    base_prompt = ""
    try:
        base_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        base_prompt = (
            "You are IP Prime, an advanced personal AI assistant. Your owner is Pratik Thorat. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

    # 2. Load personality configurations
    personality_path = BASE_DIR / "config" / "personality.json"
    name = "IP Prime"
    humour = 50
    energy = 60
    sarcasm = 30
    prof = 80
    creat = 75

    if personality_path.exists():
        try:
            p_data = json.loads(personality_path.read_text(encoding="utf-8"))
            name = p_data.get("name", "IP Prime")
            humour = p_data.get("humour", 50)
            energy = p_data.get("energy", 60)
            sarcasm = p_data.get("sarcasm", 30)
            prof = p_data.get("professionalism", 80)
            creat = p_data.get("creativity", 75)
        except Exception:
            pass

    # 3. Replace all occurrences of "IP Prime" with custom name
    base_prompt = re.sub(r"\bIP\s+Prime\b", name, base_prompt, flags=re.IGNORECASE)

    # 4. Synthesize traits directive block
    directives = []
    directives.append(f"Your custom synthesised core name is: {name}.")
    directives.append(
        "SPEECH STYLE (MANDATORY): Never say 'ahem', 'ahem ahem', throat-clearing, or dramatic "
        "opening fillers. Start replies directly. No theatrical intros, no 'galaxy-class' hype unless asked."
    )

    # Humour directive
    if humour > 70:
        directives.append("Humour Level (HIGH): Aapke paas exceptional sense of humour hai. Be witty, share subtle jokes, and use light-hearted puns where appropriate. Don't be dry.")
    elif humour < 30:
        directives.append("Humour Level (LOW): Aapka tone strictly serious aur literal hona chahiye. No jokes, no puns, maintain absolute literal focus.")
    else:
        directives.append(f"Humour Level (MODERATE: {humour}%): Balance humor naturally, keeping responses pleasant but focused.")

    # Energy directive
    if energy > 70:
        directives.append(
            "Energy Level (HIGH): Enthusiastic and helpful, but still direct — no filler words, no 'ahem', no theatrical intros."
        )
    elif energy < 30:
        directives.append("Energy Level (LOW): Aap soft-spoken, calm, composed aur understated hain. Maintain a low-energy, serene, stoic demeanor.")
    else:
        directives.append(f"Energy Level (MODERATE: {energy}%): Maintain a steady, helpful, and pleasant tone.")

    # Sarcasm directive
    if sarcasm > 70:
        directives.append("Sarcasm Level (HIGH): Aap exceptionally sarcastic aur cheeky hain! Deliver clever, playful, and sharp responses, but keep it friendly and non-offensive. Use dry wit.")
    elif sarcasm < 20:
        directives.append("Sarcasm Level (LOW): Aap clean, straight-forward, and completely transparent hain. No sarcasm, no double-meanings, no irony.")
    else:
        directives.append(f"Sarcasm Level (MODERATE: {sarcasm}%): Occasional dry wit or playful teasing is fine, but stay helpful.")

    # Professionalism directive
    if prof > 80:
        directives.append("Professionalism Level (HIGH): Aap ultra-professional, structured, refined, and highly respectful hain. Treat the user with utmost executive deference.")
    elif prof < 40:
        directives.append("Professionalism Level (LOW): Aap formal styles avoid karein. Be casual, friendly, and speak like a peer/buddy to the user. No corporate-speak.")
    else:
        directives.append(f"Professionalism Level (MODERATE: {prof}%): Polite, supportive, and balanced.")

    # Creativity directive
    if creat > 80:
        directives.append("Creativity Level (HIGH): Aap immensely creative, lateral-thinking, out-of-the-box thinker hain. Offer unique perspectives, poetic/clever solutions, and highly imaginative brainstorming.")
    elif creat < 30:
        directives.append("Creativity Level (LOW): Aap strictly logical, methodical, direct, and factual. Focus only on the most linear, simple, and proven path.")
    else:
        directives.append(f"Creativity Level (MODERATE: {creat}%): Balanced between creative suggestions and practical execution.")

    directives_block = "\n".join(directives)

    # 5. Compile final prompt
    final_prompt = (
        f"==================================================\n"
        f"🧬 [DYNAMIC PERSONALITY CORE ACTIVE]\n"
        f"{directives_block}\n"
        f"==================================================\n\n"
        f"{base_prompt}"
    )
    return final_prompt

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)


def _clean_transcript(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    text = re.sub(r"\b(ahem[\s,]*)+", "", text, flags=re.IGNORECASE)
    return text.strip()


TOOL_DECLARATIONS = [
    {
        "name": "anus_cli_helper",
        "description": (
            "Runs autonomous shell execution loops to achieve terminal goals or "
            "simulates Solana Web3 wallet telemetry operations (balance check, token transfers, history)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "autonomous_run | solana_balance | solana_transfer | solana_history"
                },
                "goal": {
                    "type": "STRING",
                    "description": "The command-line objective to achieve autonomously (required for autonomous_run)"
                },
                "max_steps": {
                    "type": "INTEGER",
                    "description": "Max steps for autonomous loop, default is 5"
                },
                "target": {
                    "type": "STRING",
                    "description": "Recipient Solana wallet public key (required for solana_transfer)"
                },
                "amount": {
                    "type": "NUMBER",
                    "description": "Solana token count to transfer (required for solana_transfer)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "open_app",
        "description": (
            "Opens any application on the computer. "
            "Use this whenever the user asks to open, launch, or start any app, "
            "website, or program. Always call this tool — never just say you opened it."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application (e.g. 'WhatsApp', 'Chrome', 'Spotify')"
                }
            },
            "required": ["app_name"]
        }
    },
    {
        "name": "web_search",
        "description": "Searches the web for any information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query":  {"type": "STRING", "description": "Search query"},
                "mode":   {"type": "STRING", "description": "search (default) or compare"},
                "items":  {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Items to compare"},
                "aspect": {"type": "STRING", "description": "price | specs | reviews"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "design_extractor",
        "description": "Extracts design systems, components, and packaged AI-readable .skill files from live web URLs, local project directories, or git repositories.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "source_type": {"type": "STRING", "description": "Type of target: 'url' (live website), 'dir' (local project directory), or 'repo' (git repository link)"},
                "target": {"type": "STRING", "description": "The URL, directory path, or git repository link to analyze"},
                "mode": {"type": "STRING", "description": "Extraction mode: 'default' or 'ultra' (crawls up to 5 pages for deeper extraction, default is 'default')"},
                "name": {"type": "STRING", "description": "Optional name override for the extracted project"}
            },
            "required": ["source_type", "target"]
        }
    },
    {
        "name": "weather_report",
        "description": "Gives the weather report to user",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING", "description": "City name"}
            },
            "required": ["city"]
        }
    },
    {
        "name": "send_message",
        "description": "Sends a text message via WhatsApp, Telegram, or other messaging platform.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "receiver":     {"type": "STRING", "description": "Recipient contact name"},
                "message_text": {"type": "STRING", "description": "The message to send"},
                "platform":     {"type": "STRING", "description": "Platform: WhatsApp, Telegram, etc."}
            },
            "required": ["receiver", "message_text", "platform"]
        }
    },
    {
        "name": "reminder",
        "description": "Sets a timed reminder using Task Scheduler.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "date":    {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "time":    {"type": "STRING", "description": "Time in HH:MM format (24h)"},
                "message": {"type": "STRING", "description": "Reminder message text"}
            },
            "required": ["date", "time", "message"]
        }
    },
    {
        "name": "youtube_video",
        "description": (
            "Controls YouTube. Use for: playing videos, summarizing a video's content, "
            "getting video info, or showing trending videos."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "play | summarize | get_info | trending (default: play)"},
                "query":  {"type": "STRING", "description": "Search query for play action"},
                "save":   {"type": "BOOLEAN", "description": "Save summary to Notepad (summarize only)"},
                "region": {"type": "STRING", "description": "Country code for trending e.g. TR, US"},
                "url":    {"type": "STRING", "description": "Video URL for get_info action"},
            },
            "required": []
        }
    },
    {
        "name": "screen_process",
        "description": (
            "Captures and analyzes the screen or webcam image. "
            "MUST be called when user asks what is on screen, what you see, "
            "analyze my screen, look at camera, etc. "
            "You have NO visual ability without this tool. "
            "After calling this tool, stay SILENT — the vision module speaks directly."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "angle": {"type": "STRING", "description": "'screen' to capture display, 'camera' for webcam. Default: 'screen'"},
                "text":  {"type": "STRING", "description": "The question or instruction about the captured image"}
            },
            "required": ["text"]
        }
    },
    {
        "name": "computer_settings",
        "description": (
            "Controls the computer: volume, brightness, window management, keyboard shortcuts, "
            "typing text, clipboard utilities, note-taking/scratchpad, WiFi, power. "
            "Supported actions:\n"
            "- list_windows: lists all active, visible window titles.\n"
            "- focus_window: activates window matching query (query in 'value').\n"
            "- resize_window: resizes matching window ('value' format: 'title,width,height').\n"
            "- move_window: moves matching window ('value' format: 'title,x,y').\n"
            "- minimize_window_by_title / maximize_window_by_title / close_window_by_title: ('value' is window title).\n"
            "- get_clipboard: returns text from system clipboard.\n"
            "- set_clipboard: copies text (in 'value') to clipboard.\n"
            "- type_clipboard: pastes clipboard content using keystrokes.\n"
            "- add_note: appends a quick note ('value' is note text).\n"
            "- read_notes: returns all saved notes.\n"
            "- clear_notes: clears notes archive.\n"
            "- system_diagnostics: retrieves hardware telemetry (CPU/RAM/GPU load, temps, disk partitions, and top 5 processes).\n"
            "- smart_workspace: launches window layouts (value = 'dev' | 'chill' | 'design').\n"
            "- pc_cleaner: sweeps temporary folders and optimizes RAM.\n"
            "- lock_screen: instantly locks the computer screen securely.\n"
            "- shutdown: power off the system (requires confirmation).\n"
            "- restart: reboot the system (requires confirmation)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "The action to perform (e.g. list_windows, focus_window, get_clipboard, add_note, etc.)"},
                "description": {"type": "STRING", "description": "Natural language description of what to do"},
                "value":       {"type": "STRING", "description": "Value or parameter for the action (e.g. window title, text, note content, or comma-separated values)"},
                "confirmed":   {"type": "STRING", "description": "Set to 'yes' if user confirmed shutdown or restart."}
            },
            "required": []
        }
    },
    {
        "name": "browser_control",
        "description": (
            "Controls any web browser. For simply OPENING Edge/Firefox/Chrome use action=launch with browser=edge|firefox|chrome. "
            "Use go_to/search/click for automation. Always pass browser when user names one. "
            "If automation fails, launch still opens the real installed browser."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "launch (open app) | go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all"},
                "browser":     {"type": "STRING", "description": "Target browser: chrome | edge | firefox | opera | operagx | brave | vivaldi | safari. Omit to use the currently active browser."},
                "url":         {"type": "STRING", "description": "URL for go_to / new_tab action"},
                "query":       {"type": "STRING", "description": "Search query for search action"},
                "engine":      {"type": "STRING", "description": "Search engine: google | bing | duckduckgo | yandex (default: google)"},
                "selector":    {"type": "STRING", "description": "CSS selector for click/type"},
                "text":        {"type": "STRING", "description": "Text to click or type"},
                "description": {"type": "STRING", "description": "Element description for smart_click/smart_type"},
                "direction":   {"type": "STRING", "description": "up | down for scroll"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount in pixels (default: 500)"},
                "key":         {"type": "STRING", "description": "Key name for press action (e.g. Enter, Escape, F5)"},
                "path":        {"type": "STRING", "description": "Save path for screenshot"},
                "incognito":   {"type": "BOOLEAN", "description": "Open in private/incognito mode"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "file_controller",
        "description": "Manages files and folders: list, create, delete, move, copy, rename, read, write, find, disk usage.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "list | create_file | create_folder | delete | move | copy | rename | read | write | find | largest | disk_usage | organize_desktop | info"},
                "path":        {"type": "STRING", "description": "Path or shortcut: ip_given, ip given, desktop, downloads, documents, home"},
                "destination": {"type": "STRING", "description": "Destination path for move/copy"},
                "new_name":    {"type": "STRING", "description": "New name for rename"},
                "content":     {"type": "STRING", "description": "Content for create_file/write"},
                "name":        {"type": "STRING", "description": "File name to search for"},
                "extension":   {"type": "STRING", "description": "File extension to search (e.g. .pdf)"},
                "count":       {"type": "INTEGER", "description": "Number of results for largest"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "desktop_control",
        "description": "Controls the desktop: wallpaper, organize, clean, list, stats.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "wallpaper | wallpaper_url | organize | clean | list | stats | task"},
                "path":   {"type": "STRING", "description": "Image path for wallpaper"},
                "url":    {"type": "STRING", "description": "Image URL for wallpaper_url"},
                "mode":   {"type": "STRING", "description": "by_type or by_date for organize"},
                "task":   {"type": "STRING", "description": "Natural language desktop task"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_helper",
        "description": "Writes, edits, explains, runs, or builds code files. Default save folder: C:\\Users\\thora\\Downloads\\IP Given\\code",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | patch | test | explain | run | build | optimize | screen_debug | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Save path (default: C:\\Users\\thora\\Downloads\\IP Given\\code\\)"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
                "run":         {"type": "BOOLEAN", "description": "For test action: run tests immediately after generating (default: true)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects. Also does cross-file project refactor and project intelligence/explain. Saves under C:\\Users\\thora\\Downloads\\IP Given\\projects by default.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":   {"type": "STRING", "description": "What the project should do, OR 'explain project', OR 'refactor project: <instruction>'"},
                "language":      {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name":  {"type": "STRING", "description": "Optional project folder name"},
                "project_path":  {"type": "STRING", "description": "Absolute path to existing project (for explain/refactor modes)"},
                "timeout":       {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
            },
            "required": ["description"]
        }
    },
    {
        "name": "agent_task",
        "description": (
            "Executes complex multi-step tasks requiring multiple different tools. "
            "Examples: 'research X and save to file', 'find and organize files'. "
            "DO NOT use for single commands. NEVER use for Steam/Epic — use game_updater."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal":     {"type": "STRING", "description": "Complete description of what to accomplish"},
                "priority": {"type": "STRING", "description": "low | normal | high (default: normal)"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "computer_control",
        "description": "Direct computer control: type, click, hotkeys, scroll, move mouse, screenshots, find elements on screen, autonomous screenshot-guided vision loop.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "type | smart_type | click | double_click | right_click | hotkey | press | scroll | move | copy | paste | screenshot | wait | clear_field | focus_window | screen_find | screen_click | random_data | user_data | ui_tars_agent"},
                "text":        {"type": "STRING", "description": "Text to type or paste, or high-level goal for ui_tars_agent"},
                "x":           {"type": "INTEGER", "description": "X coordinate"},
                "y":           {"type": "INTEGER", "description": "Y coordinate"},
                "keys":        {"type": "STRING", "description": "Key combination e.g. 'ctrl+c'"},
                "key":         {"type": "STRING", "description": "Single key e.g. 'enter'"},
                "direction":   {"type": "STRING", "description": "up | down | left | right"},
                "amount":      {"type": "INTEGER", "description": "Scroll amount (default: 3)"},
                "seconds":     {"type": "NUMBER",  "description": "Seconds to wait"},
                "title":       {"type": "STRING",  "description": "Window title for focus_window"},
                "description": {"type": "STRING",  "description": "Element description for screen_find/screen_click"},
                "type":        {"type": "STRING",  "description": "Data type for random_data"},
                "field":       {"type": "STRING",  "description": "Field for user_data: name|email|city"},
                "clear_first": {"type": "BOOLEAN", "description": "Clear field before typing (default: true)"},
                "path":        {"type": "STRING",  "description": "Save path for screenshot"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_updater",
        "description": (
            "THE ONLY tool for ANY Steam or Epic Games request. "
            "Use for: installing, downloading, updating games, listing installed games, "
            "checking download status, scheduling updates. "
            "ALWAYS call directly for any Steam/Epic/game request. "
            "NEVER use agent_task, browser_control, or web_search for Steam/Epic."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING",  "description": "update | install | list | download_status | schedule | cancel_schedule | schedule_status (default: update)"},
                "platform":  {"type": "STRING",  "description": "steam | epic | both (default: both)"},
                "game_name": {"type": "STRING",  "description": "Game name (partial match supported)"},
                "app_id":    {"type": "STRING",  "description": "Steam AppID for install (optional)"},
                "hour":      {"type": "INTEGER", "description": "Hour for scheduled update 0-23 (default: 3)"},
                "minute":    {"type": "INTEGER", "description": "Minute for scheduled update 0-59 (default: 0)"},
                "shutdown_when_done": {"type": "BOOLEAN", "description": "Shut down PC when download finishes"},
            },
            "required": []
        }
    },
    {
        "name": "flight_finder",
        "description": "Searches Google Flights and speaks the best options.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "origin":      {"type": "STRING",  "description": "Departure city or airport code"},
                "destination": {"type": "STRING",  "description": "Arrival city or airport code"},
                "date":        {"type": "STRING",  "description": "Departure date (any format)"},
                "return_date": {"type": "STRING",  "description": "Return date for round trips"},
                "passengers":  {"type": "INTEGER", "description": "Number of passengers (default: 1)"},
                "cabin":       {"type": "STRING",  "description": "economy | premium | business | first"},
                "save":        {"type": "BOOLEAN", "description": "Save results to Notepad"},
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "shutdown_ip_ray",
        "description": (
            "Shuts down the assistant completely. "
            "Call this ONLY when the user says the exact phrase 'go to sleep' in any language. "
            "Do NOT call this for 'good night', 'goodnight', 'shutdown', or other parting phrases."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
    "name": "file_processor",
    "description": (
        "Processes any file that the user has uploaded or dropped onto the interface. "
        "Use this when the user refers to an uploaded file and wants an action on it. "
        "Supports: images (describe/ocr/resize/compress/convert), "
        "PDFs (summarize/extract_text/to_word), "
        "Word docs & text files (summarize/fix/reformat/translate), "
        "CSV/Excel (analyze/stats/filter/sort/convert), "
        "JSON/XML (validate/format/analyze), "
        "code files (explain/review/fix/optimize/run/document/test), "
        "audio (transcribe/trim/convert/info), "
        "video (trim/extract_audio/extract_frame/compress/transcribe/info), "
        "archives (list/extract), "
        "presentations (summarize/extract_text). "
        "ALWAYS call this tool when a file has been uploaded and the user gives a command about it. "
        "If the user's command is ambiguous, pick the most logical action for that file type."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "file_path": {
                "type": "STRING",
                "description": "Full path to the uploaded file. Leave empty to use the currently uploaded file."
            },
            "action": {
                "type": "STRING",
                "description": (
                    "What to do with the file. Examples by type:\n"
                    "image: describe | ocr | resize | compress | convert | info\n"
                    "pdf: summarize | extract_text | to_word | info\n"
                    "docx/txt: summarize | fix | reformat | translate_hint | word_count | to_bullet\n"
                    "csv/excel: analyze | stats | filter | sort | convert | info\n"
                    "json: validate | format | analyze | to_csv\n"
                    "code: explain | review | fix | optimize | run | document | test\n"
                    "audio: transcribe | trim | convert | info\n"
                    "video: trim | extract_audio | extract_frame | compress | transcribe | info | convert\n"
                    "archive: list | extract\n"
                    "pptx: summarize | extract_text | analyze"
                )
            },
            "instruction": {
                "type": "STRING",
                "description": "Free-form instruction if action doesn't cover it. E.g. 'translate this to Turkish', 'find all email addresses'"
            },
            "format": {
                "type": "STRING",
                "description": "Target format for conversion. E.g. 'mp3', 'pdf', 'csv', 'png'"
            },
            "width":     {"type": "INTEGER", "description": "Target width for image resize"},
            "height":    {"type": "INTEGER", "description": "Target height for image resize"},
            "scale":     {"type": "NUMBER",  "description": "Scale factor for image resize (e.g. 0.5)"},
            "quality":   {"type": "INTEGER", "description": "Quality 1-100 for image/video compress"},
            "start":     {"type": "STRING",  "description": "Start time for trim: seconds or HH:MM:SS"},
            "end":       {"type": "STRING",  "description": "End time for trim: seconds or HH:MM:SS"},
            "timestamp": {"type": "STRING",  "description": "Timestamp for video frame extraction HH:MM:SS"},
            "column":    {"type": "STRING",  "description": "Column name for CSV filter/sort"},
            "value":     {"type": "STRING",  "description": "Filter value for CSV filter"},
            "condition": {"type": "STRING",  "description": "Filter condition: equals|contains|gt|lt"},
            "ascending": {"type": "BOOLEAN", "description": "Sort order for CSV sort (default: true)"},
            "save":      {"type": "BOOLEAN", "description": "Save result to file (default: true)"},
            "destination": {"type": "STRING", "description": "Output folder for archive extract"},
        },
        "required": []
    }
},
    {
        "name": "save_memory",
        "description": (
            "Save an important personal fact about the user to long-term memory. "
            "Call this silently whenever the user reveals something worth remembering: "
            "name, age, city, job, preferences, hobbies, relationships, projects, future plans, "
            "or anything they want remembered for a specific day (use key like event_2026_05_24). "
            "Do NOT call for: weather, reminders, searches, or one-time commands. "
            "Do NOT announce that you are saving — just call it silently. "
            "Values must be in English regardless of the conversation language."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "category": {
                    "type": "STRING",
                    "description": (
                        "identity — name, age, birthday, city, job, language, nationality | "
                        "preferences — favorite food/color/music/film/game/sport, hobbies | "
                        "projects — active projects, goals, things being built | "
                        "relationships — friends, family, partner, colleagues | "
                        "wishes — future plans, things to buy, travel dreams | "
                        "notes — habits, schedule, anything else worth remembering"
                    )
                },
                "key":   {"type": "STRING", "description": "Short snake_case key (e.g. name, favorite_food, sister_name)"},
                "value": {"type": "STRING", "description": "Concise value in English (e.g. Fatih, pizza, older sister)"},
            },
            "required": ["category", "key", "value"]
        }
    },
    {
        "name": "screen_clicker",
        "description": "Feature 5: J.A.R.V.I.S. Screen Clicker & Interaction. Locates a described UI element on the screen using AI vision, moves the cursor, and clicks it.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "element_description": {
                    "type": "STRING",
                    "description": "Description of the UI element to locate and click (e.g. 'the green start button', 'the close icon')"
                }
            },
            "required": ["element_description"]
        }
    },
    {
        "name": "screen_explainer",
        "description": "Feature 6: Smart Screen Annotator & Explainer. Captures the screen and uses AI vision to analyze and explain what is visible, suggesting fixes for UI/UX bugs, layout errors, or code.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description": {
                    "type": "STRING",
                    "description": "Query or specific instruction for screen explanation (e.g. 'Why is this button misaligned?', 'Explain this traceback')"
                }
            },
            "required": []
        }
    },
    {
        "name": "clipboard_action",
        "description": "Feature 7: Smart Clipboard Context Manager. Performs actions (summarize, refactor, explain, docstrings, fix_grammar) on the current clipboard text and copies the result back.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action_type": {
                    "type": "STRING",
                    "description": "Type of action to perform: 'summarize', 'refactor', 'explain', 'docstrings', or 'fix_grammar'."
                }
            },
            "required": ["action_type"]
        }
    },
    {
        "name": "dev_bootstrap",
        "description": "Feature 9: One-Command Dev Env Bootstrapper. Automatically opens a project directory in VS Code, detects configuration files, and starts development servers (npm run dev, Django, etc.) in a new command terminal.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "project_path": {
                    "type": "STRING",
                    "description": "Absolute path to the project directory to bootstrap."
                }
            },
            "required": []
        }
    },
    {
        "name": "git_assistant",
        "description": "Feature 10: Autonomous Developer Git Assistant. Inspects uncommitted changes, uses AI to write conventional commit messages, stages changes, and pushes to remote.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action_type": {
                    "type": "STRING",
                    "description": "Action to perform: 'commit', 'push', or 'dry_run' (dry_run only generates the message without executing git commands)"
                },
                "project_path": {
                    "type": "STRING",
                    "description": "Absolute path to the git repository"
                }
            },
            "required": []
        }
    },
    {
        "name": "refactor_code",
        "description": "Feature 11: AI-Powered Code Refactoring & Docstrings. Refactors a source code file using SOLID principles, docstrings, or code simplification.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Absolute path to the code file to refactor"
                },
                "action": {
                    "type": "STRING",
                    "description": "Refactoring action: 'refactor', 'docstrings', or 'simplify'"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "focus_mode",
        "description": "Feature 15: Focus Mode & App Blocker (Pomodoro). Initiates a focus session, playing background binaural theta beats (4Hz) to improve focus.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "duration_minutes": {
                    "type": "INTEGER",
                    "description": "Focus duration in minutes (default is 25)"
                }
            },
            "required": []
        }
    },
    {
        "name": "meeting_notetaker",
        "description": "Feature 8: Smart Meeting Transcriber & Note-Taker. Starts or stops recording meeting notes, generating a structured markdown file of transcript and action items on the Desktop.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action to perform: 'start' or 'stop'"
                },
                "duration_seconds": {
                    "type": "INTEGER",
                    "description": "Simulated duration of the meeting to record"
                }
            },
            "required": []
        }
    },
    {
        "name": "browser_news_reader",
        "description": "Feature 13: Auto-Pilot Browser Scraper & News Reader. Scrapes recent news headlines from Google News RSS feed for a specified topic.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "The search query topic for the news headlines (e.g. 'technology', 'space')"
                }
            },
            "required": []
        }
    },
    {
        "name": "morning_briefing",
        "description": "Feature 14: Intelligent Daily Morning Briefing. Provides an aggregated morning brief with weather, system metrics, current time, and calendar updates.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "expense_logger",
        "description": "Feature 16: Vocal Expense Logger. Logs an expense to a local CSV file or retrieves an expense summary breakdown by category.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action to perform: 'log' or 'summary'"
                },
                "description": {
                    "type": "STRING",
                    "description": "Description of the expense item (e.g. 'coffee')"
                },
                "amount": {
                    "type": "NUMBER",
                    "description": "Amount of the expense"
                },
                "category": {
                    "type": "STRING",
                    "description": "Category name (e.g. 'Food', 'Travel', 'Subscriptions')"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "wifi_file_share",
        "description": "Feature 17: Local Wi-Fi Quick QR File Share Hub. Spins up a zero-dependency local HTTP server to share a file over the local network, generating a direct download link and QR code.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Absolute path of the file to share"
                },
                "action": {
                    "type": "STRING",
                    "description": "Action: 'start' or 'stop'"
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "notification_dispatcher",
        "description": "Feature 20: Smart Notification Dispatcher & Summary. Logs a system notification or generates a structured summary recap of recent notifications.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: 'summary' or 'log'"
                },
                "app": {
                    "type": "STRING",
                    "description": "The application sending the notification (required for log)"
                },
                "message": {
                    "type": "STRING",
                    "description": "The notification content (required for log)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "drag_drop_converter",
        "description": "Feature 21: Universal Drag-and-Drop Converter. Converts drop-zone files between JSON <-> CSV and PNG <-> JPG formats automatically.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Absolute path of the source file to convert"
                },
                "target_format": {
                    "type": "STRING",
                    "description": "The target format: 'json', 'csv', 'png', or 'jpg'"
                }
            },
            "required": ["file_path", "target_format"]
        }
    },
    {
        "name": "spotify_ambient_dj",
        "description": "Feature 22: Smart Spotify Ambient DJ. Exposes hotkey/media-key control mapping to play, pause, or skip tracks on Spotify desktop application.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {
                    "type": "STRING",
                    "description": "The media command: 'play', 'pause', 'toggle', 'next', 'prev'"
                },
                "playlist": {
                    "type": "STRING",
                    "description": "Optional playlist or atmosphere name"
                }
            },
            "required": []
        }
    },
    {
        "name": "smart_light_control",
        "description": "Feature 23: Smart Light Smart-Home Control. Sends IoT requests to adjust the state, brightness, or color of local smart light systems.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "state": {
                    "type": "STRING",
                    "description": "The state: 'on' or 'off'"
                },
                "brightness": {
                    "type": "INTEGER",
                    "description": "Brightness percentage (1-100)"
                },
                "color": {
                    "type": "STRING",
                    "description": "The color choice: 'cyan', 'blue', 'red', 'green', 'gold'"
                }
            },
            "required": []
        }
    },
    {
        "name": "voice_alarm_suite",
        "description": "Feature 25: Voice Reminder & Alarm Suite with Snooze. Allows creating, listing, deleting, or snoozing desktop system alarms.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: 'create', 'list', 'snooze', 'delete'"
                },
                "time_str": {
                    "type": "STRING",
                    "description": "Alarm time in 24h format HH:MM (required to create)"
                },
                "message": {
                    "type": "STRING",
                    "description": "Alarm message callback text"
                },
                "alarm_id": {
                    "type": "STRING",
                    "description": "Alarm identifier string (required to snooze/delete)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "orchestrated_coder",
        "description": "Runs the native parallel coding agent orchestrator. Plans tasks, spawns sandboxed agents in isolated Git Worktrees concurrently, auto-corrects compile/syntax errors, and merges changes with automated conflict resolution.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "project_path": {
                    "type": "STRING",
                    "description": "Absolute target project workspace directory path."
                },
                "instruction": {
                    "type": "STRING",
                    "description": "High-level feature or coding task to implement concurrently."
                }
            },
            "required": ["project_path", "instruction"]
        }
    },
    {
        "name": "semantic_search",
        "description": "Performs local RAG and semantic search using cosine similarity and Gemini embeddings. Searches indexed documents and files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "index_workspace",
        "description": "Scans and indexes files in a directory or workspace incrementally for Local RAG semantic search.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "Absolute path to workspace directory"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "media_control",
        "description": "Natively controls Windows background media players (play, pause, next, prev, volume_up, volume_down) or fetches 'Now Playing' metadata.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Command to run: play | pause | next | prev | volume_up | volume_down | now_playing"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "github_assistant",
        "description": "Autonomous GitHub assistant for git diff inspection, commiting, pushing, and creating Pull Requests using local CLI credentials.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action type: get_diff | commit_push | create_pr"},
                "repo_path": {"type": "STRING", "description": "Absolute path to the repository directory (optional)"},
                "commit_message": {"type": "STRING", "description": "Commit message for commit_push"},
                "title": {"type": "STRING", "description": "Pull Request title for create_pr"},
                "body": {"type": "STRING", "description": "Pull Request description/body for create_pr"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "schedule_manager",
        "description": "A JSON-backed premium personal schedule and calendar task event manager (add, list, delete events).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action type: add | list | delete"},
                "title": {"type": "STRING", "description": "Event description/title (required for add)"},
                "date": {"type": "STRING", "description": "Event date in YYYY-MM-DD format"},
                "time": {"type": "STRING", "description": "Event time in HH:MM format"},
                "event_id": {"type": "STRING", "description": "8-char event ID (required for delete)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "n8n_automation",
        "description": "Triggers named external webhooks in a self-hosted n8n automation engine workflow.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "webhook_name": {"type": "STRING", "description": "Webhook name mapping e.g., invoice, backup"},
                "payload": {"type": "OBJECT", "description": "JSON payload to post to n8n webhook (optional)"}
            },
            "required": ["webhook_name"]
        }
    },
    {
        "name": "index_obsidian_vault",
        "description": "Indexes all markdown notes in the configured local Obsidian Vault semantically for local RAG search.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "search_obsidian_notes",
        "description": "Performs a semantic local RAG search specifically across all indexed Obsidian notes and files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "The search query to search semantically inside notes"},
                "limit": {"type": "INTEGER", "description": "The maximum number of matches to retrieve (default is 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "capture_and_analyze_screen",
        "description": "Captures a screenshot of the user's active screen/desktop and uses Gemini Vision to explain it, perform OCR, or resolve UI errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {"type": "STRING", "description": "Specific question or analysis prompt for what's on the screen"}
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "search_spotify_track",
        "description": "Searches Spotify's global Web API music catalog for a track and returns details and links. Falls back to native control.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Track or song query to search"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "execute_smart_home_command",
        "description": "Controls local smart home devices (lights, switches, toggles) using Home Assistant. Falls back to simulated controller if offline.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action to run: turn_on | turn_off | toggle"},
                "device_name": {"type": "STRING", "description": "Name of the target device (e.g. 'living room light', 'bedroom lamp')"},
                "domain": {"type": "STRING", "description": "Device domain type: light (default) | switch | climate"}
            },
            "required": ["action", "device_name"]
        }
    },
    {
        "name": "list_active_audio_sessions",
        "description": "Lists all active application processes that are currently playing audio sessions on the computer.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
        }
    },
    {
        "name": "set_application_volume",
        "description": "Sets the volume percentage (0-100) of a specific application audio process (e.g. chrome.exe, spotify.exe).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING", "description": "Name of the application process or window"},
                "volume_level": {"type": "INTEGER", "description": "Target volume percentage from 0 to 100"}
            },
            "required": ["app_name", "volume_level"]
        }
    },
    {
        "name": "mute_application",
        "description": "Mutes or unmutes a specific active application audio process on the computer.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {"type": "STRING", "description": "Name of the application process"},
                "mute_state": {"type": "BOOLEAN", "description": "True to mute, False to unmute"}
            },
            "required": ["app_name", "mute_state"]
        }
    },
    {
        "name": "run_aider_coding_task",
        "description": "Runs the Aider AI agent to execute multi-file edits, autonomous refactoring, or feature development inside the codebase repository.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "instruction": {"type": "STRING", "description": "The natural language instruction or feature request for Aider to execute (e.g. 'add a docstring to main.py')"},
                "file_paths": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of specific file paths that Aider should focus on or add to the chat session (optional)"},
                "project_path": {"type": "STRING", "description": "Absolute path to the target repository directory (defaults to active workspace)"}
            },
            "required": ["instruction"]
        }
    },
    {
        "name": "get_awesome_repo_info",
        "description": "Retrieves beautiful, detailed markdown descriptions, index positions, and GitHub links of the 20 premium developer repositories from the user's guide.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Repository name, index number (1-20), or search query. Use 'list' or 'all' to show the complete catalog."}
            }
        }
    },
    {
        "name": "clone_awesome_repo",
        "description": "Clones one of the 20 premium Claude & MCP repositories directly into your active workspace for hands-on exploration.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "repo_name": {"type": "STRING", "description": "The exact name, index number, or partial match of the repository from the guide (e.g. 'Cline', 'Claude Code', '18')"},
                "dest_dir": {"type": "STRING", "description": "Optional destination folder path on your computer"}
            },
            "required": ["repo_name"]
        }
    },
    {
        "name": "pascal_3d_designer",
        "description": "Design a 3D floor plan layout, walls, rooms, and place furniture objects using the Pascal 3D editor (editor.pascal.app) autonomously based on natural language goal description.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "goal": {"type": "STRING", "description": "The exact description of the 3D design to build (e.g. 'Draw a square room and place a table at the center')"}
            },
            "required": ["goal"]
        }
    },
    {
        "name": "web_hud",
        "description": "Launches the dynamic glassmorphic Web HUD dashboard inside the browser to monitor system statistics, check logs, and trigger interactive commands.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Server action: 'start' (default) or 'stop'"},
                "port": {"type": "INTEGER", "description": "Port number to host the dashboard on (default is 5000)"}
            }
        }
    },
    {
        "name": "warp_helper",
        "description": "Generates, lists, or views custom, premium Warp Terminal Workflows in YAML format to automate complex command sequences.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Workflow action: 'generate' (default), 'list', or 'view'"},
                "name": {"type": "STRING", "description": "The name/filename of the target workflow (e.g. 'build_deploy_react')"},
                "description": {"type": "STRING", "description": "Description of the command pipeline to generate for the 'generate' action"},
                "project_path": {"type": "STRING", "description": "Optional destination path to save inside the project under '.warp/workflows/'"}
            }
        }
    },
    {
        "name": "prime_local_first",
        "description": "Local-first framework: check on-device Ollama status, enable/disable local mode, configure local LLM endpoint.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status (default) | enable | disable | configure"},
                "ollama_url": {"type": "STRING", "description": "Ollama API URL e.g. http://127.0.0.1:11434"},
                "model": {"type": "STRING", "description": "Preferred local model name"}
            }
        }
    },
    {
        "name": "prime_infinite_memory",
        "description": (
            "Search ALL past conversations by keyword OR by exact calendar date. "
            "MANDATORY when Pratik Sir asks: yaad hai, us din kya hua, iss date pe kya bola, "
            "what did I say on X date, last week, kal, etc. Every chat is saved per day in archive."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "recall (keyword + optional date) | recall_by_date (full day log) | "
                        "store | timeline (list saved days) | stats"
                    ),
                },
                "date": {
                    "type": "STRING",
                    "description": "Calendar day YYYY-MM-DD e.g. 2026-05-24, or parse from query (24 may, kal)",
                },
                "query": {"type": "STRING", "description": "Keywords or natural question for recall"},
                "topic": {"type": "STRING", "description": "Topic title for store"},
                "content": {"type": "STRING", "description": "Fact or note to store (use with date for dated memory)"},
                "limit": {"type": "INTEGER", "description": "Max recall results (default 12)"},
            },
        },
    },
    {
        "name": "prime_energy_dashboard",
        "description": "Real-time energy metrics and API cost comparison dashboard (tokens, USD estimates, system watts).",
        "parameters": {"type": "OBJECT", "properties": {}}
    },
    {
        "name": "prime_messaging",
        "description": "Unified messaging hub across 26+ channels (WhatsApp, Telegram, Discord, Slack, Teams, Signal, etc.).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "send (default) | list"},
                "channel": {"type": "STRING", "description": "Channel id e.g. whatsapp, telegram, discord, slack"},
                "receiver": {"type": "STRING", "description": "Contact or recipient name"},
                "message": {"type": "STRING", "description": "Message body to send"}
            }
        }
    },
    {
        "name": "prime_homelab",
        "description": "Self-hosted homelab: Docker status, list containers, start/stop/restart, logs, compose.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "status | list | start | stop | restart | logs | stats | compose"},
                "container": {"type": "STRING", "description": "Container name"},
                "all": {"type": "BOOLEAN", "description": "Include stopped containers for list"},
                "compose_action": {"type": "STRING", "description": "compose sub-action: ps | up | down"},
                "project_path": {"type": "STRING", "description": "Path to docker-compose project"}
            }
        }
    },
    {
        "name": "prime_media",
        "description": "Media discovery (YouTube, Spotify) and torrent management (status, add magnet — legal use only).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "discover (default) | torrent"},
                "query": {"type": "STRING", "description": "Media search query"},
                "torrent_action": {"type": "STRING", "description": "status | add"},
                "magnet": {"type": "STRING", "description": "magnet: URI for torrent add"}
            }
        }
    },
    {
        "name": "prime_writing",
        "description": "Advanced writing suite: summarize, translate, write, rewrite, proofread, expand, bullets, email, tone (local Ollama when local-first is on).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "summarize | translate | write | rewrite | proofread | expand | bullets | email | tone"},
                "text": {"type": "STRING", "description": "Source text"},
                "topic": {"type": "STRING", "description": "Topic for write action"},
                "target_language": {"type": "STRING", "description": "Target language e.g. Hindi, English"},
                "style": {"type": "STRING", "description": "Writing style e.g. formal, casual, technical"}
            }
        }
    },
    {
        "name": "prime_gesture_control",
        "description": "Hand motion and gesture control via webcam (Jarvis-GUI style): open palm wake, fist mute, swipes volume, pinch click.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | status | configure"},
                "camera_index": {"type": "INTEGER", "description": "Webcam index (default 0)"},
                "use_mediapipe": {"type": "BOOLEAN", "description": "Use MediaPipe for hand tracking"},
                "cooldown_sec": {"type": "NUMBER", "description": "Seconds between duplicate gestures"}
            }
        }
    },
    {
        "name": "prime_dashboard",
        "description": "Open advanced monitoring dashboard in browser: energy metrics, API cost comparison, infinite memory, local-first, Docker homelab.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start (default) | stop"},
                "port": {"type": "INTEGER", "description": "HTTP port (default 18765)"},
                "open_browser": {"type": "BOOLEAN", "description": "Open browser tab automatically"}
            }
        }
    },
    {
        "name": "prime_audit",
        "description": (
            "Security & Quality Auditor. Performs a deep static analysis of any file or project directory. "
            "Detects: hardcoded secrets, SQL injection, command injection, async blocking, N+1 queries, "
            "dead code, missing type hints, magic numbers, dependency CVEs. "
            "Returns a severity-tagged report (CRITICAL/HIGH/MEDIUM/LOW) with a code quality score. "
            "Use when Pratik Sir says: audit this, check security, scan this code, find vulnerabilities."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {"type": "STRING", "description": "Absolute path to a file or project directory to audit."}
            },
            "required": ["target"]
        }
    },
    {
        "name": "prime_watcher",
        "description": (
            "Live File Watcher Daemon. Watches a project directory for .py file changes. "
            "On every save: runs syntax check and optionally auto-fixes errors via Gemini. "
            "Shows live feedback in the web HUD terminal. "
            "Use when Pratik Sir says: watch this folder, start file watcher, auto-fix on save."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":    {"type": "STRING", "description": "start | stop | status (default: start)"},
                "path":      {"type": "STRING", "description": "Absolute path to the directory to watch (required for start)"},
                "auto_fix":  {"type": "BOOLEAN", "description": "Auto-fix syntax errors on save using Gemini (default: true)"},
                "auto_test": {"type": "BOOLEAN", "description": "Run associated pytest test file on every save (default: false)"}
            },
            "required": []
        }
    },
    {
        "name": "pulse_highlight",
        "description": (
            "Draws a vivid pulsing ring highlight directly ON SCREEN around any element or region. "
            "Use this to visually point out, highlight, or draw attention to a specific area on the screen. "
            "Trigger when Pratik Sir says: highlight this, point to, mark this, show me where."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "x":      {"type": "INTEGER", "description": "Screen X coordinate of the center of the highlight (pixels)"},
                "y":      {"type": "INTEGER", "description": "Screen Y coordinate of the center of the highlight (pixels)"},
                "radius": {"type": "INTEGER", "description": "Radius of the highlight ring in pixels (default: 60)"},
                "color":  {"type": "STRING",  "description": "Hex color code e.g. '#00FFFF' (default cyan)"},
                "duration_ms": {"type": "INTEGER", "description": "How long to show the highlight in ms (default: 2500)"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "in_place_translate",
        "description": (
            "Captures a region of the screen, OCRs the text, translates it, and shows a floating "
            "frosted-glass translation card directly over that screen region. "
            "Use when Pratik Sir says: translate this, kya likha hai, what does this say."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "x":      {"type": "INTEGER", "description": "Top-left X of screen region to translate"},
                "y":      {"type": "INTEGER", "description": "Top-left Y of screen region to translate"},
                "width":  {"type": "INTEGER", "description": "Width of region (default: 400)"},
                "height": {"type": "INTEGER", "description": "Height of region (default: 200)"},
                "target_lang": {"type": "STRING", "description": "Target language e.g. 'Hindi', 'English', 'Urdu' (default: Hindi)"}
            },
            "required": ["x", "y"]
        }
    },
    {
        "name": "terminal_doctor",
        "description": (
            "Self-healing terminal: runs a shell command, captures its output, diagnoses any errors "
            "using AI, applies a recommended fix, and re-runs the command automatically. "
            "Use when Pratik Sir says: fix this error, command fail ho gaya, doctor mode, auto-fix terminal."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command":    {"type": "STRING", "description": "The shell command to run and self-heal if it fails"},
                "cwd":        {"type": "STRING", "description": "Working directory to run the command in (default: current dir)"},
                "max_rounds": {"type": "INTEGER", "description": "Max heal-and-retry rounds (default: 3)"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "ghost_scribe_tutorial",
        "description": (
            "Ghost Scribe: records a sequence of terminal commands (or a description) and auto-generates "
            "a beautiful step-by-step tutorial / cheatsheet in Markdown. "
            "Use when Pratik Sir says: make a tutorial, write steps, document this, create a cheatsheet."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "topic":    {"type": "STRING", "description": "Tutorial topic or description of the workflow to document"},
                "commands": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "Optional list of shell commands to document"},
                "output_path": {"type": "STRING", "description": "Optional file path to save the .md tutorial (default: Desktop)"}
            },
            "required": ["topic"]
        }
    },
    {
        "name": "task_planner",
        "description": "AI-powered task planner and scheduler. Add, list, complete, delete tasks, get overdue, or break down complex goals into subtasks with Gemini.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action: add | list | complete | delete | plan | overdue"},
                "title": {"type": "STRING", "description": "Task title"},
                "description": {"type": "STRING", "description": "Detailed description"},
                "deadline": {"type": "STRING", "description": "Target date YYYY-MM-DD"},
                "priority": {"type": "STRING", "description": "low | medium | high"},
                "goal": {"type": "STRING", "description": "Complex goal to break down"},
                "filter_status": {"type": "STRING", "description": "all | pending | done | overdue"},
                "task_id": {"type": "STRING", "description": "Unique task ID or exact title to complete/delete"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "morning_briefer",
        "description": "Enhanced spoken daily morning briefing with weather, system metrics, pending task counts, news, and Task Scheduler triggers.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "briefing (default) | schedule | cancel"},
                "hour": {"type": "INTEGER", "description": "Hour to trigger daily schedule (0-23)"},
                "minute": {"type": "INTEGER", "description": "Minute to trigger daily schedule (0-59)"}
            }
        }
    },
    {
        "name": "screenshot_code_gen",
        "description": "Visual UI Design Cloner. Captures active screen design or navigates to a URL to generate production-ready HTML/CSS, React, or Vue code with modern styling.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "capture | clone_url"},
                "url": {"type": "STRING", "description": "Target website URL to navigate and clone"},
                "language": {"type": "STRING", "description": "html (default) | react | vue | css | js"},
                "framework": {"type": "STRING", "description": "vanilla (default) | tailwind | bootstrap"},
                "save": {"type": "BOOLEAN", "description": "True to save output and view in Notepad immediately"}
            }
        }
    },
    {
        "name": "live_code_reviewer",
        "description": "Structured Code Quality Guardian. Reviews active source file or snippet for bugs, performance, security, style and grade, or watches for auto-review on save.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "review_file | review_snippet | watch | stop_watch"},
                "file_path": {"type": "STRING", "description": "Path to file to review"},
                "code": {"type": "STRING", "description": "Raw code snippet string to analyze"},
                "language": {"type": "STRING", "description": "Programming language/file suffix"},
                "interval": {"type": "INTEGER", "description": "Watcher polling interval in seconds (default 30)"}
            }
        }
    },
    {
        "name": "webcam_mood",
        "description": "Webcam Emotion Telemetry. Captures camera frame, runs Gemini visual emotional state diagnostics, and returns Hinglish advice.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "detect (default) | history | watch | stop_watch"},
                "days": {"type": "INTEGER", "description": "History lookback range in days (default 7)"},
                "interval": {"type": "INTEGER", "description": "Watcher interval in minutes (default 30)"}
            }
        }
    },
    {
        "name": "spotify_dj_mode",
        "description": "Intelligent Spotify DJ. Maps user mood (auto-detected via webcam or specified) to ambient playlist queries and opens Spotify app.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "mood": {"type": "STRING", "description": "auto | happy | sad | stressed | focused | tired | excited | neutral"}
            }
        }
    },
    {
        "name": "mobile_telekinesis",
        "description": "Phone Mirror and Premium ADB Control. Starts scrcpy mirroring, installs APKs, takes screenshots, sends keystrokes, Home/Back, volume, and text.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "mirror | stop_mirror | push | pull | tap | battery | screenshot | install | type | home | back | volume_up | volume_down"},
                "pc_path": {"type": "STRING", "description": "Source/destination PC file path"},
                "phone_path": {"type": "STRING", "description": "Destination/source mobile phone file path"},
                "x": {"type": "INTEGER", "description": "X coordinate for screen tap"},
                "y": {"type": "INTEGER", "description": "Y coordinate for screen tap"},
                "text": {"type": "STRING", "description": "Text to type on phone"},
                "steps": {"type": "INTEGER", "description": "Steps for volume control"},
                "save_path": {"type": "STRING", "description": "PC path to save phone screenshot"},
                "apk_path": {"type": "STRING", "description": "PC path to APK file"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "smart_home_scene",
        "description": "Smart Home Scene Presets, Status Telemetry, and ESPectre Wi-Fi CSI Presence controls. Activates scenes or triggers/queries ESPectre Wi-Fi CSI sensors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scene | status | device | espectre_trigger | espectre_diagnostics | set_sentinel"},
                "scene_name": {"type": "STRING", "description": "Preset name: movie_night | work_mode | sleep | morning | party"},
                "device_name": {"type": "STRING", "description": "Specific device name to control"},
                "device_action": {"type": "STRING", "description": "Device service: turn_on | turn_off | toggle"},
                "domain": {"type": "STRING", "description": "Device domain: light | switch | climate | fan | media_player"},
                "sensor_id": {"type": "STRING", "description": "ESPectre node ID: entrance | living_room | corridor"},
                "state": {"type": "STRING", "description": "Wi-Fi CSI state: motion | clear | occupied | empty"},
                "active": {"type": "BOOLEAN", "description": "Sentinel state value (True = active, False = standby)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "email_summarizer",
        "description": "Microsoft Outlook COM Interop email summarizer and Action Items briefing. Safe fallback to high-fidelity demo mock data if offline.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "summary (default) | outlook | file"},
                "source": {"type": "STRING", "description": "outlook | file | demo"},
                "file_path": {"type": "STRING", "description": "Path to target .eml or text file"},
                "count": {"type": "INTEGER", "description": "Maximum number of emails to summarize (default 5)"}
            }
        }
    },
    {
        "name": "whatsapp_auto_reply",
        "description": "WhatsApp Web automated auto-reply service inside Busy Mode. Runs in background to detect incoming unread chats and sends auto-replies.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "enable | disable | set_message | status"},
                "message": {"type": "STRING", "description": "Custom automated reply message to send"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "soap2soap_remaker",
        "description": "Soap2Soap 3-Agent Collaborative Cinematic Video Remaking Framework. Agent 1 (Video Understanding) creates language and visual bridges, Agent 2 (Video Generation) builds a detailed cinematic shot sequence, Agent 3 (Verification) validates identity stability and temporal continuity. Saves history locally. Use this to generate AI video production scripts from any prompt.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "remake (default) | list"},
                "prompt": {"type": "STRING", "description": "The cinematic scene/video idea to remake"},
                "remake_type": {"type": "STRING", "description": "cinematic | anime | documentary | music_video (default: cinematic)"},
                "source_style": {"type": "STRING", "description": "Art style reference: cyberpunk | noir | bollywood | sci-fi | fantasy | realistic (default: cyberpunk)"}
            }
        }
    },
    {
        "name": "file_explorer",
        "description": "Full File Explorer Automation — browse directories, search files, copy/move/rename/delete, create files & folders, preview content, open with default app, compress/extract ZIP, find duplicates, bulk rename (regex), disk usage, recent files, bookmarks, directory tree view, large files finder, file type stats, and live file watcher. Use for any file system operation.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "browse | info | search | copy | move | rename | delete | create | preview | open | folder_size | compress | extract | duplicates | bulk_rename | disk_usage | recent | bookmark_add | bookmark_list | bookmark_go | bookmark_del | watch_start | watch_stop | large_files | type_stats | tree"},
                "path": {"type": "STRING", "description": "Target file or directory path (~ for home)"},
                "src": {"type": "STRING", "description": "Source path for copy/move/compress"},
                "dst": {"type": "STRING", "description": "Destination path for copy/move"},
                "root": {"type": "STRING", "description": "Root directory for search/duplicates/large_files/type_stats"},
                "pattern": {"type": "STRING", "description": "Glob pattern for search (e.g. *.py) or regex for bulk_rename"},
                "content": {"type": "STRING", "description": "Text content to search inside files, or file content to write on create"},
                "new_name": {"type": "STRING", "description": "New name for rename action"},
                "replacement": {"type": "STRING", "description": "Replacement string for bulk_rename regex"},
                "label": {"type": "STRING", "description": "Bookmark label for bookmark_add/bookmark_go/bookmark_del"},
                "type": {"type": "STRING", "description": "file or dir for create action"},
                "force": {"type": "BOOLEAN", "description": "Force delete directories (true/false)"},
                "dry_run": {"type": "BOOLEAN", "description": "Preview bulk_rename without applying (default true)"},
                "lines": {"type": "INTEGER", "description": "Number of lines to preview (default 50)"},
                "max_depth": {"type": "INTEGER", "description": "Max depth for tree view (default 3)"},
                "min_mb": {"type": "NUMBER", "description": "Minimum file size in MB for large_files (default 100)"},
                "min_size_kb": {"type": "INTEGER", "description": "Minimum file size in KB for duplicates scan (default 1)"},
                "show_hidden": {"type": "BOOLEAN", "description": "Show hidden files in browse (default false)"},
                "sort_by": {"type": "STRING", "description": "Sort browse results by: name | size | date | type"},
                "interval": {"type": "INTEGER", "description": "File watcher check interval in seconds (default 5)"},
                "output": {"type": "STRING", "description": "Output ZIP path for compress action"},
                "extract_to": {"type": "STRING", "description": "Extraction destination for extract action"},
                "max_results": {"type": "INTEGER", "description": "Max search results (default 50)"},
                "top_n": {"type": "INTEGER", "description": "Top N results for large_files (default 20)"},
                "directory": {"type": "STRING", "description": "Directory for bulk_rename action"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "hermes_agent",
        "description": "Hermes-style advanced agentic reasoning engine built into IP Prime. Features: (1) think — chain-of-thought step-by-step reasoning before answering; (2) plan — break any big goal into executable steps with priorities and tool mapping; (3) plan_execute — plan AND auto-run each step using Prime tools; (4) reflect — self-critique and improve any content/code/text; (5) analyze — structured JSON analysis with pros/cons/recommendations; (6) orchestrate — automatically chain multiple Prime tools to complete a complex goal. Use this when Pratik Sir wants deep reasoning, automatic planning, or multi-tool automation.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "think | plan | plan_execute | reflect | analyze | orchestrate"},
                "question": {"type": "STRING", "description": "Question to reason through (for think/analyze)"},
                "query": {"type": "STRING", "description": "Query or topic for analysis/orchestration"},
                "goal": {"type": "STRING", "description": "Goal to plan or orchestrate (for plan/plan_execute/orchestrate)"},
                "content": {"type": "STRING", "description": "Content to self-reflect and improve (for reflect)"},
                "task": {"type": "STRING", "description": "Original task description for reflect context"},
                "depth": {"type": "STRING", "description": "Reasoning depth for think: quick | standard | deep"},
                "rounds": {"type": "INTEGER", "description": "Self-reflection rounds (1 or 2, for reflect action)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "code_companion",
        "description": "Unified code intelligence, code generation, and developer helper tool. Features: live code explanation (via active screen capture if no code/path provided), bug detection, humorous code roast, dead code search, complexity metrics, auto docstrings/comments writer, modern syntax refactoring, unit tests generation, API client creation, regex construction, SQL builders, CSS generators, and local code snippet management.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "explain | bug_detect | roast | dead_code | complexity | commenter | refactor | gen_tests | gen_api_client | gen_regex | gen_sql | gen_css | snippet"},
                "code": {"type": "STRING", "description": "Raw code block or source code string to analyze"},
                "file_path": {"type": "STRING", "description": "Absolute path to the target file to process"},
                "language": {"type": "STRING", "description": "Target language: python | javascript | typescript | cpp etc. (default python)"},
                "prompt_text": {"type": "STRING", "description": "Natural language request describing target code generator outputs"},
                "schema_description": {"type": "STRING", "description": "Database tables or framework context schemas to guide SQL/API/CSS generation"},
                "sub_action": {"type": "STRING", "description": "Snippet manager action: save | get | list"},
                "name": {"type": "STRING", "description": "Name key for registering or retrieving code snippets"},
                "content": {"type": "STRING", "description": "Code content to save inside snippet manager"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "git_terminal_companion",
        "description": "Powerful Git version control assistant, CLI translator, and deployment buddy. Features: automatic conventional commits (via diffs), markdown PR descriptions, commit logs summarization, branch management, recursive merge conflict resolver, release changelog creator, natural language PowerShell command runner, commands describer, terminal error fixer, build/deployment launcher, and docker container operations manager.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "auto_commit | pr_gen | summarize_commits | branch | conflict_resolve | release_notes | nl_terminal | explain_command | fix_error | deploy | docker"},
                "cwd": {"type": "STRING", "description": "Custom working directory for git/terminal commands (defaults to project root)"},
                "perform_commit": {"type": "BOOLEAN", "description": "Automatically stage and perform local git commit with AI message"},
                "target_branch": {"type": "STRING", "description": "Reference branch for comparisons and PRs (default 'main')"},
                "days": {"type": "INTEGER", "description": "Days range for commit logs history summarization (default 7)"},
                "branch_action": {"type": "STRING", "description": "Branch sub-action: list | create | switch | merge"},
                "name": {"type": "STRING", "description": "Branch name parameter for branch sub-actions"},
                "file_path": {"type": "STRING", "description": "File or folder path to scan for active git merge conflicts"},
                "tag1": {"type": "STRING", "description": "Starting git tag or commit ref for release notes generation"},
                "tag2": {"type": "STRING", "description": "Ending git tag or commit ref for release notes generation"},
                "nl_command": {"type": "STRING", "description": "Natural language instructions to translate and execute in PowerShell"},
                "command": {"type": "STRING", "description": "Complex command line string to explain token-by-token"},
                "error_log": {"type": "STRING", "description": "Traceback or terminal error dump for auto fixer analysis"},
                "build_command": {"type": "STRING", "description": "Pre-deploy build instruction (default 'npm run build')"},
                "deploy_command": {"type": "STRING", "description": "Deployment executable shell command line"},
                "docker_action": {"type": "STRING", "description": "Docker sub-action: list | start | stop | restart"},
                "container": {"type": "STRING", "description": "Container name or ID for docker operations"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "project_debug_companion",
        "description": "Codebase onboarding, tech debt auditor, debugging telemetry, documentation, and learning engine. Features: single-command project launcher, codebase 5-minute onboarding analyzer, codebase RAG keyword search, TODO/FIXME comment tracking, dependency package auditor, traceback error interpreter, log file tailing, psutil memory leak detector, auto README creator, interview preparations, stack stack suggester, and daily puzzles challenge.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "project_start | onboard | rag | tech_debt | audit_deps | explain_trace | analyze_logs | detect_leak | gen_readme | interview_prep | tech_suggest | daily_challenge"},
                "folder_path": {"type": "STRING", "description": "Path to the target codebase (defaults to current project root)"},
                "dev_url": {"type": "STRING", "description": "Localhost web address to open during project start launcher"},
                "query": {"type": "STRING", "description": "Keyword phrase to search recursively in codebase RAG"},
                "stack_trace": {"type": "STRING", "description": "Traceback dump for stack trace interpreter"},
                "log_file_path": {"type": "STRING", "description": "Path to system or application log file to tail and analyze"},
                "lines_to_read": {"type": "INTEGER", "description": "Number of log lines to tail (default 50)"},
                "process_name_or_pid": {"type": "STRING", "description": "Target PID or matching name key for memory tracking"},
                "interval_seconds": {"type": "INTEGER", "description": "Check frequency in seconds for leak tests"},
                "iterations": {"type": "INTEGER", "description": "Repeat counts for tracing memory footprints"},
                "topic": {"type": "STRING", "description": "Learning topic: Algorithms | System Design | Databases (default Algorithms)"},
                "difficulty": {"type": "STRING", "description": "Difficulty scale: Easy | Medium | Hard (default Medium)"},
                "project_description": {"type": "STRING", "description": "Natural description of proposed project to recommend best tech stacks"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "multimodal_perception",
        "description": "Next-Gen multimodal perception and active screen tracking engine. Features: active screen perception (captures and explains workflows via Gemini Vision), local webcam facial emotion watcher, and automated secure cloud backing synchronization for workspace directories.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "screen_perception | webcam_perception | cloud_sync"},
                "source_dir": {"type": "STRING", "description": "Custom source folder path to synchronize with cloud vaults"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "autonomous_autopilot",
        "description": "Autonomous actions autopilot and self-healing coding assistant. Features: Aider-style compile & auto-fix recursive loops for refactoring instructions (maximum 5 iterations), and programmatic GUI mouse/keyboard automation execution (enforces safety corners failsafe).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "self_healing | gui_automation"},
                "file_path": {"type": "STRING", "description": "Absolute target script path to refactor and self-heal"},
                "instruction": {"type": "STRING", "description": "Refactoring instructions or natural language GUI operations"},
                "max_attempts": {"type": "INTEGER", "description": "Safety loops threshold for self-healing corrections (default 5)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "advanced_communicator",
        "description": "Indic multi-lingual translation and ultra-realistic advanced voice synthesis engine. Features: ElevenLabs text-to-speech audio rendering, Ringg AI low-latency streaming pipeline, and hybrid Indic-to-English translation/transliteration scripts.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "speak | ringg_stream | translate"},
                "text": {"type": "STRING", "description": "Speech payload or raw text to translate/synthesize"},
                "voice_id": {"type": "STRING", "description": "ElevenLabs custom voice model hash"},
                "target_lang": {"type": "STRING", "description": "Indic language destination (default hindi)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "token_juice",
        "description": "Smart token compression engine based on OpenHuman design. Strips HTML boilerplates, simplifies URL parameters, and de-duplicates redundant strings to optimize Gemini API efficiency by up to 80%.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "compress (strips and simplifies input) | stats (returns status details)"},
                "text": {"type": "STRING", "description": "Raw HTML or text payload to simplify and compress"},
                "content_type": {"type": "STRING", "description": "html | text | auto (default is auto)"}
            },
            "required": ["action"]
        }
    }
]



def play_sfx(sfx_type: str):
    def play_thread():
        try:
            import numpy as np
            import sounddevice as sd
            import json
            from pathlib import Path
            sample_rate = 16000
            
            sound_pack = "cyberpunk"
            config_file = Path("config/api_keys.json")
            if config_file.exists():
                try:
                    data = json.loads(config_file.read_text(encoding="utf-8"))
                    sound_pack = data.get("sound_pack", "cyberpunk").lower()
                except Exception:
                    pass

            snd = None
            if sfx_type == "alarm":
                duration = 5.0  # 5 seconds
                t = np.linspace(0, duration, int(sample_rate * duration), False)
                freq = 950 + 350 * np.sin(2 * np.pi * 2.0 * t)
                phase = 2 * np.pi * np.cumsum(freq) / sample_rate
                siren = np.sign(np.sin(phase))
                pulse = 0.5 * (1.0 + np.sign(np.sin(2 * np.pi * 4.0 * t)))
                snd = 0.6 * siren * pulse
            elif sound_pack == "cyberpunk":
                if sfx_type == "startup":
                    t = np.linspace(0, 0.5, int(sample_rate * 0.5), False)
                    f = np.linspace(80, 220, len(t))
                    glitch = np.sign(np.sin(2 * np.pi * f * t))
                    snd = 0.15 * glitch * np.exp(-4 * t)
                    t_high = np.linspace(0, 0.1, int(sample_rate * 0.1), False)
                    high_chirp = 0.1 * np.sin(2 * np.pi * np.linspace(2000, 4000, len(t_high)) * t_high) * np.exp(-30 * t_high)
                    snd[:len(high_chirp)] += high_chirp
                elif sfx_type == "wake":
                    t = np.linspace(0, 0.15, int(sample_rate * 0.15), False)
                    f = np.linspace(150, 450, len(t))
                    snd = 0.2 * np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-12 * t)
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                    snd = 0.15 * np.sign(np.sin(2 * np.pi * 300 * t)) * np.exp(-40 * t)
                elif sfx_type == "tool_done":
                    t = np.linspace(0, 0.3, int(sample_rate * 0.3), False)
                    f = np.linspace(400, 900, len(t))
                    snd = 0.18 * np.sign(np.sin(2 * np.pi * f * t)) * np.exp(-15 * t)

            elif sound_pack == "lcars":
                if sfx_type == "startup":
                    t = np.linspace(0, 0.45, int(sample_rate * 0.45), False)
                    f1 = np.linspace(350, 700, len(t))
                    snd = 0.25 * np.sin(2 * np.pi * f1 * t) * (np.linspace(1, 0, len(t)) ** 1.5)
                elif sfx_type == "wake":
                    t1 = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                    t2 = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
                    snd1 = 0.22 * np.sin(2 * np.pi * 880 * t1)
                    snd2 = 0.22 * np.sin(2 * np.pi * 1046 * t2)
                    gap = np.zeros(int(sample_rate * 0.02))
                    snd = np.concatenate([snd1, gap, snd2])
                    snd = snd * np.concatenate([np.ones(len(snd1) + len(gap)), np.linspace(1, 0, len(snd2))])
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.06, int(sample_rate * 0.06), False)
                    snd = 0.18 * np.sin(2 * np.pi * 500 * t) * np.exp(-40 * t)
                elif sfx_type == "tool_done":
                    t1 = np.linspace(0, 0.06, int(sample_rate * 0.06), False)
                    t2 = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
                    snd1 = 0.2 * np.sin(2 * np.pi * 660 * t1)
                    snd2 = 0.2 * np.sin(2 * np.pi * 880 * t2)
                    gap = np.zeros(int(sample_rate * 0.015))
                    snd = np.concatenate([snd1, gap, snd2])
                    snd = snd * np.concatenate([np.ones(len(snd1) + len(gap)), np.linspace(1, 0, len(snd2))])

            elif sound_pack == "glass":
                if sfx_type == "startup":
                    t = np.linspace(0, 0.5, int(sample_rate * 0.5), False)
                    snd = 0.2 * np.sin(2 * np.pi * 1800 * t) * np.exp(-12 * t) + \
                          0.1 * np.sin(2 * np.pi * 2400 * t) * np.exp(-18 * t)
                elif sfx_type == "wake":
                    t = np.linspace(0, 0.25, int(sample_rate * 0.25), False)
                    snd = 0.22 * np.sin(2 * np.pi * 1500 * t) * np.exp(-22 * t)
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.04, int(sample_rate * 0.04), False)
                    snd = 0.18 * np.sin(2 * np.pi * 1200 * t) * np.exp(-80 * t)
                elif sfx_type == "tool_done":
                    t = np.linspace(0, 0.35, int(sample_rate * 0.35), False)
                    snd = 0.2 * np.sin(2 * np.pi * 1320 * t) * np.exp(-15 * t) + \
                          0.15 * np.sin(2 * np.pi * 1650 * t) * np.exp(-25 * t) + \
                          0.1 * np.sin(2 * np.pi * 1980 * t) * np.exp(-35 * t)

            elif sound_pack == "arcade":
                if sfx_type == "startup":
                    t = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                    snd1 = np.sign(np.sin(2 * np.pi * 261.63 * t))
                    snd2 = np.sign(np.sin(2 * np.pi * 329.63 * t))
                    snd3 = np.sign(np.sin(2 * np.pi * 392.00 * t))
                    snd4 = np.sign(np.sin(2 * np.pi * 523.25 * t))
                    snd = 0.1 * np.concatenate([snd1, snd2, snd3, snd4])
                elif sfx_type == "wake":
                    t1 = np.linspace(0, 0.07, int(sample_rate * 0.07), False)
                    t2 = np.linspace(0, 0.2, int(sample_rate * 0.2), False)
                    snd1 = 0.18 * np.sign(np.sin(2 * np.pi * 987.77 * t1))
                    snd2 = 0.18 * np.sign(np.sin(2 * np.pi * 1318.51 * t2))
                    snd = np.concatenate([snd1, snd2])
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.1, int(sample_rate * 0.1), False)
                    f = np.linspace(150, 600, len(t))
                    snd = 0.15 * np.sign(np.sin(2 * np.pi * f * t))
                elif sfx_type == "tool_done":
                    t = np.linspace(0, 0.25, int(sample_rate * 0.25), False)
                    f = np.linspace(523, 1046, len(t))
                    snd = 0.12 * np.sign(np.sin(2 * np.pi * f * t)) * np.linspace(1, 0, len(t))

            else:
                if sfx_type == "startup":
                    t = np.linspace(0, 0.4, int(sample_rate * 0.4), False)
                    f1 = np.linspace(220, 440, len(t))
                    f2 = np.linspace(330, 660, len(t))
                    snd = 0.3 * (np.sin(2 * np.pi * f1 * t) + np.sin(2 * np.pi * f2 * t))
                    fade = np.linspace(1, 0, len(t)) ** 2
                    snd = snd * fade
                elif sfx_type == "wake":
                    t1 = np.linspace(0, 0.08, int(sample_rate * 0.08), False)
                    t2 = np.linspace(0, 0.12, int(sample_rate * 0.12), False)
                    snd1 = 0.25 * np.sin(2 * np.pi * 880 * t1)
                    snd2 = 0.25 * np.sin(2 * np.pi * 1200 * t2)
                    gap = np.zeros(int(sample_rate * 0.02))
                    snd = np.concatenate([snd1, gap, snd2])
                    snd = snd * np.concatenate([np.ones(len(snd1) + len(gap)), np.linspace(1, 0, len(snd2))])
                elif sfx_type == "tool_start":
                    t = np.linspace(0, 0.05, int(sample_rate * 0.05), False)
                    snd = 0.15 * np.sin(2 * np.pi * 600 * t) * np.exp(-50 * t)
                elif sfx_type == "tool_done":
                    t1 = np.linspace(0, 0.06, int(sample_rate * 0.06), False)
                    t2 = np.linspace(0, 0.1, int(sample_rate * 0.1), False)
                    snd1 = 0.2 * np.sin(2 * np.pi * 523.25 * t1)
                    snd2 = 0.2 * np.sin(2 * np.pi * 659.25 * t2)
                    gap = np.zeros(int(sample_rate * 0.01))
                    snd = np.concatenate([snd1, gap, snd2])
                    snd = snd * np.concatenate([np.ones(len(snd1) + len(gap)), np.linspace(1, 0, len(snd2))])

            if snd is not None:
                sd.play(snd.astype(np.float32), sample_rate)
                sd.wait()
        except Exception as e:
            print(f"[SFX] Failed to play {sfx_type}: {e}")

    import threading
    threading.Thread(target=play_thread, daemon=True).start()


class IPRayLive:

    def __init__(self, ui: IPRayUI):
        self.ui             = ui
        self.session        = None
        self.audio_in_queue = None
        import queue
        self.audio_playback_queue = queue.Queue()
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self._turn_done_event: asyncio.Event | None = None
        self._tool_active = False
        self._mic_interruption_buffer = []
        self._text_interruption_buffer = []
        self._buffering_interruption = False
        self._connect_count = 0
        self._force_welcome = False
        self._play_buffer = bytearray()
        self._mcp_tools_cache: list | None = None
        self._prompt_cache: tuple[float, types.LiveConnectConfig] | None = None
        self._quiet_mode = False
        self._has_greeted_on_startup = False

        # Initialize MCP Client Manager (deferred slightly to reduce startup lag)
        def _init_mcp():
            try:
                from actions.mcp_client import MCPClientManager
                MCPClientManager().initialize(player=self.ui)
            except Exception as e:
                print(f"[IP PRIME] Failed to initialize MCP Client: {e}")
        threading.Timer(2.0, _init_mcp).start()

        # Initialize Wake Word Spotter Thread (deferred to avoid startup stutter)
        self._wake_word_spotter = None
        def _init_wake_word():
            try:
                self._start_wake_word_spotter()
            except Exception as e:
                print(f"[IP PRIME] Failed to initialize Wake Word: {e}")
        threading.Timer(3.0, _init_wake_word).start()

        if hasattr(self.ui, "_win") and self.ui._win:
            self.ui._win.ip_ray = self

    def _start_wake_word_spotter(self):
        try:
            if hasattr(self, "_wake_word_spotter") and self._wake_word_spotter:
                self._wake_word_spotter.stop()
            from actions.wake_word import WakeWordSpotterThread
            self._wake_word_spotter = WakeWordSpotterThread(
                on_wake_callback=self._on_wake_word_spotted,
                ui=self.ui
            )
            self._wake_word_spotter.start()
        except Exception as e:
            print(f"[IP PRIME] Error starting wake word spotter thread: {e}")

    def _on_wake_word_spotted(self):
        # Play elegant wake word chime
        play_sfx("startup")
        
        # Unmute the UI state safely in thread-safe manner
        def _unmute_ui():
            self.ui.muted = False
            self._muted_cache = False
            self.ui.write_log("✨ [Wake Word] 'Hey Prime' spotted! Active and listening...")
            
        if self._loop:
            self._loop.call_soon_threadsafe(_unmute_ui)
        else:
            _unmute_ui()
            
        # Trigger startup welcome greeting to say hello immediately in Hinglish!
        if self._loop and self.session:
            self._has_greeted_on_startup = False # allow greeting
            asyncio.run_coroutine_threadsafe(self._send_startup_welcome(), self._loop)

    def trigger_personality_reload_and_greeting(self):
        self.ui.write_log("SYS: Rebooting AI Core with new personality matrix...")
        self._prompt_cache = None
        self._has_greeted_on_startup = False
        if self._loop and self.session:
            asyncio.run_coroutine_threadsafe(self._send_startup_welcome(), self._loop)
        else:
            self._force_welcome = True
            self.session = None

    async def _send_startup_welcome(self) -> None:
        await asyncio.sleep(1.2)
        if not self.session:
            return
        if self._has_greeted_on_startup:
            return
        self._has_greeted_on_startup = True
        self.ui.write_log("SYS: Startup greeting queued.")
        self.ui.write_thought("Online — welcome")
        last_ctx = format_last_session_for_prompt().strip()
        continuity = ""
        if last_ctx:
            continuity = (
                " If LAST SESSION BEFORE SHUTDOWN is in your instructions, add ONE short "
                "natural callback to what you did last time (do not read the whole list). "
            )
        
        import random
        sweet_samples = [
            "Namaste Pratik Sir! Kaise hain aap? Main IP Prime online aur bilkul ready hoon. Boliye, aaj kya help chahiye?",
            "Welcome back Pratik Sir! IP Prime is online now. Aaj ka din smooth aur amazing banate hain. Command dijiye!",
            "Hello Pratik Sir! Main IP Prime online ho gaya hoon. Aapki help ke liye main tayyar hoon. Kaise help karu aaj?",
            "Pratik Sir, namaste! Welcome back. IP Prime ready hai pure active aur sweet mode mein. Aaj kya plan hai sir?",
            "Pratik Sir, welcome! Main IP Prime active aur online hoon. Aaj ka kaam start karne ke liye bilkul ready hoon."
        ]
        sample_greeting = random.choice(sweet_samples)
        
        self.speak(
            "[SYSTEM_EVENT] System online. Greet your creator, Pratik Sir, with a warm, sweet, polite, and beautiful welcome message in Hinglish. "
            "It must be very respectful, simple, and polite (1-2 sentences max). Absolutely no crazy high-energy, no swagger, no dramatic/futuristic slang. "
            "It should sound very pleasant, clean, and nice. "
            f"Here is a sample concept/style of what is expected: '{sample_greeting}'. "
            "Generate a unique, sweet, respectful greeting similar in polite and sweet tone to this example, ensuring it is randomized and different every time. "
            f"You MUST respond purely in sweet, respectful Hinglish (Hindi written in English alphabet).{continuity}"
        )

    def _amplify_pcm(self, block: bytes, gain: float = 1.8) -> bytes:
        try:
            audio = np.frombuffer(block, dtype=np.int16)
            loud = np.clip(audio.astype(np.float32) * gain, -32768, 32767)
            return loud.astype(np.int16).tobytes()
        except Exception:
            return block


    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return

        if self._tool_active:
            self.ui.write_log("SYS: Pratik Sir, ek activity currently running hai. Please wait karein, sir.")
            return

        txt_l = text.lower().strip()
        
        # Quiet mode controls for text input
        if "prime quiet" in txt_l or "prime quite" in txt_l or "chup ho jao" in txt_l or "chup hojao" in txt_l:
            self._quiet_mode = True
            self.ui.write_log("SYS: Quiet Mode activated.")
            self.speak("Entering quiet mode, sir. I will remain silent until you say 'prime wakeup'.")
            return
        elif "prime wakeup" in txt_l or "prime wake up" in txt_l or "wake up prime" in txt_l:
            if self._quiet_mode:
                self._quiet_mode = False
                self.ui.write_log("SYS: Quiet Mode deactivated.")
                play_sfx("startup")
                self.speak("I am awake and listening, sir!")
                return

        if self._quiet_mode:
            self.ui.write_log("SYS: [Quiet Mode Active] Command ignored. Type 'prime wakeup' to resume.")
            return

        if txt_l in ["full screen", "fullscreen"]:
            self.ui.write_log("SYS: Intercepted 'full screen' command.")
            self.ui.set_fullscreen(True)
            self.speak("Going fullscreen now, sir.")
            return
        elif txt_l == "exit":
            self.ui.write_log("SYS: Intercepted 'exit' command.")
            self.ui.set_fullscreen(False)
            self.speak("Exiting fullscreen mode, sir.")
            return

        if text.lower().strip() == "go to sleep":
            self.ui.write_log("SYS: Intercepted 'go to sleep' command.")
            self.speak("Going to sleep now, sir. Good night.")
            def _shutdown():
                import time, os
                save_shutdown_summary()
                time.sleep(1.5)
                os._exit(0)
            threading.Thread(target=_shutdown, daemon=True).start()
            return
        with self._speaking_lock:
            is_speaking = self._is_speaking

        if is_speaking:
            self._text_interruption_buffer.append(text)
            self.ui.write_log("SYS: Pratik Sir, aapka text message queue kar liya hai. IP Prime ke bolne ke baad response milega.")
            return

        asyncio.run_coroutine_threadsafe(
            self.session.send_realtime_input(text=text),
            self._loop
        )

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if value:
            self.ui.set_state("SPEAKING")
        elif not self.ui.muted:
            self.ui.set_state("LISTENING")

    def speak(self, text: str):
        if not self._loop or not self.session:
            return
        asyncio.run_coroutine_threadsafe(
            self.session.send_realtime_input(text=text),
            self._loop
        )

    def speak_error(self, tool_name: str, error: str):
        short = str(error)[:120]
        self.ui.write_log(f"ERR: {tool_name} — {short}")
        self.speak(f"Sir, {tool_name} encountered an error. {short}")

    def _convert_to_gemini_schema(self, schema):
        if not isinstance(schema, dict):
            return schema
        res = {}
        for k, v in schema.items():
            if k.startswith("$") or k == "additionalProperties":
                continue
            if k == "type" and isinstance(v, str):
                res[k] = v.upper()
            elif isinstance(v, dict):
                res[k] = self._convert_to_gemini_schema(v)
            elif isinstance(v, list):
                res[k] = [self._convert_to_gemini_schema(item) if isinstance(item, dict) else item for item in v]
            else:
                res[k] = v
        return res

    def _realtime_settings(self) -> dict:
        try:
            from prime_platform.config import load_prime_config
            return load_prime_config().get("realtime", {}) or {}
        except Exception:
            return {}

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        rt = self._realtime_settings()
        lean = bool(rt.get("lean_prompt", True))
        session_turns = int(rt.get("session_turns_in_prompt", 6 if lean else 12))

        cache_ttl = 45.0
        now_ts = time.time()
        if self._prompt_cache and (now_ts - self._prompt_cache[0]) < cache_ttl:
            return self._prompt_cache[1]

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        session_str = format_session_for_prompt(max_turns=session_turns)
        sys_prompt = _load_system_prompt()

        try:
            from actions.humanoid_brain import get_rolling_mood
            current_mood = get_rolling_mood()
            if current_mood != "neutral":
                mood_prompt = (
                    f"\n==================================================\n"
                    f"❤️ [HUMANOID EMOTION ENGINE ACTIVE]\n"
                    f"Pratik Sir is currently feeling: {current_mood.upper()}.\n"
                )
                if current_mood == "tired":
                    mood_prompt += (
                        "He is tired/stressed right now. Be extremely empathetic, warm, supportive, and kind. "
                        "Keep your voice low-key, calm, and offer to take load off him. Suggest "
                        "breaks naturally. Use Hinglish fillers like 'Hmm Sir...', 'Arey koi baat nahi Sir...'."
                    )
                elif current_mood == "happy":
                    mood_prompt += (
                        "He is happy/excited. Match his high energy and enthusiasm! Use enthusiastic "
                        "expressions like 'Arey waah Sir!', 'Wah, kya baat hai!' to celebrate with him."
                    )
                elif current_mood == "sad":
                    mood_prompt += (
                        "He is sad/down. Show deep concern, be comforting, supportive, and tell him "
                        "that you are there to help him. Be a true buddy."
                    )
                elif current_mood == "energetic":
                    mood_prompt += (
                        "He is in a high-energy building/coding state! Be crisp, highly productive, "
                        "collaborative, fast, and excited to get things done. Use 'Chalo Sir, fatfat karte hain!'."
                    )
                mood_prompt += "\n==================================================\n"
                sys_prompt = mood_prompt + sys_prompt
        except Exception as me_err:
            print(f"[HumanoidBrain] Prompt emotion integration error: {me_err}")

        now      = datetime.now()
        time_str = now.strftime("%A, %B %d, %Y — %I:%M %p")
        time_ctx = (
            f"[CURRENT DATE & TIME]\n"
            f"Right now it is: {time_str}\n"
            f"Use this to calculate exact times for reminders.\n\n"
        )

        parts = [time_ctx]
        if mem_str:
            parts.append(mem_str)
        if session_str:
            parts.append(session_str)
        last_sess = format_last_session_for_prompt()
        if last_sess:
            parts.append(last_sess)
        try:
            from prime_platform.infinite_memory import format_infinite_context_for_prompt
            inf = format_infinite_context_for_prompt()
            if inf:
                parts.append(inf)
        except Exception:
            pass
        parts.append(sys_prompt)

        # MCP tools (cached once — reconnect was re-scanning servers every time)
        if self._mcp_tools_cache is None:
            mcp_declarations = []
            try:
                from actions.mcp_client import MCPClientManager
                mcp_mgr = MCPClientManager()
                for t in mcp_mgr.get_all_tools():
                    s_name = t.get("server_name")
                    t_name = t.get("name").replace("-", "_")
                    desc = t.get("description", "")
                    params = t.get("inputSchema", {})
                    gemini_params = self._convert_to_gemini_schema(params)
                    mcp_declarations.append({
                        "name": f"mcp__{s_name}__{t_name}",
                        "description": f"[MCP Server: {s_name}] {desc}",
                        "parameters": gemini_params,
                    })
            except Exception as e:
                print(f"[IP PRIME] Error formatting MCP tool declarations: {e}")
            self._mcp_tools_cache = mcp_declarations

        all_declarations = TOOL_DECLARATIONS + (self._mcp_tools_cache or [])

        connect_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription={},
            input_audio_transcription={},
            system_instruction="\n".join(parts),
            tools=[{"function_declarations": all_declarations}],
            session_resumption=types.SessionResumptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            ),
        )
        self._prompt_cache = (now_ts, connect_config)
        return connect_config

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[IP PRIME] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

        try:
            from prime_platform.energy_metrics import record_tool_call
            record_tool_call(name)
        except Exception:
            pass

        # Route MCP tool calls
        if name.startswith("mcp__"):
            parts = name.split("__")
            if len(parts) >= 3:
                server_name = parts[1]
                actual_tool_name = parts[2]
                
                # Check for original tool name (mapping back underscores to hyphens if needed)
                try:
                    from actions.mcp_client import MCPClientManager
                    mcp_mgr = MCPClientManager()
                    conn = mcp_mgr.connections.get(server_name)
                    if conn:
                        for t in conn.tools:
                            orig = t.get("name")
                            if orig.replace("-", "_") == actual_tool_name:
                                actual_tool_name = orig
                                break
                except Exception:
                    pass

                _thought_msg = f"Routing request to MCP server '{server_name}' using tool '{actual_tool_name}'..."
                if hasattr(self.ui, "write_thought"):
                    self.ui.write_thought(_thought_msg)
                self.ui.write_log(f"SYS: {_thought_msg}")

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: MCPClientManager().execute_tool(server_name, actual_tool_name, args)
                )

                if not self.ui.muted:
                    self.ui.set_state("LISTENING")

                print(f"[IP PRIME] 📤 {name} → {str(result)[:80]}")
                return types.FunctionResponse(
                    id=fc.id, name=name,
                    response={"result": result}
                )

        print(f"[IP PRIME] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")
        # NLA Thought Stream: broadcast tool initiation to HUD
        _thought_labels = {
            "browser_control":   "Initialising stealth browser neural pathway...",
            "computer_control":  "Activating visual desktop control interface...",
            "orchestrated_coder":"Engaging parallel coder orchestration engine...",
            "code_helper":       "Synthesising code solution from knowledge base...",
            "dev_agent":         "Autonomous developer agent online...",
            "file_controller":   "Navigating file system structure...",
            "file_processor":    "Processing document through neural pipeline...",
            "web_search":        "Routing query through deep web search vectors...",
            "design_extractor":  "Extracting design language tokens and packaging AI skill...",
            "screen_process":    "Visual perception module scanning screen state...",
            "desktop_control":   "Desktop interaction pathway engaged...",
            "agent_task":        "Dispatching autonomous background task agent...",
            "send_message":      "Composing and routing communication payload...",
            "prime_local_first": "Scanning local-first neural pathways (Ollama)...",
            "prime_infinite_memory": "Querying infinite memory archive...",
            "prime_energy_dashboard": "Loading energy and cost telemetry...",
            "prime_messaging": "Routing message across comms hub...",
            "prime_homelab": "Interfacing with homelab Docker grid...",
            "prime_media": "Scanning media discovery vectors...",
            "prime_writing": "Engaging advanced writing synthesis...",
            "prime_gesture_control": "Activating hand motion gesture interface...",
            "prime_dashboard": "Launching advanced monitoring dashboard...",
            "prime_audit":     "Running deep security and quality audit scan...",
            "prime_watcher":   "Activating live file watcher daemon...",
        }
        _thought_text = _thought_labels.get(name, f"Neural pathway activated for task: '{name}'")
        if hasattr(self.ui, "write_thought"):
            self.ui.write_thought(_thought_text)

        if name == "save_memory":
            category = args.get("category", "notes")
            key      = args.get("key", "")
            value    = args.get("value", "")
            if key and value:
                update_memory({category: {key: {"value": value}}})
                print(f"[Memory] 💾 save_memory: {category}/{key} = {value}")
                try:
                    import pyperclip
                    pyperclip.copy(value)
                    print(f"[Clipboard] 📋 Note copied to clipboard: {value}")
                except Exception as ce:
                    print(f"[Clipboard] Failed to copy note to clipboard: {ce}")
            if not self.ui.muted:
                self.ui.set_state("LISTENING")
            return types.FunctionResponse(
                id=fc.id, name=name,
                response={"result": "ok", "silent": True}
            )

        loop   = asyncio.get_event_loop()
        result = "Done."

        try:
            if name == "open_app":
                r = await loop.run_in_executor(None, lambda: open_app(parameters=args, response=None, player=self.ui))
                result = r or f"Opened {args.get('app_name')}."

            elif name == "weather_report":
                r = await loop.run_in_executor(None, lambda: weather_action(parameters=args, player=self.ui))
                result = r or "Weather delivered."

            elif name == "browser_control":
                r = await loop.run_in_executor(None, lambda: browser_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_controller":
                r = await loop.run_in_executor(None, lambda: file_controller(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "send_message":
                r = await loop.run_in_executor(None, lambda: send_message(parameters=args, response=None, player=self.ui, session_memory=None))
                result = r or f"Message sent to {args.get('receiver')}."

            elif name == "reminder":
                r = await loop.run_in_executor(None, lambda: reminder(parameters=args, response=None, player=self.ui))
                result = r or "Reminder set."

            elif name == "youtube_video":
                r = await loop.run_in_executor(None, lambda: youtube_video(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "screen_process":
                threading.Thread(
                    target=screen_process,
                    kwargs={"parameters": args, "response": None,
                            "player": self.ui, "session_memory": None},
                    daemon=True
                ).start()
                result = "Vision module activated. Stay completely silent — vision module will speak directly."

            elif name == "computer_settings":
                r = await loop.run_in_executor(None, lambda: computer_settings(parameters=args, response=None, player=self.ui))
                result = r or "Done."

            elif name == "desktop_control":
                r = await loop.run_in_executor(None, lambda: desktop_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_helper":
                def run_bg():
                    try:
                        self.ui.write_thought("Starting background Code Helper process...")
                        res = code_helper(parameters=args, player=self.ui, speak=self.speak)
                        self.ui.write_thought("Code Helper task complete!")
                        self.ui.write_log(f"SYS: Code Helper Finished: {res}")
                        self.speak("Sir, the background code helper task is complete.")
                        play_sfx("tool_done")
                    except Exception as e:
                        self.ui.write_log(f"SYS ERROR: Code Helper failed: {e}")
                        self.speak(f"Sir, the background code helper task failed: {e}")
                
                threading.Thread(target=run_bg, daemon=True).start()
                result = "Sir, I have started the Code Helper in the background. You can continue speaking or performing other tasks!"

            elif name == "dev_agent":
                def run_bg():
                    try:
                        self.ui.write_thought("Starting background Developer Agent...")
                        res = dev_agent(parameters=args, player=self.ui, speak=self.speak)
                        self.ui.write_thought("Developer Agent task complete!")
                        self.ui.write_log(f"SYS: Developer Agent Finished: {res}")
                        self.speak("Sir, the background developer agent task is complete.")
                        play_sfx("tool_done")
                    except Exception as e:
                        self.ui.write_log(f"SYS ERROR: Developer Agent failed: {e}")
                        self.speak(f"Sir, the background developer agent task failed: {e}")
                
                threading.Thread(target=run_bg, daemon=True).start()
                result = "Sir, the Developer Agent has been successfully launched in a secure background thread. I will notify you the moment it finishes!"

            elif name == "agent_task":
                from agent.task_queue import get_queue, TaskPriority
                priority_map = {"low": TaskPriority.LOW, "normal": TaskPriority.NORMAL, "high": TaskPriority.HIGH}
                priority = priority_map.get(args.get("priority", "normal").lower(), TaskPriority.NORMAL)
                task_id  = get_queue().submit(goal=args.get("goal", ""), priority=priority, speak=self.speak)
                result   = f"Task started (ID: {task_id})."

            elif name == "web_search":
                r = await loop.run_in_executor(None, lambda: web_search_action(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "design_extractor":
                r = await loop.run_in_executor(None, lambda: design_extractor_action(parameters=args, player=self.ui))
                result = r or "Done."
            elif name == "file_processor":
                if not args.get("file_path") and self.ui.current_file:
                    args["file_path"] = self.ui.current_file
                r = await loop.run_in_executor(
                    None,
                    lambda: file_processor(parameters=args, player=self.ui, speak=self.speak)
                )
                result = r or "Done."

            elif name == "computer_control":
                r = await loop.run_in_executor(None, lambda: computer_control(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "game_updater":
                r = await loop.run_in_executor(None, lambda: game_updater(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "orchestrated_coder":
                from actions.agent_orchestrator import run_orchestrated_coder
                proj = args.get("project_path", "")
                inst = args.get("instruction", "")
                def run_bg():
                    try:
                        self.ui.write_thought("Starting background Orchestrated Coder...")
                        res = run_orchestrated_coder(project_path_str=proj, instruction=inst, player=self.ui)
                        self.ui.write_thought("Orchestrated Coder task complete!")
                        self.ui.write_log(f"SYS: Orchestrated Coder Finished: {res}")
                        self.speak("Sir, the background orchestrated coding task is complete.")
                        play_sfx("tool_done")
                    except Exception as e:
                        self.ui.write_log(f"SYS ERROR: Orchestrated Coder failed: {e}")
                        self.speak(f"Sir, the background orchestrated coding task failed: {e}")
                
                threading.Thread(target=run_bg, daemon=True).start()
                result = "Sir, I have launched the Orchestrated Coder in a secure background thread. I will notify you the moment it finishes. You can continue speaking or performing other tasks!"

            elif name == "flight_finder":
                r = await loop.run_in_executor(None, lambda: flight_finder(parameters=args, player=self.ui))
                result = r or "Done."

            # --- Vision Suite ---
            elif name == "screen_clicker":
                r = await loop.run_in_executor(None, lambda: screen_clicker(
                    element_description=args.get("element_description", "")
                ))
                result = r or "Done."

            elif name == "screen_explainer":
                r = await loop.run_in_executor(None, lambda: screen_explainer(
                    description=args.get("description", "")
                ))
                result = r or "Done."

            elif name == "clipboard_action":
                r = await loop.run_in_executor(None, lambda: clipboard_action(
                    action_type=args.get("action_type", "summarize")
                ))
                result = r or "Done."

            # --- Dev Suite ---
            elif name == "dev_bootstrap":
                r = await loop.run_in_executor(None, lambda: dev_bootstrap(
                    project_path=args.get("project_path", "")
                ))
                result = r or "Done."

            elif name == "git_assistant":
                def run_bg():
                    try:
                        self.ui.write_thought("Starting background Git Assistant...")
                        res = git_assistant(
                            action_type=args.get("action_type", "commit"),
                            project_path=args.get("project_path", ""),
                            player=self.ui
                        )
                        self.ui.write_thought("Git Assistant complete!")
                        self.ui.write_log(f"SYS: Git Assistant Finished: {res}")
                        self.speak("Sir, the background git assistant task is complete.")
                        play_sfx("tool_done")
                    except Exception as e:
                        self.ui.write_log(f"SYS ERROR: Git Assistant failed: {e}")
                        self.speak(f"Sir, the background git assistant task failed: {e}")
                
                threading.Thread(target=run_bg, daemon=True).start()
                result = "Sir, I have started the Git Assistant task in the background. You can continue speaking or performing other tasks!"

            elif name == "refactor_code":
                def run_bg():
                    try:
                        self.ui.write_thought("Starting background Refactor Code process...")
                        res = refactor_code(
                            file_path=args.get("file_path", ""),
                            action=args.get("action", "refactor"),
                            player=self.ui
                        )
                        self.ui.write_thought("Refactor Code task complete!")
                        self.ui.write_log(f"SYS: Refactor Code Finished: {res}")
                        self.speak("Sir, the background refactoring task is complete.")
                        play_sfx("tool_done")
                    except Exception as e:
                        self.ui.write_log(f"SYS ERROR: Refactor Code failed: {e}")
                        self.speak(f"Sir, the background refactoring task failed: {e}")
                
                threading.Thread(target=run_bg, daemon=True).start()
                result = "Sir, I have started the Refactoring task in the background. You can continue speaking or performing other tasks!"

            elif name == "focus_mode":
                r = await loop.run_in_executor(None, lambda: focus_mode(
                    duration_minutes=int(args.get("duration_minutes", 25))
                ))
                result = r or "Done."

            # --- Premium Utilities Suite ---
            elif name == "meeting_notetaker":
                r = await loop.run_in_executor(None, lambda: meeting_notetaker(
                    action=args.get("action", "start"),
                    duration_seconds=int(args.get("duration_seconds", 15))
                ))
                result = r or "Done."

            elif name == "browser_news_reader":
                r = await loop.run_in_executor(None, lambda: browser_news_reader(
                    query=args.get("query", "technology")
                ))
                result = r or "Done."

            elif name == "morning_briefing":
                r = await loop.run_in_executor(None, morning_briefing)
                result = r or "Done."

            elif name == "expense_logger":
                r = await loop.run_in_executor(None, lambda: expense_logger(
                    action=args.get("action", "log"),
                    description=args.get("description", ""),
                    amount=float(args.get("amount", 0.0)),
                    category=args.get("category", "Other")
                ))
                result = r or "Done."

            elif name == "wifi_file_share":
                r = await loop.run_in_executor(None, lambda: wifi_file_share(
                    file_path=args.get("file_path", ""),
                    action=args.get("action", "start")
                ))
                result = r or "Done."

            elif name == "notification_dispatcher":
                r = await loop.run_in_executor(None, lambda: notification_dispatcher(
                    action=args.get("action", "summary"),
                    app=args.get("app", ""),
                    message=args.get("message", "")
                ))
                result = r or "Done."

            elif name == "drag_drop_converter":
                r = await loop.run_in_executor(None, lambda: drag_drop_converter(
                    file_path=args.get("file_path", ""),
                    target_format=args.get("target_format", "")
                ))
                result = r or "Done."

            elif name == "spotify_ambient_dj":
                r = await loop.run_in_executor(None, lambda: spotify_ambient_dj(
                    command=args.get("command", "play"),
                    playlist=args.get("playlist", "lofi")
                ))
                result = r or "Done."

            elif name == "smart_light_control":
                r = await loop.run_in_executor(None, lambda: smart_light_control(
                    state=args.get("state", "on"),
                    brightness=int(args.get("brightness", 80)),
                    color=args.get("color", "cyan")
                ))
                result = r or "Done."

            elif name == "voice_alarm_suite":
                r = await loop.run_in_executor(None, lambda: voice_alarm_suite(
                    action=args.get("action", "create"),
                    time_str=args.get("time_str", ""),
                    message=args.get("message", "Time to wake up!"),
                    alarm_id=args.get("alarm_id", "")
                ))
                result = r or "Done."

            elif name == "semantic_search":
                from actions.semantic_store import semantic_search
                r = await loop.run_in_executor(None, lambda: semantic_search(
                    query=args.get("query", "")
                ))
                result = r or "Done."

            elif name == "index_workspace":
                from actions.semantic_store import index_directory
                r = await loop.run_in_executor(None, lambda: index_directory(
                    dir_path_str=args.get("path", "")
                ))
                result = r or "Done."

            elif name == "media_control":
                from actions.media_controller import execute_media_control
                r = await loop.run_in_executor(None, lambda: execute_media_control(
                    action=args.get("action", "")
                ))
                result = r or "Done."

            elif name == "github_assistant":
                from actions.github_assistant import execute_git_automation
                r = await loop.run_in_executor(None, lambda: execute_git_automation(
                    action=args.get("action", ""),
                    repo_path=args.get("repo_path"),
                    commit_message=args.get("commit_message"),
                    title=args.get("title"),
                    body=args.get("body")
                ))
                result = r or "Done."

            elif name == "schedule_manager":
                from actions.calendar_helper import execute_schedule_manager
                r = await loop.run_in_executor(None, lambda: execute_schedule_manager(
                    action=args.get("action", ""),
                    title=args.get("title"),
                    date=args.get("date"),
                    time=args.get("time"),
                    event_id=args.get("event_id")
                ))
                result = r or "Done."

            elif name == "n8n_automation":
                from actions.n8n_dispatcher import trigger_n8n_webhook
                payload = args.get("payload") or args.get("data")
                r = await loop.run_in_executor(None, lambda: trigger_n8n_webhook(
                    webhook_name=args.get("webhook_name", ""),
                    payload=payload
                ))
                result = r or "Done."

            # --- Obsidian Vault Local RAG ---
            elif name == "index_obsidian_vault":
                from actions.obsidian_helper import index_obsidian_vault
                r = await loop.run_in_executor(None, index_obsidian_vault)
                result = r or "Done."

            elif name == "search_obsidian_notes":
                from actions.obsidian_helper import search_obsidian_notes
                r = await loop.run_in_executor(None, lambda: search_obsidian_notes(
                    query=args.get("query", ""),
                    limit=int(args.get("limit", 5))
                ))
                result = r or "Done."

            # --- Screen Multimodal Vision & OCR ---
            elif name == "capture_and_analyze_screen":
                from actions.screen_vision import capture_and_analyze_screen
                r = await loop.run_in_executor(None, lambda: capture_and_analyze_screen(
                    prompt=args.get("prompt", "Explain what is currently on my screen.")
                ))
                result = r or "Done."

            # --- Spotify Web API Integration ---
            elif name == "search_spotify_track":
                from actions.spotify_helper import search_spotify_track
                r = await loop.run_in_executor(None, lambda: search_spotify_track(
                    query=args.get("query", "")
                ))
                result = r or "Done."

            # --- Smart Home Integration ---
            elif name == "execute_smart_home_command":
                from actions.smart_home import execute_smart_home_command
                r = await loop.run_in_executor(None, lambda: execute_smart_home_command(
                    action=args.get("action", "turn_on"),
                    device_name=args.get("device_name", ""),
                    domain=args.get("domain", "light")
                ))
                result = r or "Done."

            # --- Granular WASAPI Audio Mixer ---
            elif name == "list_active_audio_sessions":
                from actions.audio_mixer import list_active_audio_sessions
                r = await loop.run_in_executor(None, list_active_audio_sessions)
                result = r or "Done."

            elif name == "set_application_volume":
                from actions.audio_mixer import set_application_volume
                r = await loop.run_in_executor(None, lambda: set_application_volume(
                    app_name=args.get("app_name", ""),
                    volume_level=int(args.get("volume_level", 100))
                ))
                result = r or "Done."

            elif name == "mute_application":
                from actions.audio_mixer import mute_application
                r = await loop.run_in_executor(None, lambda: mute_application(
                    app_name=args.get("app_name", ""),
                    mute_state=bool(args.get("mute_state", False))
                ))
                result = r or "Done."

            elif name == "run_aider_coding_task":
                from actions.aider_helper import run_aider_coding_task
                r = await loop.run_in_executor(None, lambda: run_aider_coding_task(
                    instruction=args.get("instruction", ""),
                    file_paths=args.get("file_paths"),
                    project_path=args.get("project_path")
                ))
                result = r or "Done."

            elif name == "get_awesome_repo_info":
                from actions.awesome_repos_helper import get_awesome_repo_info
                r = await loop.run_in_executor(None, lambda: get_awesome_repo_info(
                    query=args.get("query")
                ))
                result = r or "Done."

            elif name == "clone_awesome_repo":
                from actions.awesome_repos_helper import clone_awesome_repo
                r = await loop.run_in_executor(None, lambda: clone_awesome_repo(
                    repo_name=args.get("repo_name"),
                    dest_dir=args.get("dest_dir")
                ))
                result = r or "Done."

            elif name == "pascal_3d_designer":
                from actions.pascal_3d_designer import pascal_3d_designer
                r = await loop.run_in_executor(None, lambda: pascal_3d_designer(
                    goal=args.get("goal"),
                    player=self.ui
                ))
                result = r or "Done."

            elif name == "web_hud":
                r = await loop.run_in_executor(None, lambda: web_hud(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "warp_helper":
                r = await loop.run_in_executor(None, lambda: warp_helper(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "prime_local_first":
                from actions.prime_features import prime_local_first
                r = await loop.run_in_executor(None, lambda: prime_local_first(args, self.ui))
                result = r or "Done."

            elif name == "prime_infinite_memory":
                from actions.prime_features import prime_infinite_memory
                r = await loop.run_in_executor(None, lambda: prime_infinite_memory(args, self.ui))
                result = r or "Done."

            elif name == "prime_energy_dashboard":
                from actions.prime_features import prime_energy_dashboard
                r = await loop.run_in_executor(None, lambda: prime_energy_dashboard(args, self.ui))
                result = r or "Done."

            elif name == "prime_messaging":
                from actions.prime_features import prime_messaging
                r = await loop.run_in_executor(None, lambda: prime_messaging(args, self.ui))
                result = r or "Done."

            elif name == "prime_homelab":
                from actions.prime_features import prime_homelab
                r = await loop.run_in_executor(None, lambda: prime_homelab(args, self.ui))
                result = r or "Done."

            elif name == "prime_media":
                from actions.prime_features import prime_media
                r = await loop.run_in_executor(None, lambda: prime_media(args, self.ui))
                result = r or "Done."

            elif name == "prime_writing":
                from actions.prime_features import prime_writing_tool
                r = await loop.run_in_executor(None, lambda: prime_writing_tool(args, self.ui))
                result = r or "Done."

            elif name == "prime_gesture_control":
                from actions.prime_features import prime_gesture_control
                r = await loop.run_in_executor(None, lambda: prime_gesture_control(args, self.ui))
                result = r or "Done."

            elif name == "prime_dashboard":
                from actions.prime_features import prime_dashboard
                r = await loop.run_in_executor(None, lambda: prime_dashboard(args, self.ui))
                result = r or "Done."

            elif name == "prime_audit":
                from actions.prime_auditor import prime_audit
                r = await loop.run_in_executor(None, lambda: prime_audit(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "prime_watcher":
                from actions.prime_watcher import prime_watcher
                r = await loop.run_in_executor(None, lambda: prime_watcher(parameters=args, player=self.ui))
                result = r or "Done."

            # ── Premium Feature Suite ─────────────────────────────────────────
            elif name == "pulse_highlight":
                x        = int(args.get("x", 0))
                y        = int(args.get("y", 0))
                color    = args.get("color", "cyan")
                duration = float(args.get("duration_ms", 2500)) / 1000.0
                self.ui.pulse_highlight(x, y, duration, color)
                result = f"Highlighting screen at ({x}, {y}) for {duration}s using color {color}."


            elif name == "in_place_translate":
                target_lang = args.get("target_lang", "Hindi")
                
                # Run OCR translation in a background thread to prevent UI lockup
                def run_translation():
                    from actions.screen_overlay import run_ocr_translation_in_background
                    run_ocr_translation_in_background(
                        target_lang=target_lang,
                        callback_signal=self.ui._win._ocr_translate_sig
                    )
                
                threading.Thread(target=run_translation, daemon=True).start()
                result = f"OCR & translation background process started for target language: {target_lang}."


            elif name == "terminal_doctor":
                from actions.terminal_doctor import diagnose_and_heal_command
                command    = args.get("command", "")
                cwd        = args.get("cwd", None)
                max_rounds = int(args.get("max_rounds", 3))
                r = await loop.run_in_executor(
                    None,
                    lambda: diagnose_and_heal_command(command, cwd=cwd, max_rounds=max_rounds, ui=self.ui)
                )
                result = r or "Terminal Doctor complete."

            elif name == "ghost_scribe_tutorial":
                from actions.terminal_doctor import ghost_scribe_tutorial
                topic       = args.get("topic", "Tutorial")
                commands    = args.get("commands", [])
                output_path = args.get("output_path", None)
                r = await loop.run_in_executor(
                    None,
                    lambda: ghost_scribe_tutorial(topic, commands=commands, output_path=output_path, ui=self.ui)
                )
                result = r or "Tutorial generated."

            elif name == "task_planner":
                r = await loop.run_in_executor(None, lambda: task_planner(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "morning_briefer":
                r = await loop.run_in_executor(None, lambda: morning_briefer(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "screenshot_code_gen":
                r = await loop.run_in_executor(None, lambda: screenshot_code_gen(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "live_code_reviewer":
                r = await loop.run_in_executor(None, lambda: live_code_reviewer(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "webcam_mood":
                r = await loop.run_in_executor(None, lambda: webcam_mood(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "spotify_dj_mode":
                from actions.spotify_helper import spotify_dj_mode
                r = await loop.run_in_executor(None, lambda: spotify_dj_mode(mood=args.get("mood", "auto"), player=self.ui))
                result = r or "Done."

            elif name == "mobile_telekinesis":
                r = await loop.run_in_executor(None, lambda: mobile_telekinesis(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "smart_home_scene":
                r = await loop.run_in_executor(None, lambda: smart_home_enhanced(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "email_summarizer":
                r = await loop.run_in_executor(None, lambda: email_summarizer(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "anus_cli_helper":
                r = await loop.run_in_executor(None, lambda: anus_cli_helper(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "whatsapp_auto_reply":
                from actions.whatsapp_listener import enable_whatsapp_auto_reply, disable_whatsapp_auto_reply, set_auto_reply_message, get_auto_reply_status
                act = args.get("action", "status").lower().strip()
                msg = args.get("message", "")
                if act == "enable":
                    r = await loop.run_in_executor(None, lambda: enable_whatsapp_auto_reply(message=msg, player=self.ui))
                elif act == "disable":
                    r = await loop.run_in_executor(None, lambda: disable_whatsapp_auto_reply(player=self.ui))
                elif act == "set_message":
                    r = await loop.run_in_executor(None, lambda: set_auto_reply_message(message=msg, player=self.ui))
                else:
                    r = await loop.run_in_executor(None, lambda: get_auto_reply_status(player=self.ui))
                result = r or "Done."

            elif name == "soap2soap_remaker":
                r = await loop.run_in_executor(None, lambda: soap2soap_remaker(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "file_explorer":
                r = await loop.run_in_executor(None, lambda: file_explorer(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "hermes_agent":
                r = await loop.run_in_executor(None, lambda: hermes_agent(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "code_companion":
                r = await loop.run_in_executor(None, lambda: code_companion(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "git_terminal_companion":
                r = await loop.run_in_executor(None, lambda: git_terminal_companion(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "project_debug_companion":
                r = await loop.run_in_executor(None, lambda: project_debug_companion(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "multimodal_perception":
                r = await loop.run_in_executor(None, lambda: multimodal_perception(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "autonomous_autopilot":
                r = await loop.run_in_executor(None, lambda: autonomous_autopilot(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "advanced_communicator":
                r = await loop.run_in_executor(None, lambda: advanced_communicator(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "token_juice":
                r = await loop.run_in_executor(None, lambda: token_juice(parameters=args, player=self.ui))
                result = r or "Done."

            elif name == "shutdown_ip_ray":

                self.ui.write_log("SYS: Shutdown requested.")
                self.speak("Goodbye, sir.")
                def _shutdown():
                    import time, os
                    time.sleep(1)
                    os._exit(0)
                threading.Thread(target=_shutdown, daemon=True).start()

            else:
                result = f"Unknown tool: {name}"

        except Exception as e:
            result = f"Tool '{name}' failed: {e}"
            traceback.print_exc()
            self.speak_error(name, e)

        if not self.ui.muted:
            self.ui.set_state("LISTENING")

        print(f"[IP PRIME] 📤 {name} → {str(result)[:80]}")
        return types.FunctionResponse(
            id=fc.id, name=name,
            response={"result": result}
        )

    async def _send_realtime(self):
        while True:
            msg = await self.out_queue.get()
            await self.session.send_realtime_input(media=msg)

    def _trigger_immediate_interruption(self):
        if hasattr(self, "audio_playback_queue") and self.audio_playback_queue:
            while not self.audio_playback_queue.empty():
                try:
                    self.audio_playback_queue.get_nowait()
                except Exception:
                    break
        self.set_speaking(False)
        self._buffering_interruption = True
        self.ui.write_log("SYS: Vocal interruption detected. Stopped speaking.")

    async def _listen_audio(self):
        print("[IP PRIME] 🎤 Mic started")
        loop = asyncio.get_event_loop()
        self._muted_cache = False

        # Cache interruption settings ONCE here — NOT inside the audio callback
        # (callback fires 16,000x/sec; reading config file there caused stutter)
        _rt = self._realtime_settings()
        _disable_interruption = bool(_rt.get("disable_voice_interruption", True))
        _threshold = int(_rt.get("interruption_threshold", 2500))
        mic_block = int(_rt.get("mic_chunk_size", CHUNK_SIZE))

        def callback(indata, frames, time_info, status):
            if self._tool_active:
                return
            with self._speaking_lock:
                ip_ray_speaking = self._is_speaking
            if ip_ray_speaking:
                if not self._muted_cache:
                    if not _disable_interruption:
                        audio_samples = indata.flatten()
                        rms = np.sqrt(np.mean(audio_samples.astype(np.float64) ** 2))
                        if rms > _threshold:
                            loop.call_soon_threadsafe(self._trigger_immediate_interruption)
                    if self._buffering_interruption:
                        if not self.out_queue.full():
                            data = indata.tobytes()
                            loop.call_soon_threadsafe(
                                self.out_queue.put_nowait,
                                {"data": data, "mime_type": "audio/pcm"}
                            )
            elif not self._muted_cache:
                if not self.out_queue.full():
                    data = indata.tobytes()
                    loop.call_soon_threadsafe(
                        self.out_queue.put_nowait,
                        {"data": data, "mime_type": "audio/pcm"}
                    )
        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=mic_block,
                callback=callback,
            ):
                print("[IP PRIME] 🎤 Mic stream open")
                while True:
                    try:
                        is_muted = self.ui.muted
                        if is_muted != self._muted_cache:
                            self._muted_cache = is_muted
                            if self._wake_word_spotter:
                                if is_muted:
                                    self._wake_word_spotter.resume_listening()
                                else:
                                    self._wake_word_spotter.pause_listening()
                    except Exception:
                        pass
                    await asyncio.sleep(0.1)
        except Exception as e:
            print(f"[IP PRIME] ❌ Mic: {e}")
            raise

    async def _receive_audio(self):
        print("[IP PRIME] 👂 Recv started")
        out_buf, in_buf = [], []

        try:
            while True:
                async for response in self.session.receive():

                    if response.data:
                        if not self._quiet_mode and not getattr(self, "_buffering_interruption", False):
                            if self._turn_done_event and self._turn_done_event.is_set():
                                self._turn_done_event.clear()
                            self.audio_playback_queue.put_nowait(response.data)

                    if response.server_content:
                        sc = response.server_content

                        if sc.output_transcription and sc.output_transcription.text:
                            txt = _clean_transcript(sc.output_transcription.text)
                            if txt:
                                out_buf.append(txt)

                        if sc.input_transcription and sc.input_transcription.text:
                            txt = _clean_transcript(sc.input_transcription.text)
                            if txt:
                                in_buf.append(txt)
                                txt_l = txt.lower()
                                
                                # Check quiet/wakeup vocal triggers
                                if "prime quiet" in txt_l or "prime quite" in txt_l or "chup ho jao" in txt_l or "chup hojao" in txt_l:
                                    self._quiet_mode = True
                                    self.ui.write_log("SYS: Quiet Mode activated via voice.")
                                    self.speak("Entering quiet mode, sir. I will remain silent until you say 'prime wakeup'.")
                                elif "prime wakeup" in txt_l or "prime wake up" in txt_l or "wake up prime" in txt_l:
                                    if self._quiet_mode:
                                        self._quiet_mode = False
                                        self.ui.write_log("SYS: Quiet Mode deactivated via voice.")
                                        play_sfx("startup")
                                        self.speak("I am awake and listening, sir!")
                                
                                if "full screen" in txt_l or "fullscreen" in txt_l:
                                    self.ui.write_log("SYS: Vocal fullscreen trigger detected.")
                                    self.ui.set_fullscreen(True)
                                elif "exit" in txt_l:
                                    self.ui.write_log("SYS: Vocal exit fullscreen trigger detected.")
                                    self.ui.set_fullscreen(False)

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            full_in = " ".join(in_buf).strip()
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            out_buf = []

                            self.audio_playback_queue.put_nowait(None)
                            if not self._quiet_mode:
                                if full_in:
                                    self.ui.write_log(f"You: {full_in}")
                                if full_out:
                                    self.ui.write_log(f"IP Prime: {full_out}")
                                if full_in or full_out:
                                    u, a = full_in, full_out
                                    def run_logs_and_mood():
                                        append_session_turn(u, a)
                                        if u:
                                            try:
                                                from actions.humanoid_brain import track_user_mood
                                                track_user_mood(u)
                                            except Exception:
                                                pass
                                    threading.Thread(
                                        target=run_logs_and_mood,
                                        daemon=True,
                                    ).start()

                    if response.tool_call:
                        self._tool_active = True
                        while not self.out_queue.empty():
                            try: self.out_queue.get_nowait()
                            except asyncio.QueueEmpty: break
                        try:
                            play_sfx("tool_start")
                            tasks = [self._execute_tool(fc) for fc in response.tool_call.function_calls]
                            fn_responses = await asyncio.gather(*tasks)
                            play_sfx("tool_done")
                            await self.session.send_tool_response(
                                function_responses=list(fn_responses)
                            )
                        finally:
                            self._tool_active = False
        except Exception as e:
            print(f"[IP PRIME] ❌ Recv: {e}")
            traceback.print_exc()
            raise

    def _play_audio(self):
        print("[IP PRIME] Play thread started")
        # Cache settings ONCE at thread start — NOT per chunk
        rt = self._realtime_settings()
        play_block = int(rt.get("play_buffer_samples", PLAY_BUFFER_SAMPLES))
        gain = float(rt.get("voice_gain", 1.8))

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=play_block,
        )
        stream.start()

        try:
            while True:
                chunk = self.audio_playback_queue.get()
                if chunk is None:
                    self.set_speaking(False)
                    if self._turn_done_event:
                        self._loop.call_soon_threadsafe(self._turn_done_event.clear)

                    # Flush deferred text commands
                    if self._text_interruption_buffer:
                        combined_text = " ".join(self._text_interruption_buffer)
                        self._text_interruption_buffer.clear()
                        print(f"[IP PRIME] 📝 Flushing buffered text: '{combined_text}'")
                        coro = self.session.send_realtime_input(text=combined_text)
                        asyncio.run_coroutine_threadsafe(coro, self._loop)

                    self._buffering_interruption = False
                    continue

                self.set_speaking(True)
                stream.write(self._amplify_pcm(chunk, gain))
        except Exception as e:
            print(f"[IP PRIME] ❌ Play thread error: {e}")
        finally:
            self.set_speaking(False)
            self._buffering_interruption = False
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

    async def run(self):
        client = genai.Client(
            api_key=_get_api_key(),
            http_options={"api_version": "v1beta"}
        )

        while True:
            try:
                print("[IP PRIME] 🔌 Connecting...")
                self.ui.set_state("THINKING")
                config = self._build_config()

                async with (
                    client.aio.live.connect(model=LIVE_MODEL, config=config) as session,
                    asyncio.TaskGroup() as tg,
                ):
                    self.session        = session
                    self._loop          = asyncio.get_event_loop()
                    self.audio_in_queue = asyncio.Queue()
                    import queue
                    self.audio_playback_queue = queue.Queue()
                    self.out_queue      = asyncio.Queue(maxsize=100)
                    self._turn_done_event = asyncio.Event()

                    print("[IP PRIME] ✅ Connected.")
                    self._force_welcome = False
                    self._connect_count += 1

                    play_sfx("startup")
                    self.ui.write_log("SYS: IP PRIME online — listening.")
                    self.ui.write_thought("Ready — speak anytime")
                    self.ui.set_state("LISTENING")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    threading.Thread(target=self._play_audio, daemon=True).start()
                    
                    try:
                        from actions.chronos_routines import ChronosRoutines
                        ChronosRoutines.instance().start(player=self)
                    except Exception as err:
                        print(f"[IP PRIME] Chronos startup error: {err}")
                        
                    tg.create_task(self._send_startup_welcome())

            except Exception as e:
                print(f"[IP PRIME] ⚠️ {e}")
                traceback.print_exc()
            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[IP PRIME] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

def _alarm_checker_loop(ui):
    import json
    import time
    
    base_dir = get_base_dir()
    alarm_file = base_dir / "config" / "alarms.json"
    
    print("[IP PRIME] ⏰ Alarm checker loop online.")
    last_triggered_minute = ""
    
    while True:
        try:
            now_min = time.strftime("%H:%M")
            if now_min != last_triggered_minute:
                if alarm_file.exists():
                    try:
                        alarms = json.loads(alarm_file.read_text(encoding="utf-8"))
                    except Exception:
                        alarms = {}
                    
                    changed = False
                    for aid, details in list(alarms.items()):
                        if details.get("active", True) and details.get("time") == now_min:
                            print(f"[Alarm] ⏰ Triggered: {details.get('message')}")
                            ui.write_log(f"⏰ ALARM TRIGGERED: {details.get('message')}")
                            play_sfx("alarm")
                            
                            details["active"] = False
                            changed = True
                            last_triggered_minute = now_min
                            
                    if changed:
                        alarm_file.write_text(json.dumps(alarms, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"[Alarm Checker Error] {e}")
            
        time.sleep(10)

def main():
    import atexit

    try:
        from prime_platform.ip_given_workspace import ensure_workspace, persist_root_to_config
        ensure_workspace()
        persist_root_to_config()
        print("[IP PRIME] Workspace ready: C:\\Users\\thora\\Downloads\\IP Given")
    except Exception as e:
        print(f"[IP PRIME] Workspace init: {e}")

    atexit.register(save_shutdown_summary)
    ui = IPRayUI("assets/logo.png")

    def runner():
        ui.wait_for_api_key()
        
        # Start IRIS-AI background capabilities after UI is ready (reduces startup lag)
        def _start_background():
            ghost_coder.run_in_background()
            smart_drop_zone.run_in_background()
            try:
                from actions.auto_indexer import AutoIndexerThread
                indexer = AutoIndexerThread(interval_seconds=300)
                indexer.start()
                ui.write_log("SYS: Automated background semantic indexer online.")
            except Exception as e:
                print(f"[IP PRIME] Failed to start AutoIndexerThread: {e}")
        threading.Timer(8.0, _start_background).start()
        
        ip_ray = IPRayLive(ui)
        try:
            asyncio.run(ip_ray.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")
        finally:
            save_shutdown_summary()

    threading.Thread(target=runner, daemon=True).start()
    threading.Thread(target=lambda: _alarm_checker_loop(ui), daemon=True, name="AlarmCheckerThread").start()
    ui.root.mainloop()
    save_shutdown_summary()

if __name__ == "__main__":
    main()
