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
CHUNK_SIZE          = 1024

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["gemini_api_key"]


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are IP Prime, an advanced personal AI assistant. Your owner is Pratik Thorat. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results — always call the appropriate tool."
        )

_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)

def _clean_transcript(text: str) -> str:    
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()

TOOL_DECLARATIONS = [
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
            "Controls any web browser. Use for: opening websites, searching the web, "
            "clicking elements, filling forms, scrolling, screenshots, navigation, any web-based task. "
            "Always pass the 'browser' parameter when the user specifies a browser (e.g. 'open in Edge', "
            "'use Firefox', 'open Chrome'). Multiple browsers can run simultaneously."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "go_to | search | click | type | scroll | fill_form | smart_click | smart_type | get_text | get_url | press | new_tab | close_tab | screenshot | back | forward | reload | switch | list_browsers | close | close_all"},
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
                "path":        {"type": "STRING", "description": "File/folder path or shortcut: desktop, downloads, documents, home"},
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
        "description": "Writes, edits, explains, runs, or builds code files.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | explain | run | build | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Where to save the file"},
                "file_path":   {"type": "STRING", "description": "Path to existing file for edit/explain/run/build"},
                "code":        {"type": "STRING", "description": "Raw code string for explain"},
                "args":        {"type": "STRING", "description": "CLI arguments for run/build"},
                "timeout":     {"type": "INTEGER", "description": "Execution timeout in seconds (default: 30)"},
            },
            "required": ["action"]
        }
    },
    {
        "name": "dev_agent",
        "description": "Builds complete multi-file projects from scratch: plans, writes files, installs deps, opens VSCode, runs and fixes errors.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "description":  {"type": "STRING", "description": "What the project should do"},
                "language":     {"type": "STRING", "description": "Programming language (default: python)"},
                "project_name": {"type": "STRING", "description": "Optional project folder name"},
                "timeout":      {"type": "INTEGER", "description": "Run timeout in seconds (default: 30)"},
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
            "name, age, city, job, preferences, hobbies, relationships, projects, or future plans. "
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
            if sound_pack == "cyberpunk":
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
        self.out_queue      = None
        self._loop          = None
        self._is_speaking   = False
        self._speaking_lock = threading.Lock()
        self.ui.on_text_command = self._on_text_command
        self._turn_done_event: asyncio.Event | None = None
        self._wake_active = False
        self._wake_timer = 0.0
        self._tool_active = False
        self._current_turn_has_prime = False
        self._temp_audio_chunks = []
        self._mic_interruption_buffer = []
        self._text_interruption_buffer = []
        self._buffering_interruption = False

        # Initialize MCP Client Manager
        try:
            from actions.mcp_client import MCPClientManager
            MCPClientManager().initialize(player=self.ui)
        except Exception as e:
            print(f"[IP PRIME] Failed to initialize MCP Client: {e}")

    def _on_text_command(self, text: str):
        if not self._loop or not self.session:
            return
        # Explicit text input wakes the AI
        self._wake_active = True
        self._wake_timer = time.time()
        self._current_turn_has_prime = True

        txt_l = text.lower().strip()
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
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
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
        # Explicit speaking wakes the AI
        self._wake_active = True
        self._wake_timer = time.time()
        self._current_turn_has_prime = True
        asyncio.run_coroutine_threadsafe(
            self.session.send_client_content(
                turns={"parts": [{"text": text}]},
                turn_complete=True
            ),
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

    def _build_config(self) -> types.LiveConnectConfig:
        from datetime import datetime

        memory     = load_memory()
        mem_str    = format_memory_for_prompt(memory)
        sys_prompt = _load_system_prompt()

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
        parts.append(sys_prompt)

        # Dynamic MCP tools integration
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
                    "parameters": gemini_params
                })
        except Exception as e:
            print(f"[IP PRIME] Error formatting MCP tool declarations: {e}")

        all_declarations = TOOL_DECLARATIONS + mcp_declarations

        return types.LiveConnectConfig(
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

    async def _execute_tool(self, fc) -> types.FunctionResponse:
        name = fc.name
        args = dict(fc.args or {})

        print(f"[IP PRIME] 🔧 {name}  {args}")
        self.ui.set_state("THINKING")

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
                r = await loop.run_in_executor(None, lambda: code_helper(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

            elif name == "dev_agent":
                r = await loop.run_in_executor(None, lambda: dev_agent(parameters=args, player=self.ui, speak=self.speak))
                result = r or "Done."

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
                r = await loop.run_in_executor(None, lambda: run_orchestrated_coder(project_path_str=proj, instruction=inst, player=self.ui))
                result = r or "Done."

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
                r = await loop.run_in_executor(None, lambda: git_assistant(
                    action_type=args.get("action_type", "commit"),
                    project_path=args.get("project_path", ""),
                    player=self.ui
                ))
                result = r or "Done."

            elif name == "refactor_code":
                r = await loop.run_in_executor(None, lambda: refactor_code(
                    file_path=args.get("file_path", ""),
                    action=args.get("action", "refactor"),
                    player=self.ui
                ))
                result = r or "Done."

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

    async def _listen_audio(self):
        print("[IP PRIME] 🎤 Mic started")
        loop = asyncio.get_event_loop()

        def callback(indata, frames, time_info, status):
            if self._tool_active:
                return
            with self._speaking_lock:
                ip_ray_speaking = self._is_speaking
            if ip_ray_speaking:
                if not self.ui.muted:
                    # Compute volume intensity (RMS) to see if Pratik Sir is speaking
                    audio_samples = indata.flatten()
                    rms = np.sqrt(np.mean(audio_samples.astype(np.float64) ** 2))
                    if rms > 800:
                        self._buffering_interruption = True
                    
                    if self._buffering_interruption:
                        data = indata.tobytes()
                        self._mic_interruption_buffer.append(data)
            elif not self.ui.muted:
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
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[IP PRIME] 🎤 Mic stream open")
                while True:
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
                        if self._turn_done_event and self._turn_done_event.is_set():
                            self._turn_done_event.clear()
                        # If already awake and active within the last 1 minute, auto-set active turn
                        if self._wake_active and time.time() - self._wake_timer <= 60:
                            self._current_turn_has_prime = True

                        if self._current_turn_has_prime:
                            self.audio_in_queue.put_nowait(response.data)
                        else:
                            self._temp_audio_chunks.append(response.data)

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

                                # If already awake and active within the last 1 minute, auto-set active turn
                                if self._wake_active and time.time() - self._wake_timer <= 60:
                                    self._current_turn_has_prime = True

                                # Check cumulative transcript in this turn
                                full_in_so_far = " ".join(in_buf).lower()
                                if "prime" in full_in_so_far:
                                    if not self._current_turn_has_prime:
                                        self._current_turn_has_prime = True
                                        self._wake_active = True
                                        self._wake_timer = time.time()
                                        self.ui.write_log("SYS: Wake word 'prime' detected.")
                                        play_sfx("wake")
                                        # Flush all buffered audio chunks
                                        while self._temp_audio_chunks:
                                            self.audio_in_queue.put_nowait(self._temp_audio_chunks.pop(0))

                                # Vocal fullscreen triggers only work when wake-word is confirmed/active
                                if self._current_turn_has_prime:
                                    if "full screen" in txt_l or "fullscreen" in txt_l:
                                        self.ui.write_log("SYS: Vocal fullscreen trigger detected.")
                                        self.ui.set_fullscreen(True)
                                    elif "exit" in txt_l:
                                        self.ui.write_log("SYS: Vocal exit fullscreen trigger detected.")
                                        self.ui.set_fullscreen(False)

                        if sc.turn_complete:
                            if self._turn_done_event:
                                self._turn_done_event.set()

                            # Check for sleep timeout (1 minute of inactivity)
                            if self._wake_active and time.time() - self._wake_timer > 60:
                                self._wake_active = False
                                self.ui.write_log("SYS: Sleep mode activated after 1 minute of inactivity.")

                            # A turn is active if it had "prime" or if the wake period is still valid
                            is_active = self._current_turn_has_prime or (self._wake_active and time.time() - self._wake_timer <= 60)

                            full_in = " ".join(in_buf).strip()
                            in_buf = []

                            full_out = " ".join(out_buf).strip()
                            out_buf = []

                            if is_active:
                                self.audio_in_queue.put_nowait(None)
                                if full_in:
                                    self.ui.write_log(f"You: {full_in}")
                                if full_out:
                                    self.ui.write_log(f"IP Prime: {full_out}")
                                # Reset wake timer on successful active response
                                self._wake_timer = time.time()
                            else:
                                # Suppress response, clear buffered chunks
                                self._temp_audio_chunks = []
                                if full_in:
                                    self.ui.write_log(f"You (Ignored): {full_in}")

                            # Reset turn-level flag for the next turn
                            self._current_turn_has_prime = False

                    if response.tool_call:
                        self._tool_active = True
                        while not self.out_queue.empty():
                            try: self.out_queue.get_nowait()
                            except asyncio.QueueEmpty: break
                        try:
                            # Check for sleep timeout
                            if self._wake_active and time.time() - self._wake_timer > 60:
                                self._wake_active = False
                                self.ui.write_log("SYS: Sleep mode activated after 1 minute of inactivity.")

                            # Refuse tool execution if neither prime spoken nor wake timer active
                            is_active = self._current_turn_has_prime or (self._wake_active and time.time() - self._wake_timer <= 60)
                            if not is_active:
                                fn_responses = []
                                for fc in response.tool_call.function_calls:
                                    fn_responses.append({
                                        "id": fc.id,
                                        "name": fc.name,
                                        "response": {"result": "Ignored, user did not mention wake word."}
                                    })
                                await self.session.send_tool_response(function_responses=fn_responses)
                                continue

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

    async def _play_audio(self):
        print("[IP PRIME] 🔊 Play started")

        stream = sd.RawOutputStream(
            samplerate=RECEIVE_SAMPLE_RATE,
            channels=CHANNELS,
            dtype="int16",
            blocksize=CHUNK_SIZE,
        )
        stream.start()

        try:
            while True:
                chunk = await self.audio_in_queue.get()
                if chunk is None:
                    self.set_speaking(False)
                    if self._turn_done_event:
                        self._turn_done_event.clear()

                    # Flush deferred text commands
                    if self._text_interruption_buffer:
                        combined_text = " ".join(self._text_interruption_buffer)
                        self._text_interruption_buffer.clear()
                        print(f"[IP PRIME] 📝 Flushing buffered text interruption: '{combined_text}'")
                        self._wake_active = True
                        self._wake_timer = time.time()
                        self._current_turn_has_prime = True
                        await self.session.send_client_content(
                            turns={"parts": [{"text": combined_text}]},
                            turn_complete=True
                        )

                    # Flush deferred microphone audio chunks
                    if self._mic_interruption_buffer:
                        print(f"[IP PRIME] 🎙️ Flushing {len(self._mic_interruption_buffer)} buffered audio chunks to the server...")
                        self._wake_active = True
                        self._wake_timer = time.time()
                        self._current_turn_has_prime = True
                        for data in self._mic_interruption_buffer:
                            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                        self._mic_interruption_buffer.clear()

                    self._buffering_interruption = False
                    continue
                
                # Model speaking automatically wakes/keeps IP Prime awake and active
                self._wake_active = True
                self._wake_timer = time.time()

                self.set_speaking(True)
                
                # Amplification to increase volume ("iski awaj or bada doo")
                try:
                    audio_data = np.frombuffer(chunk, dtype=np.int16)
                    # 1.0x scaling (clean/original volume) to completely prevent digital clipping distortion
                    amplified_data = np.clip(audio_data.astype(np.float32) * 1.0, -32768, 32767).astype(np.int16)
                    chunk = amplified_data.tobytes()
                except Exception as amp_err:
                    print(f"[IP PRIME] ⚠️ Volume scale error: {amp_err}")

                await asyncio.to_thread(stream.write, chunk)
        except Exception as e:
            print(f"[IP PRIME] ❌ Play: {e}")
            raise
        finally:
            self.set_speaking(False)
            self._mic_interruption_buffer.clear()
            self._text_interruption_buffer.clear()
            self._buffering_interruption = False
            stream.stop()
            stream.close()

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
                    self.out_queue      = asyncio.Queue(maxsize=100)
                    self._turn_done_event = asyncio.Event()

                    print("[IP PRIME] ✅ Connected.")
                    play_sfx("startup")
                    self.ui.set_state("LISTENING")
                    self.ui.write_log("SYS: IP PRIME online.")

                    async def send_welcome():
                        await asyncio.sleep(1) # Give audio time to initialize
                        self.speak("[SYSTEM_EVENT] System online. Greet your creator, Pratik Thorat, with an exceptionally crazy, high-energy, and completely random welcome message. It must be wildly different every time, full of futuristic vibes, swagger, and absolute awesomeness (1-2 sentences max). You MUST respond purely in Hinglish (Hindi written in English alphabet).")

                    tg.create_task(self._send_realtime())
                    tg.create_task(self._listen_audio())
                    tg.create_task(self._receive_audio())
                    tg.create_task(self._play_audio())
                    tg.create_task(send_welcome())

            except Exception as e:
                print(f"[IP PRIME] ⚠️ {e}")
                traceback.print_exc()
            self.set_speaking(False)
            self.ui.set_state("THINKING")
            print("[IP PRIME] 🔄 Reconnecting in 3s...")
            await asyncio.sleep(3)

def main():
    ui = IPRayUI("assets/logo.png")

    def runner():
        ui.wait_for_api_key()
        ip_ray = IPRayLive(ui)
        try:
            asyncio.run(ip_ray.run())
        except KeyboardInterrupt:
            print("\n🔴 Shutting down...")

    threading.Thread(target=runner, daemon=True).start()
    ui.root.mainloop()

if __name__ == "__main__":
    main()