"""
core/tool_registry.py -- IP Prime tool declarations registry.

The TOOL_DECLARATIONS list is consumed by IPRayPlayer._build_tools() to register
all available function-calling tools with the Gemini live session.

To add a new tool:
  1. Append a new dict entry to TOOL_DECLARATIONS following the existing schema.
  2. Add the corresponding elif branch in main.py IPRayPlayer._handle_tool_call().
"""

from __future__ import annotations

TOOL_DECLARATIONS: list[dict] = [
    {
        "name": "autonomous_cli_helper",
        "description": (
            "Runs autonomous shell execution loops to achieve terminal goals. "
            "Internally powered by autonomous_shell_helper."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "autonomous_run"
                },
                "goal": {
                    "type": "STRING",
                    "description": "The command-line objective to achieve autonomously (required for autonomous_run)"
                },
                "max_steps": {
                    "type": "INTEGER",
                    "description": "Max steps for autonomous loop, default is 5"
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
        "name": "close_app",
        "description": (
            "Closes any application, window, or software currently open on the computer. "
            "Use this whenever the user asks to close, terminate, shutdown, or exit any app "
            "or window."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app_name": {
                    "type": "STRING",
                    "description": "Exact name of the application or window to close (e.g. 'WhatsApp', 'Calculator', 'Editor')"
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
                "city": {"type": "STRING", "description": "City name"},
                "open_browser": {
                    "type": "BOOLEAN",
                    "description": "Set to true ONLY if the user explicitly asked to open or show the weather webpage/browser window. Default is false."
                }
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
        "description": "Writes, edits, explains, runs, or builds code files. Default save folder: C:\\Users\\thora\\Downloads\\output\\code",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action":      {"type": "STRING", "description": "write | edit | patch | test | explain | run | build | optimize | screen_debug | auto (default: auto)"},
                "description": {"type": "STRING", "description": "What the code should do or what change to make"},
                "language":    {"type": "STRING", "description": "Programming language (default: python)"},
                "output_path": {"type": "STRING", "description": "Save path (default: C:\\Users\\thora\\Downloads\\output\\code\\)"},
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
        "description": "Builds complete multi-file projects. Also does cross-file project refactor and project intelligence/explain. Saves under C:\\Users\\thora\\Downloads\\output\\projects by default.",
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
        "description": "Feature 8: Smart Meeting Transcriber & Note-Taker. Starts or stops recording meeting notes, or deploys a Clara AI notetaker bot to join a Google Meet, Zoom, or Microsoft Teams call.",
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
                },
                "meeting_url": {
                    "type": "STRING",
                    "description": "The Google Meet, Zoom, or Microsoft Teams link for the Clara AI bot to join and record"
                },
                "meeting_title": {
                    "type": "STRING",
                    "description": "The title or subject of the meeting"
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
        "name": "ip_army",
        "description": "Deploys the IP AI Army of specialized agents (IP Scout, IP Scribe, IP Codex, IP Lexicon, IP Audit) to execute complex coding, writing, localization, and audit operations concurrently.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "project_path": {
                    "type": "STRING",
                    "description": "Optional absolute path to target project workspace directory."
                },
                "instruction": {
                    "type": "STRING",
                    "description": "Goal instruction to decompose and execute using the AI army specialized agents."
                }
            },
            "required": ["instruction"]
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
        "name": "compact_memory",
        "description": "Compacts and vacuums local database memory tables (LanceDB) and cleans up old versions to optimize search performance and save disk space.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "claude_code",
        "description": "Runs the autonomous Claude Code CLI developer agent for complex multi-file coding and refactoring tasks without API cost using free local proxy.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action: run | start_proxy | stop_proxy | status"},
                "instruction": {"type": "STRING", "description": "The coding prompt/instruction for Claude Code (required for run)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "auto_organize_notes",
        "description": "Scans the Obsidian Vault for new or modified notes, extracts topics using Gemini, and appends semantic double-bracket [[Topic]] links to notes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "generate_vault_digest",
        "description": "Generates a comprehensive daily/weekly markdown productivity digest containing completed/pending tasks and screen time info, saving it directly to Daily Digests/ in the Obsidian Vault.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "digest_type": {
                     "type": "STRING",
                     "description": "Type of digest to compile: 'daily' (default) or 'weekly'"
                }
            },
            "required": []
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
        "name": "brain_search",
        "description": (
            "🧠 UNLIMITED BRAIN — searches ALL memory layers at once: long-term, episodic, "
            "knowledge base, archive transcripts, SQLite graph (entities/facts/timeline), "
            "compressed digests, and vector store. Use when Pratik Sir asks to remember, "
            "recall, search, or find ANYTHING from the past."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query — keywords, names, topics, anything"},
                "limit": {"type": "INTEGER", "description": "Max results to return (default: 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "brain_stats",
        "description": "Shows full statistics of the Unlimited Memory Brain — counts across all 8 layers.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "brain_store_fact",
        "description": (
            "Stores a structured fact (subject-predicate-object triple) in the brain's graph. "
            "Use for permanent knowledge: 'Pratik likes Python', 'IP Prime was created in 2025'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "subject": {"type": "STRING", "description": "Who/what the fact is about"},
                "predicate": {"type": "STRING", "description": "The relationship or property"},
                "object": {"type": "STRING", "description": "The value or target"},
            },
            "required": ["subject", "predicate", "object"],
        },
    },
    {
        "name": "brain_store_event",
        "description": (
            "Records a dated event in the brain's timeline. Use for birthdays, milestones, "
            "important dates, achievements, or anything that happened on a specific date."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "event_date": {"type": "STRING", "description": "Date in YYYY-MM-DD format"},
                "summary": {"type": "STRING", "description": "What happened"},
                "event_type": {"type": "STRING", "description": "general | birthday | milestone | project | personal"},
                "importance": {"type": "INTEGER", "description": "1-10 importance scale (default: 5)"},
            },
            "required": ["event_date", "summary"],
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
    },
    {
        "name": "local_llm",
        "description": "Switch active intelligence engine to local offline LLM (Ollama) or back online.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "switch_offline | switch_online | status"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "model_switcher",
        "description": "Toggles active model config settings (Gemini, Claude, GPT-4o, local Ollama).",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "switch | status"},
                "model_name": {"type": "STRING", "description": "Target model: gemini | claude | gpt-4o | ollama"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "force_nvidia",
        "description": "Forces all query responses through NVIDIA NIM models until reset, sir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "force_gemini",
        "description": "Forces all query responses through Gemini until reset, sir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "auto_route",
        "description": "Restores smart automatic routing mode (NVIDIA for coding, Gemini for other tasks), sir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "set_coding_model",
        "description": "Changes the specific NVIDIA model used for coding queries, sir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "model_name": {
                    "type": "STRING",
                    "description": "NVIDIA model name, e.g. nvidia/llama-3.1-nemotron-70b-instruct | meta/codellama-70b | mistralai/codestral-22b-instruct-v0.1 | google/codegemma-7b"
                }
            },
            "required": ["model_name"]
        }
    },
    {
        "name": "habit_tracker",
        "description": "AI Daily Habit Tracker module. Register, track streaks, check daily goals.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add | check | report | delete | evening_check"},
                "name": {"type": "STRING", "description": "Habit name to register or check off"},
                "frequency": {"type": "STRING", "description": "daily (default) | weekly"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "email_ai",
        "description": "Gmail & Outlook inbox scanner, digest compiler, and auto draft responder.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read | summary | draft | reply | search | digest"},
                "source": {"type": "STRING", "description": "Inbox source: gmail | outlook | all"},
                "count": {"type": "INTEGER", "description": "Number of email updates to pull"},
                "to": {"type": "STRING", "description": "Recipient address"},
                "subject": {"type": "STRING", "description": "Email subject string"},
                "body": {"type": "STRING", "description": "Email body content"},
                "email_id": {"type": "STRING", "description": "Reply thread ID target"},
                "message": {"type": "STRING", "description": "Reply email body text"},
                "query": {"type": "STRING", "description": "Search keyword phrase"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "aislop_helper",
        "description": "🛡️ AI-SLOP QUALITY GATE — scans and auto-fixes AI-generated code. Detects dead code, unused imports, unfinished placeholders (# TODO, stubs). Runs standard and aggressive code auto-fixes. Use when Pratik Sir says: check code quality, clean stubs, scan for AI slop, fix placeholders.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "scan (default) | fix"},
                "target": {"type": "STRING", "description": "Absolute or relative path to file or directory to scan/fix (defaults to workspace root)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "discord_helper",
        "description": "Discord channel reader, servers manager, and userbot dispatcher.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "read | send | servers | mentions"},
                "channel": {"type": "STRING", "description": "Target channel name key (default: general)"},
                "message": {"type": "STRING", "description": "Text body to dispatch"},
                "count": {"type": "INTEGER", "description": "History logs cap listing limit"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "telegram_bot",
        "description": "Telegram remote control bot daemon manager. Status/Run/Screenshot hooks.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | send | poll"},
                "message": {"type": "STRING", "description": "Push notification text content"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "live_translator",
        "description": "Real-time translation, OCR screen translation, and live voice translations.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "translate | screen | set_lang | mic"},
                "text": {"type": "STRING", "description": "Payload to translate"},
                "target": {"type": "STRING", "description": "Target ISO lang code (e.g. hi, fr)"},
                "source": {"type": "STRING", "description": "Source ISO lang code (e.g. en, auto)"},
                "target_lang": {"type": "STRING", "description": "Set active target lang"},
                "source_lang": {"type": "STRING", "description": "Set active source lang"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "docker_controller",
        "description": "Docker and Virtual Machine (VirtualBox/VMware) manager.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list_containers | control_container | logs | list_vms | control_vm"},
                "name": {"type": "STRING", "description": "Container name or ID for Docker"},
                "container_action": {"type": "STRING", "description": "start | stop | restart"},
                "vm_name": {"type": "STRING", "description": "Hypervisor virtual machine title"},
                "vm_action": {"type": "STRING", "description": "start | stop"},
                "tail": {"type": "INTEGER", "description": "Logs rows tailing (default: 20)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "clipboard_manager",
        "description": "Clipboard logger & categorizer. Search, restore, clear copied history.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | search | history | restore | clear"},
                "query": {"type": "STRING", "description": "Search copied data history query"},
                "count": {"type": "INTEGER", "description": "History logs cap listing limit"},
                "value": {"type": "STRING", "description": "Exact text or index value to restore to clipboard"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "pr_reviewer",
        "description": "AI-automated GitHub pull request code reviewer. Scans diffs, posts review comments.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | review"},
                "repo": {"type": "STRING", "description": "Target repository (e.g. 'owner/repo')"},
                "pr_number": {"type": "INTEGER", "description": "PR number ID"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "venv_manager",
        "description": "Local virtualenv and Conda environments manager.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "list | create | delete | packages | install"},
                "name": {"type": "STRING", "description": "Local folder path name or Conda target env name"},
                "mode": {"type": "STRING", "description": "venv (default) | conda"},
                "package": {"type": "STRING", "description": "Target pip package name to install"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "presentation_generator",
        "description": "AI PowerPoint presentation deck generator.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate"},
                "topic": {"type": "STRING", "description": "Target presentation subject"},
                "slides": {"type": "INTEGER", "description": "Target slides count (default: 5)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "health_monitor",
        "description": "Posture slouch checker and break interval reminder tracker.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | stats"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "journal",
        "description": "Mood analytics journal. Logs daily vocal thoughts and calculates mood trends.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add | read | search | trends | summary"},
                "text": {"type": "STRING", "description": "Vocal / text journal entry body"},
                "mood": {"type": "STRING", "description": "Mood tag: happy | sad | stressed | neutral"},
                "date": {"type": "STRING", "description": "Target log date: YYYY-MM-DD"},
                "query": {"type": "STRING", "description": "Search keyword phrase"},
                "tags": {"type": "STRING", "description": "Comma-separated tag strings"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "screen_time",
        "description": "Active window usage screen-time log system and daily app limit alerts.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "start | stop | get | report | set_limit | top"},
                "app": {"type": "STRING", "description": "Application package name key"},
                "limit": {"type": "INTEGER", "description": "Usage threshold limit in minutes"},
                "count": {"type": "INTEGER", "description": "Top items listing cap limit"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "health_tracker",
        "description": "Daily consumption logger. Track meals, water ML volume, and sleep hours.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action: log_water | set_goal | log_meal | log_sleep | summary"},
                "value": {"type": "INTEGER", "description": "Water volume logged in ml"},
                "goal": {"type": "INTEGER", "description": "Target daily water goal in ml"},
                "meal": {"type": "STRING", "description": "Meal description string"},
                "calories": {"type": "INTEGER", "description": "Estimated calorie intake (kcal)"},
                "sleep_hours": {"type": "NUMBER", "description": "Sleep hours duration today"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "finance_tracker",
        "description": "Stock and crypto watchlist portfolio price watcher with alert limits.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "add | remove | summary | set_alert"},
                "ticker": {"type": "STRING", "description": "Stock ticker or crypto ID (e.g. TCS.NS, BTC-USD)"},
                "target": {"type": "NUMBER", "description": "Price alert target valuation"},
                "direction": {"type": "STRING", "description": "above (default) | below"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "network_monitor",
        "description": "Bandwidth speed counters and local connected network device discovery.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action: stats | speed | list | set_alert | top_apps"},
                "alert_active": {"type": "BOOLEAN", "description": "Enable unknown device triggers"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "wifi_speed_logger",
        "description": "Automated speedtest logger. Logs bandwidth diagnostics to speed_log.csv.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "test | history | average | set_threshold | start | stop"},
                "threshold": {"type": "NUMBER", "description": "Speed alert download threshold (Mbps)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "second_monitor_overlay",
        "description": "Glassmorphic transparent second monitor HUD status overlay.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "enable | disable | update_tasks"},
                "value": {"type": "STRING", "description": "HUD checklist tasks string update"}
            },
            "required": ["action"]
        }
    },

    {
        "name": "enable_hacker_mode",
        "description": "Activates Hacker Mode, updating your personality to an expert ethical hacker and enabling the security console skull badge, sir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "disable_hacker_mode",
        "description": "Deactivates Hacker Mode and restores default assistant operations, sir.",
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "password_toolkit",
        "description": "Local password security toolkit. Analyzes strength, calculates entropy, generates secure keys or memorable passphrases, and runs local hashes.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "strength | generate_strong | generate_passphrase | hash | crack | check_common"},
                "text": {"type": "STRING", "description": "Password or hash text input"},
                "length": {"type": "INTEGER", "description": "Length of secure password to generate (default 16)"},
                "words_count": {"type": "INTEGER", "description": "Words count for memorable passphrase generation (default 4)"},
                "algorithm": {"type": "STRING", "description": "Hashing algorithm: md5 | sha1 | sha256 | sha512"},
                "wordlist_path": {"type": "STRING", "description": "Optional file path to local wordlist for hashing checks"},
                "confirmed": {"type": "STRING", "description": "Must be set to 'yes' to run scope audit checks on your owned hashes"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "encryption_toolkit",
        "description": "Local encryption and digital signatures toolkit. Encrypts or decrypts local files (AES-256), generates RSA keypairs, signs files, and verifies signatures.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "encrypt | decrypt | generate_rsa | sign | verify"},
                "path": {"type": "STRING", "description": "Target file or output directory path to encrypt, decrypt, sign, or verify"},
                "password": {"type": "STRING", "description": "The secret password/key to derive AES encryption keys"},
                "key_path": {"type": "STRING", "description": "Optional private/public key PEM file path for sign/verify"},
                "sig_path": {"type": "STRING", "description": "Optional digital signature .sig file path to verify"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "ask_antigravity",
        "description": "Delegates complex coding tasks, code refactoring, full project building, or advanced programming logic to Antigravity (your master AI assistant). Use this whenever the user asks you to write code, do software engineering, or delegate logic to Antigravity.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "instruction": {
                    "type": "STRING",
                    "description": "The specific coding task, prompt, or instruction to delegate to Antigravity (e.g. 'write a python calculator app and save it in the output folder')"
                }
            },
            "required": ["instruction"]
        }
    },
    {
        "name": "predictive_workspace",
        "description": "Proactively stages files, tools, apps, and window layout layouts by analyzing the user's upcoming schedule calendar events and active projects inside the CODING PROJECTS workspace.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "llama_factory",
        "description": "Clones, runs, and controls the LLaMA-Factory open-source fine-tuning toolkit locally.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "clone (clones the LLaMA-Factory repo), webui (launches LLaMA Board UI), train (starts local training job), status (checks training logs/process status)"
                },
                "model_name": {
                    "type": "STRING",
                    "description": "Local model name or path (required for train, e.g. Qwen/Qwen2.5-1.5B-Instruct)"
                },
                "dataset": {
                    "type": "STRING",
                    "description": "Dataset name or file path configured in data/ (required for train)"
                },
                "output_dir": {
                    "type": "STRING",
                    "description": "Directory to save fine-tuned checkpoints (required for train)"
                },
                "finetuning_type": {
                    "type": "STRING",
                    "description": "Fine-tuning strategy: lora (default), full, freeze"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "mythos_sentinel",
        "description": (
            "🧙 THE SAGE — IP Prime's elite cybersecurity oracle and hacker AI. "
            "Powered by The Sage persona: ancient wisdom meets cutting-edge hacking. "
            "LEGACY: audit (code security scan), network_audit (local port scan), threat_model (STRIDE), patch_code (secure auto-patcher), tutor, decode. "
            "ELITE HACKER ARSENAL: "
            "recon (OSINT on domain/IP — WHOIS, subdomains, geolocation, attack surface), "
            "payload_forge (generate XSS/SQLi/CSRF/LFI/RFI/SSRF payloads for CTF/pentesting), "
            "hash_crack (identify hash type MD5/SHA/bcrypt + cracking commands), "
            "web_scan (OWASP Top 10 security headers + vuln scan for a URL), "
            "exploit_suggest (map software+version to CVEs and exploit strategies), "
            "osint_dossier (full OSINT intelligence report on domain/email/username), "
            "blue_team (generate SIEM rules + firewall rules + IDS signatures + YARA rules), "
            "crypto_break (analyze and break ciphers + ciphertext), "
            "network_map (ARP sweep and map local network devices), "
            "shell_craft (generate reverse/bind shell one-liners for pentesting). "
            "SAGE MODE: sage_oracle (ask The Sage any cybersecurity concept for deep wisdom)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "LEGACY: audit | network_audit | threat_model | patch_code | tutor | decode. "
                        "ELITE: recon | payload_forge | hash_crack | web_scan | exploit_suggest | "
                        "osint_dossier | blue_team | crypto_break | network_map | shell_craft. "
                        "SAGE: sage_oracle"
                    )
                },
                "target": {
                    "type": "STRING",
                    "description": "Main target: file/folder path for audit, domain/IP for recon/osint_dossier, URL for web_scan, software name for exploit_suggest, attack type for payload_forge, hash for hash_crack, ciphertext for crypto_break, shell type for shell_craft, architecture for threat_model, code language for patch_code"
                },
                "text": {
                    "type": "STRING",
                    "description": "Text input: vulnerable code for patch_code, ciphertext for crypto_break, question for sage_oracle, threat scenario for blue_team, context for payload_forge"
                },
                "version": {
                    "type": "STRING",
                    "description": "Software version for exploit_suggest"
                },
                "lhost": {
                    "type": "STRING",
                    "description": "Attacker IP for shell_craft (default: 10.10.10.1)"
                },
                "lport": {
                    "type": "STRING",
                    "description": "Listener port for shell_craft (default: 4444)"
                },
                "target_type": {
                    "type": "STRING",
                    "description": "Target type for osint_dossier: domain | email | username | organization"
                },
                "hints": {
                    "type": "STRING",
                    "description": "Optional hints for crypto_break (cipher type hints)"
                },
                "sub_action": {
                    "type": "STRING",
                    "description": "Sub-action for decode: asm_auditor | dependency_auditor | hex | base64 | rot13 | morse | caesar"
                },
                "topic_id": {
                    "type": "STRING",
                    "description": "Topic ID for cybersecurity tutor"
                },
                "quiz_id": {
                    "type": "STRING",
                    "description": "Quiz ID for tutor quiz"
                },
                "user_answer": {
                    "type": "STRING",
                    "description": "User answer for tutor quiz check"
                },
                "file_path": {
                    "type": "STRING",
                    "description": "File path for dependency_auditor or stego_check"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "pentagi_engine",
        "description": (
            "⚡ PENTAGI ENGINE — Real hacking tools. Uses ACTUAL network connections, real TCP port scanning, "
            "real DNS queries, real HTTP requests. Inspired by github.com/vxcontrol/pentagi. "
            "NO simulation — real results. "
            "Actions: "
            "port_scan (real TCP port scanner on any host/IP — finds open ports + banners + vuln hints), "
            "dns_enum (real DNS enumeration + subdomain bruteforce — finds A/MX/NS/TXT records + hidden subdomains), "
            "web_check (real HTTP security check — grabs actual headers, checks for missing security headers, finds sensitive paths), "
            "ssh_audit (real SSH connection — grabs banner + version + checks known CVEs + algorithm weaknesses), "
            "net_discover (real ARP table + ping sweep — finds live hosts on local network with MAC vendor info), "
            "hash_id (real hash type identification — detects MD5/SHA/bcrypt/NTLM + gives exact hashcat modes + john commands). "
            "Use this when user wants REAL scanning/hacking, not AI simulation."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: port_scan | dns_enum | web_check | ssh_audit | net_discover | hash_id"
                },
                "target": {
                    "type": "STRING",
                    "description": "Target: hostname, IP address, URL, or hash value depending on action"
                },
                "port_range": {
                    "type": "STRING",
                    "description": "For port_scan: 'common' (default), 'top100', '1-1000', or '80,443,8080'"
                },
                "port": {
                    "type": "INTEGER",
                    "description": "For ssh_audit: SSH port (default 22)"
                }
            },
            "required": ["action"]
        }
    },

    {
        "name": "mythos_internet",
        "description": (
            "🌐 MYTHOS INTERNET — Live internet access for IP Prime. Like Claude's internet knowledge but REAL-TIME. "
            "Searches live databases, CVEs, exploits, breaches, subdomains. No simulation — actual internet queries. "
            "Use when user wants LIVE/CURRENT information from the internet. "
            "Actions: "
            "cve_search (live CVE lookup from NVD NIST — 'CVE-2021-44228' ya 'log4j' — real current data), "
            "exploit_search (live ExploitDB search — find real public exploits for any software), "
            "web_search (DuckDuckGo live search — any query, security-focused results), "
            "read_url (read any URL/webpage and summarize with AI — articles, docs, writeups), "
            "breach_check (check if email/username in data breaches — HIBP database), "
            "subdomains (live subdomain discovery via crt.sh SSL certificates — real subdomains), "
            "shodan (Shodan IP intelligence — exposed services, banners, vulns — needs API key). "
            "Trigger phrases: 'live search', 'internet pe dhundho', 'CVE dhundho', 'exploit search', "
            "'yeh URL padho', 'breach check karo', 'subdomains dhundho', 'Shodan pe check karo'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: cve_search | exploit_search | web_search | read_url | breach_check | subdomains | shodan"
                },
                "query": {
                    "type": "STRING",
                    "description": "Search query for cve_search, exploit_search, web_search"
                },
                "target": {
                    "type": "STRING",
                    "description": "Target: CVE ID, software name, domain, IP, email, username, URL"
                },
                "url": {
                    "type": "STRING",
                    "description": "Full URL to read for read_url action"
                },
                "domain": {
                    "type": "STRING",
                    "description": "Domain name for subdomains action"
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Max results to return (default 10)"
                }
            },
            "required": ["action"]
        }
    },

    {
        "name": "wifi_security",
        "description": (
            "📡 WiFi SECURITY & DEFENSE AUDIT — Wireless security concepts and defensive auditing tool for IP Prime. "
            "Covers WPA2/WPA3 4-way handshake theory, WEP/WPS historical weaknesses, router hardening checklists, "
            "and allows running a local wireless connection profile audit on Windows. "
            "Actions: "
            "learn (get general theoretical guides on WiFi protocols & weaknesses), "
            "handshake_theory (detailed technical explanation of 4-way handshake), "
            "audit_local (query local active WiFi details like SSID, Auth type, Cipher, Signal quality & evaluate risk), "
            "hardening_guide (checklist to secure home/enterprise router configurations). "
            "Trigger phrases: 'wifi audit', 'wifi handshake kaise kaam karta hai', 'wifi secure kaise karein', 'router configuration checklist'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "Action: learn | handshake_theory | audit_local | hardening_guide"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "image_generator",
        "description": (
            "🎨 AI IMAGE & ART GENERATOR — Generates premium visual art, photos, or graphics using AI. "
            "Supports high-quality models (Flux/SDXL/Ideogram) with a free fallback. "
            "Saves generated files under 'CODING PROJECTS/exports/' and opens them automatically. "
            "Actions: generate. "
            "Trigger phrases: 'generate an image of X', 'create art of Y', 'draw a Z', 'flux model image'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "prompt": {
                    "type": "STRING",
                    "description": "Detailed prompt describing the image you want to generate. E.g., 'A futuristic cybernetic tiger, neon lighting, highly detailed'"
                },
                "aspect_ratio": {
                    "type": "STRING",
                    "description": "Aspect ratio of the generated image. E.g., '1:1', '16:9', '9:16', '4:3', '3:4' (default: '1:1')"
                },
                "provider": {
                    "type": "STRING",
                    "description": "The AI model provider to use. E.g., 'auto' (default), 'ideogram', 'replicate', 'pollinations' (free)"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "coding_workflow",
        "description": (
            "🚀 NEXT-GEN SELF-HEALING CODING WORKFLOW — Runs an elite multi-agent and self-healing software engineering pipeline. "
            "1. Coding: Automatically plans and implements file changes using the IP AI Army. "
            "2. Verification: Executes specified unit test or compiler commands to check compilation. "
            "3. Self-Healing: If verification fails, automatically deploys the Terminal Doctor to diagnose and heal syntax/logical errors. "
            "4. Save & Version Control: If verification passes, stages changes and auto-commits via the Git Assistant with standard conventional commits. "
            "Trigger when Pratik Sir says: run coding workflow, coding pipeline chalao, execute coder workflow, self-healing code workflow."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "instruction": {
                    "type": "STRING",
                    "description": "Natural language instruction of the feature to build or bug to fix (required)"
                },
                "project_path": {
                    "type": "STRING",
                    "description": "Absolute path to the project directory (defaults to current workspace root)"
                },
                "test_command": {
                    "type": "STRING",
                    "description": "Shell command to execute verification tests (e.g. 'pytest tests/' or 'python -m unittest tests/test_chess.py')"
                },
                "auto_commit": {
                    "type": "BOOLEAN",
                    "description": "Automatically stage and perform git commit on successful verification (default: true)"
                }
            },
            "required": ["instruction"]
        }
    },
    {
        "name": "cmd_control",
        "description": (
            "Translates a natural language task into a single Windows PowerShell command and runs it. "
            "Use this for quick terminal tasks that can be done with a single command."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {
                    "type": "STRING",
                    "description": "The natural language instruction of what you want to execute (e.g. 'list all directories', 'kill process 1234')"
                }
            },
            "required": ["task"]
        }
    },
    {
        "name": "youtube_macros",
        "description": "Controls YouTube playback in active browser tab: play_video, pause, mute, volume_up, volume_down, forward, rewind, next, full_screen, theater_mode, subtitle.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "play_video | pause | mute | volume_up | volume_down | forward | rewind | next | full_screen | theater_mode | subtitle"
                },
                "query": {
                    "type": "STRING",
                    "description": "Search query or video title to search and play (required only for play_video)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "notepad_automation",
        "description": "Controls Notepad: open new document, save, search/find, replace, write/type text.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "new_document | save | find | replace | write"
                },
                "text": {
                    "type": "STRING",
                    "description": "Text to write/type in Notepad (required only for write)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "panic_wipe",
        "description": "Instantly force-closes all active web browser and communication windows for privacy lockdown.",
        "parameters": {
            "type": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "usb_monitor",
        "description": "Toggles unauthorized USB port monitoring lockdown.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "enabled": {
                    "type": "BOOLEAN",
                    "description": "Enable (true) or disable (false) USB lockdown monitoring"
                }
            },
            "required": ["enabled"]
        }
    },
    {
        "name": "iot_controller",
        "description": "Controls smart home IoT devices like study lights, ambient shield, and secure gate.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": "toggle | get_state"
                },
                "device": {
                    "type": "STRING",
                    "description": "study_lights | ambient_shield | secure_gate (required only for toggle)"
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "app_shortcuts",
        "description": "Controls standard Windows apps: Calculator, Clock, Paint, Settings, and File Explorer.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "app": {
                    "type": "STRING",
                    "description": "calc | clock | paint | settings | explorer"
                },
                "action": {
                    "type": "STRING",
                    "description": "The specific shortcut/nav action e.g. scientific, standard, timer, alarm, new_canvas, save, wifi, open_downloads, new_folder"
                },
                "path_arg": {
                    "type": "STRING",
                    "description": "Optional directory/folder target string for explorer open action"
                }
            },
            "required": ["app", "action"]
        }
    },
    {
        "name": "web_app_macros",
        "description": "Controls Gmail and Google Drive tabs inside browser utilizing keyboard shortcut macros.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "service": {
                    "type": "STRING",
                    "description": "gmail | drive"
                },
                "action": {
                    "type": "STRING",
                    "description": "gmail actions: compose, search, inbox, sent, starred, drafts, refresh; drive actions: new_doc, new_sheet, new_folder, search, recent"
                }
            },
            "required": ["service", "action"]
        }
    },
    {
        "name": "whatsapp_automation",
        "description": "Pre-fills and sends a message to a contact name or phone number on WhatsApp Web in Chrome.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target": {
                    "type": "STRING",
                    "description": "Contact name or phone number"
                },
                "message": {
                    "type": "STRING",
                    "description": "Message to send"
                }
            },
            "required": ["target", "message"]
        }
    },
    {
        "name": "realtime_knowledge",
        "description": "Queries Tavily / Google News RSS / Wikipedia for real-time information, news, or general knowledge.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {
                    "type": "STRING",
                    "description": "Search query or question"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "automate_multitasking",
        "description": (
            "Controls Windows workspace multitasking — snap windows, manage virtual desktops, "
            "minimize/restore all, task view, and alt-tab. "
            "Use when the user says 'snap left', 'new desktop', 'show desktop', 'minimize all', "
            "'task view', 'switch app', 'maximize window', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {
                    "type": "STRING",
                    "description": (
                        "Multitasking action. Examples: 'minimize all', 'restore all', "
                        "'snap left', 'snap right', 'maximize window', 'minimize window', "
                        "'new desktop', 'next desktop', 'previous desktop', 'close desktop', "
                        "'task view', 'switch app'"
                    )
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "automate_browser",
        "description": (
            "Executes keyboard shortcut automations inside Chrome or Firefox. "
            "Use when the user says 'open new tab in chrome', 'close tab in firefox', "
            "'refresh chrome', 'go incognito', 'open devtools', 'scroll down in chrome', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "browser": {
                    "type": "STRING",
                    "description": "Browser name: 'chrome' or 'firefox'"
                },
                "action": {
                    "type": "STRING",
                    "description": (
                        "Action to perform. Examples: 'new tab', 'close tab', 'next tab', "
                        "'prev tab', 'refresh', 'hard refresh', 'zoom in', 'zoom out', "
                        "'fullscreen', 'incognito', 'history', 'downloads', 'developer tools', "
                        "'scroll down', 'scroll up', 'back', 'forward', 'address bar'"
                    )
                }
            },
            "required": ["browser", "action"]
        }
    },
    {
        "name": "switch_app",
        "description": (
            "Switches focus to an already-open application window using robust Win32 APIs. "
            "Use when the user says 'switch to chrome', 'bring up spotify', 'focus vscode', "
            "'open discord window', 'switch to notepad', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {
                    "type": "STRING",
                    "description": (
                        "Name of the application to focus. Examples: 'chrome', 'vscode', "
                        "'spotify', 'discord', 'notepad', 'whatsapp', 'explorer', 'terminal'"
                    )
                }
            },
            "required": ["name"]
        }
    },
    {
        "name": "run_system_maintenance",
        "description": (
            "Runs a system maintenance sweep — clears TEMP directories, old log files, "
            "and cache files. Reports how many MB were freed. "
            "Use when the user says 'run maintenance', 'clean temp files', 'clear cache', "
            "'optimize system', 'free up space', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "toggle_sandbox",
        "description": (
            "Toggles network sandbox mode. When enabled, kills all established external network "
            "connections (except local). Useful for privacy lockdown. "
            "Use when the user says 'enable network sandbox', 'isolate network', "
            "'kill all connections', 'disable sandbox', 'deactivate network shield', etc."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "enabled": {
                    "type": "BOOLEAN",
                    "description": "true to enable sandbox (kill connections), false to disable"
                }
            },
            "required": ["enabled"]
        }
    },

    # ── SAT Batch 4 — 39 New Tools ──────────────────────────────────────────

    {
        "name": "deep_research",
        "description": (
            "JARVIS-class deep research engine. Searches multiple sources (DuckDuckGo, Tavily, Wikipedia) "
            "and synthesizes a comprehensive Markdown report. "
            "Use when user says 'deep research on X', 'research topic Y', 'find everything about Z', "
            "'make a report on X', 'study this topic for me'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Research topic or question"},
                "depth": {"type": "STRING", "description": "Research depth: 'quick', 'standard', 'deep' (default: standard)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "document_generator",
        "description": (
            "Generates professional documents — PDF, Markdown, or TXT — with styled headers, sections, and bullet points. "
            "Use when user says 'generate a PDF', 'create a document', 'write a report as PDF', "
            "'make a professional document about X'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "content": {"type": "STRING", "description": "Document content or topic to generate"},
                "format": {"type": "STRING", "description": "Output format: 'pdf', 'markdown', 'txt' (default: pdf)"},
                "title": {"type": "STRING", "description": "Document title"}
            },
            "required": ["content"]
        }
    },
    {
        "name": "email_reader",
        "description": (
            "Reads emails from Gmail inbox via IMAP. Lists recent emails or reads a specific email. "
            "Use when user says 'check my emails', 'read my inbox', 'show latest emails', 'read email from X'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'list' to show inbox, 'read' to read specific email"},
                "count": {"type": "INTEGER", "description": "Number of emails to fetch (default: 5)"},
                "search": {"type": "STRING", "description": "Search term to filter emails"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "email_sender",
        "description": (
            "Sends emails via Gmail SMTP. "
            "Use when user says 'send an email to X', 'email Y saying Z', 'compose and send email'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "to": {"type": "STRING", "description": "Recipient email address"},
                "subject": {"type": "STRING", "description": "Email subject"},
                "body": {"type": "STRING", "description": "Email body content"}
            },
            "required": ["to", "subject", "body"]
        }
    },
    {
        "name": "notion_tool",
        "description": (
            "Controls Notion workspace — list pages, create new pages, search content. "
            "Use when user says 'open Notion', 'create a Notion page about X', 'list my Notion pages', 'search Notion for Y'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'list', 'create', 'search'"},
                "title": {"type": "STRING", "description": "Page title (for create)"},
                "content": {"type": "STRING", "description": "Page content (for create)"},
                "query": {"type": "STRING", "description": "Search query (for search)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "google_drive_tool",
        "description": (
            "Access Google Drive — list files, upload, download, search. "
            "Use when user says 'show my Drive files', 'upload X to Drive', 'download Y from Drive', 'search Drive for Z'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'list', 'upload', 'download', 'search'"},
                "query": {"type": "STRING", "description": "Search term or file name"},
                "file_path": {"type": "STRING", "description": "Local file path for upload"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "huggingface_tool",
        "description": (
            "Access HuggingFace — run inference on models, search models/datasets. "
            "Use when user says 'run X model on HuggingFace', 'search HuggingFace for Y', 'inference with HF model'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'inference', 'search_models', 'search_datasets'"},
                "model": {"type": "STRING", "description": "HuggingFace model ID"},
                "input": {"type": "STRING", "description": "Input text for inference"},
                "query": {"type": "STRING", "description": "Search query"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "security_auditor",
        "description": (
            "Scans code files or directories for security vulnerabilities — SQL injection, XSS, hardcoded secrets, insecure packages. "
            "Use when user says 'audit my code', 'scan for security issues', 'check for vulnerabilities in X', 'security scan'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'scan_secrets', 'vuln_check', 'system_security', 'deep_audit', 'audit_packages'"},
                "target": {"type": "STRING", "description": "File or directory path to audit"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "study_mode",
        "description": (
            "Interactive study/quiz session on any topic. Saturday asks questions and evaluates answers. "
            "Use when user says 'quiz me on X', 'study mode for Y', 'test my knowledge on Z', 'start a quiz'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'start', 'answer', 'skip', 'end', 'history'"},
                "topic": {"type": "STRING", "description": "Topic to study (for start)"},
                "answer": {"type": "STRING", "description": "User's answer to the current question"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "game_mode",
        "description": (
            "Activates/deactivates game mode — minimizes UI overhead, disables notifications, optimizes performance when gaming. "
            "Use when user says 'game mode on', 'I'm gaming', 'enable game mode', 'disable game mode', 'exit game mode'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'on' to enable, 'off' to disable, 'status' to check"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "goals_tracker",
        "description": (
            "Track long-term goals with AI coaching. Set goals, mark progress, review status. "
            "Use when user says 'add a goal', 'track my goal', 'show my goals', 'I completed goal X', 'review my goals'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'add', 'list', 'complete', 'delete', 'progress', 'coach'"},
                "goal": {"type": "STRING", "description": "Goal description (for add)"},
                "goal_id": {"type": "STRING", "description": "Goal ID (for complete/delete/progress)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "project_memory",
        "description": (
            "Per-project memory context — store and recall facts specific to a project without mixing with others. "
            "Use when user says 'remember for project X', 'what do you know about project Y', 'store this for my current project'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'store', 'recall', 'list_projects', 'clear'"},
                "project": {"type": "STRING", "description": "Project name"},
                "fact": {"type": "STRING", "description": "Fact or info to store"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "project_setup",
        "description": (
            "Bootstraps a new coding project — creates folder structure, venv, git init, README. "
            "Use when user says 'setup a new project', 'create project X', 'initialize new Python project', 'bootstrap my project'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "project_name": {"type": "STRING", "description": "Name of the project"},
                "language": {"type": "STRING", "description": "Programming language (python, node, etc.)"},
                "path": {"type": "STRING", "description": "Where to create the project (optional)"}
            },
            "required": ["project_name"]
        }
    },
    {
        "name": "plugin_creator",
        "description": (
            "Creates and registers a new tool plugin at runtime — no restart needed. "
            "Use when user says 'create a new tool', 'make a plugin for X', 'build me a new action module'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING", "description": "Plugin/tool name"},
                "description": {"type": "STRING", "description": "What the plugin should do"},
                "code_hint": {"type": "STRING", "description": "Optional code snippet or logic hint"}
            },
            "required": ["name", "description"]
        }
    },
    {
        "name": "error_detective",
        "description": (
            "Analyzes error messages, stack traces, and exceptions to identify root cause and suggest fixes. "
            "Use when user says 'what does this error mean', 'fix this error', 'debug this exception', 'analyze this stack trace'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "error": {"type": "STRING", "description": "Error message or stack trace to analyze"},
                "context": {"type": "STRING", "description": "Additional context about what was being done"}
            },
            "required": ["error"]
        }
    },
    {
        "name": "explorer_control",
        "description": (
            "Controls Windows File Explorer — open folders, navigate, create directories. "
            "Use when user says 'open this folder in Explorer', 'navigate to X in Explorer', 'go to Downloads in Explorer'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'open', 'navigate', 'get_active', 'new_folder'"},
                "path": {"type": "STRING", "description": "Folder path to open or navigate to"},
                "folder_name": {"type": "STRING", "description": "New folder name (for new_folder)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "export_conversation",
        "description": (
            "Exports the current conversation/chat session to PDF or TXT file. "
            "Use when user says 'save this conversation', 'export our chat', 'save chat as PDF', 'export session'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "format": {"type": "STRING", "description": "Export format: 'pdf' or 'txt' (default: txt)"},
                "filename": {"type": "STRING", "description": "Output filename (optional)"}
            },
            "required": []
        }
    },
    {
        "name": "focus_mode",
        "description": (
            "Focus mode — blocks distracting websites, sets Do Not Disturb, optionally starts Pomodoro timer. "
            "Use when user says 'focus mode on', 'block distractions', 'start focus session', 'unblock sites', 'stop focus mode'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'start', 'stop', 'block', 'unblock', 'status'"},
                "duration": {"type": "INTEGER", "description": "Focus session duration in minutes (default: 25)"},
                "sites": {"type": "STRING", "description": "Comma-separated sites to block (optional)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "git_copilot",
        "description": (
            "AI-powered Git assistant — AI-generated commit messages, smart push/pull, branch management. "
            "Use when user says 'git commit', 'generate commit message', 'push my changes', 'git status with AI', 'create branch X'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'status', 'commit', 'push', 'pull', 'branch', 'log', 'diff'"},
                "message": {"type": "STRING", "description": "Commit message (optional — AI generates if not provided)"},
                "branch": {"type": "STRING", "description": "Branch name (for branch action)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "github_tool",
        "description": (
            "GitHub API integration — search repos, list issues, check PRs, view repo info. "
            "Use when user says 'search GitHub for X', 'show issues in repo Y', 'list my GitHub repos', 'check PRs'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'search_repos', 'list_issues', 'list_prs', 'repo_info', 'my_repos'"},
                "query": {"type": "STRING", "description": "Search query or repo name"},
                "repo": {"type": "STRING", "description": "Repository (owner/repo format)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "github_action",
        "description": (
            "Trigger GitHub Actions, manage workflows, view run status. "
            "Use when user says 'trigger GitHub action', 'run workflow X', 'check GitHub CI status'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'trigger', 'list_runs', 'cancel_run', 'list_workflows'"},
                "repo": {"type": "STRING", "description": "Repository (owner/repo)"},
                "workflow": {"type": "STRING", "description": "Workflow file name or ID"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "hacker_tools",
        "description": (
            "Network and security utilities — port scan, base64 encode/decode, hash identify, password audit, file encryption. "
            "Use when user says 'scan ports on X', 'encode this in base64', 'what hash is this', 'encrypt this file'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'port_scan', 'encode', 'decode', 'hash_identify', 'password_audit', 'file_crypt'"},
                "target": {"type": "STRING", "description": "IP, text, or file path"},
                "key": {"type": "STRING", "description": "Encryption key (for file_crypt)"}
            },
            "required": ["action", "target"]
        }
    },
    {
        "name": "local_ingester",
        "description": (
            "Ingests local files (PDF, TXT, code) into a ChromaDB vector database for RAG memory. "
            "Use when user says 'index this file', 'add this PDF to memory', 'ingest my documents', 'remember this file'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "path": {"type": "STRING", "description": "File or folder path to ingest"},
                "collection": {"type": "STRING", "description": "Vector DB collection name (default: 'prime_kb')"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "local_search",
        "description": (
            "Semantic search across locally indexed files and documents. "
            "Use when user says 'search my documents for X', 'find in my local files', 'semantic search for Y in my notes'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"},
                "collection": {"type": "STRING", "description": "Collection to search (default: 'prime_kb')"},
                "top_k": {"type": "INTEGER", "description": "Number of results (default: 5)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "music_control",
        "description": (
            "System media controls — play, pause, next, previous, volume. "
            "Use when user says 'play music', 'pause', 'next song', 'previous track', 'mute', 'volume up/down'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'play', 'pause', 'next', 'previous', 'mute', 'volume_up', 'volume_down'"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "obsidian_organizer",
        "description": (
            "Obsidian vault organizer — index notes, auto-categorize by topic, generate summaries. "
            "Use when user says 'organize my Obsidian vault', 'categorize my notes', 'summarize Obsidian notes', 'index vault'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'index', 'categorize', 'summarize', 'search'"},
                "vault_path": {"type": "STRING", "description": "Path to Obsidian vault (optional)"},
                "query": {"type": "STRING", "description": "Search query (for search action)"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "auto_code_explainer",
        "description": (
            "Captures the active window screen and automatically explains the visible code. "
            "Use when user says 'explain this code', 'what does this code do', 'explain what I see on screen', 'read this code'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "detail": {"type": "STRING", "description": "Level of detail: 'brief', 'detailed' (default: detailed)"}
            },
            "required": []
        }
    },
    {
        "name": "auto_code_helper",
        "description": (
            "Real-time code assistant — provides suggestions, completions, and refactoring hints based on visible code. "
            "Use when user says 'help me with this code', 'suggest improvements', 'how can I improve this', 'code hints'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "task": {"type": "STRING", "description": "What kind of help needed: 'suggest', 'complete', 'refactor', 'document'"},
                "code": {"type": "STRING", "description": "Code snippet (optional — captures from screen if not provided)"}
            },
            "required": []
        }
    },
    {
        "name": "voice_to_code",
        "description": (
            "Converts voice dictation directly into typed code in the active IDE/editor. "
            "Use when user says 'type this code for me', 'write code by voice', 'dictate code', 'type what I say as code'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "code": {"type": "STRING", "description": "Code to type into the active editor"},
                "language": {"type": "STRING", "description": "Programming language hint (optional)"}
            },
            "required": ["code"]
        }
    },
    {
        "name": "content_creator",
        "description": (
            "AI content creation — blog posts, social media captions, YouTube scripts, ad copy. "
            "Use when user says 'write a blog post about X', 'create social media caption for Y', 'make YouTube script', 'write ad copy'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "type": {"type": "STRING", "description": "'blog', 'social', 'youtube', 'ad', 'email_newsletter', 'thread'"},
                "topic": {"type": "STRING", "description": "Content topic"},
                "tone": {"type": "STRING", "description": "Tone: 'professional', 'casual', 'funny', 'inspirational'"},
                "length": {"type": "STRING", "description": "Length: 'short', 'medium', 'long'"}
            },
            "required": ["type", "topic"]
        }
    },
    {
        "name": "browser_agent",
        "description": (
            "Playwright headless browser agent — automates websites, fills forms, extracts data, takes screenshots. "
            "Use when user says 'open this website and do X', 'fill this form', 'extract data from URL', 'automate browser task'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'open', 'click', 'type', 'extract', 'screenshot', 'scroll'"},
                "url": {"type": "STRING", "description": "URL to navigate to"},
                "selector": {"type": "STRING", "description": "CSS selector for element"},
                "text": {"type": "STRING", "description": "Text to type"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "calendar_tool",
        "description": (
            "Google Calendar integration — add and list events. "
            "Use when user says 'add event to calendar', 'schedule X on date Y', 'what events do I have', 'show calendar'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'list', 'create'"},
                "title": {"type": "STRING", "description": "Event title (for create)"},
                "date": {"type": "STRING", "description": "Event date/time (for create)"},
                "duration": {"type": "INTEGER", "description": "Duration in minutes"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "scheduled_task",
        "description": (
            "Schedule tasks using Windows Task Scheduler. "
            "Use when user says 'schedule this task', 'run X every day at Y time', 'create scheduled task', 'set up recurring task'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "'create', 'list', 'delete', 'run'"},
                "task_name": {"type": "STRING", "description": "Task name"},
                "command": {"type": "STRING", "description": "Command to run"},
                "schedule": {"type": "STRING", "description": "Schedule: 'daily', 'weekly', 'once', time like '09:00'"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "system_monitor",
        "description": (
            "Quick system stats — CPU, RAM, disk, battery, temperature. "
            "Use when user says 'system stats', 'how is my CPU', 'RAM usage', 'battery level', 'system health'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "metric": {"type": "STRING", "description": "'all', 'cpu', 'ram', 'disk', 'battery', 'temperature'"}
            },
            "required": []
        }
    },
    {
        "name": "translate_text",
        "description": (
            "Translates text between languages using Gemini AI. "
            "Use when user says 'translate this to X', 'what is Y in Z language', 'translate: <text>'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "text": {"type": "STRING", "description": "Text to translate"},
                "target_language": {"type": "STRING", "description": "Target language (e.g. 'Hindi', 'French', 'Spanish')"},
                "source_language": {"type": "STRING", "description": "Source language (optional — auto-detected)"}
            },
            "required": ["text", "target_language"]
        }
    },
    {
        "name": "query_visual_timeline",
        "description": (
            "Queries the visual timeline (screen history) to find what was on screen at a given time. "
            "Use when user says 'what was I doing an hour ago', 'show screen history', 'what was on my screen earlier', 'find in my screen history'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "What to search for in screen history"},
                "time_ago": {"type": "STRING", "description": "Time range like '1 hour', '30 minutes', 'today'"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "quick_briefing",
        "description": (
            "Generates a quick morning/evening briefing with weather, news, and tasks. "
            "Use when user says 'give me a briefing', 'morning briefing', 'quick summary of today', 'what should I know today'."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "type": {"type": "STRING", "description": "'morning', 'evening', 'quick' (default: quick)"}
            },
            "required": []
        }
    },
    {
        "name": "web_search_quick",
        "description": (
            "Fast web search via Tavily API — returns quick results without deep synthesis. "
            "Use when user says 'quick search for X', 'fast lookup Y', 'search the web for Z' (for deeper research use deep_research)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "query": {"type": "STRING", "description": "Search query"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "autonomy_engine",
        "description": (
            "Manages IP Prime's autonomous goal queue. Use when the user wants to "
            "give Prime a standing objective to work on in the background, check "
            "what it's working on, or approve/reject an action it's waiting on."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description":
                    "add_goal | list_goals | pending_confirmations | approve | reject | set_level"},
                "description": {"type": "STRING", "description": "Goal text (for add_goal)"},
                "priority": {"type": "STRING", "description": "low | normal | high"},
                "confirmation_id": {"type": "STRING", "description": "ID from pending_confirmations"},
                "reason": {"type": "STRING", "description": "Why you're rejecting an action"},
                "level": {"type": "STRING", "description": "off | supervised | trusted"}
            },
            "required": ["action"]
        }
    },
    {
        "name": "macro_automation",
        "description": (
            "Executes custom system GUI macro sequences including mouse clicks, typing, and key strokes. "
            "Use when user wants to automate GUI sequences, click buttons, type text on screen, or run hotkey combinations."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "sequence": {
                    "type": "ARRAY",
                    "description": "List of sequence steps: move_to, click, type, hotkey, delay",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "action": {"type": "STRING", "description": "move_to | click | type | hotkey | delay"},
                            "x": {"type": "INTEGER", "description": "X coordinate for move_to"},
                            "y": {"type": "INTEGER", "description": "Y coordinate for move_to"},
                            "text": {"type": "STRING", "description": "Text to type"},
                            "keys": {
                                "type": "ARRAY",
                                "description": "Keys for hotkey action",
                                "items": {"type": "STRING"}
                            },
                            "seconds": {"type": "NUMBER", "description": "Seconds to wait for delay action"}
                        },
                        "required": ["action"]
                    }
                }
            },
            "required": ["sequence"]
        }
    },
    {
        "name": "web_scraper",
        "description": (
            "Fetches a web page and extracts structured elements (text blocks, tables, lists) "
            "based on natural language instructions using Gemini AI."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "url": {"type": "STRING", "description": "Target website URL to scrape"},
                "instruction": {"type": "STRING", "description": "Specific information extraction instruction"}
            },
            "required": ["url"]
        }
    },
    {
        "name": "boss_orchestrator",
        "description": (
            "Chains sequential tool calls dynamically to execute multi-step cross-domain instructions."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "command": {"type": "STRING", "description": "High-level orchestration request"}
            },
            "required": ["command"]
        }
    },
    {
        "name": "asset_scaffolder",
        "description": (
            "Generates HTML/CSS layout templates or extracts styling parameters and tokens from design scripts."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "generate_layout | extract_styling"},
                "target": {"type": "STRING", "description": "Prompt description or CSS/HTML script block"}
            },
            "required": ["target"]
        }
    },
    {
        "name": "connector_jobs",
        "description": "Hyper-local job listing platform. Search for jobs or post new jobs to match local skills with opportunity.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "action": {"type": "STRING", "description": "Action: 'search' (default) or 'post'"},
                "query": {"type": "STRING", "description": "Keywords, title, or skills to search for"},
                "location": {"type": "STRING", "description": "Local city or region"},
                "job_details": {
                    "type": "OBJECT",
                    "description": "Required when action is 'post'. Details of the job.",
                    "properties": {
                        "title": {"type": "STRING", "description": "Title of the job"},
                        "employer": {"type": "STRING", "description": "Company or business name"},
                        "location": {"type": "STRING", "description": "Job location"},
                        "type": {"type": "STRING", "description": "Full-Time, Part-Time, Internship, etc."},
                        "skills": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of required skills"},
                        "description": {"type": "STRING", "description": "Brief description of role"}
                    },
                    "required": ["title"]
                }
            },
            "required": []
        }
    }
]
