import importlib
import json
import sys
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
DYNAMIC_DIR = BASE_DIR / "actions" / "dynamic"

# Core/standard built-in tools of IP Prime
CORE_TOOLS = {
    "open_app": {
        "description": "Launch an application by its name.",
        "parameters": {
            "app_name": "string (required)"
        },
        "module": "actions.open_app",
        "func": "open_app",
        "pass_speak": False
    },
    "web_search": {
        "description": "Use web search for information retrieval, research, or current data.",
        "parameters": {
            "query": "string (required) - write a clear, focused search query",
            "mode": "\"search\" or \"compare\" (optional, default: search)",
            "items": "list of strings (optional, for compare mode)",
            "aspect": "string (optional, for compare mode)"
        },
        "module": "actions.web_search",
        "func": "web_search",
        "pass_speak": False
    },
    "game_updater": {
        "description": "Manage game downloads, installs, updates, status or scheduling for Steam and Epic Platforms.",
        "parameters": {
            "action": "\"update\" | \"install\" | \"list\" | \"download_status\" | \"schedule\" (required)",
            "platform": "\"steam\" | \"epic\" | \"both\" (optional, default: both)",
            "game_name": "string (optional)",
            "app_id": "string (optional)",
            "shutdown_when_done": "boolean (optional)"
        },
        "module": "actions.game_updater",
        "func": "game_updater",
        "pass_speak": True
    },
    "browser_control": {
        "description": "Control the web browser directly.",
        "parameters": {
            "action": "\"go_to\" | \"search\" | \"click\" | \"type\" | \"scroll\" | \"get_text\" | \"press\" | \"close\" (required)",
            "url": "string (for go_to)",
            "query": "string (for search)",
            "text": "string (for click/type)",
            "direction": "\"up\" | \"down\" (for scroll)"
        },
        "module": "actions.browser_control",
        "func": "browser_control",
        "pass_speak": False
    },
    "file_controller": {
        "description": "Save content to disk, create, read, list, delete, move, copy, or find files. Use \"desktop\" for Desktop folder.",
        "parameters": {
            "action": "\"write\" | \"create_file\" | \"read\" | \"list\" | \"delete\" | \"move\" | \"copy\" | \"find\" | \"disk_usage\" (required)",
            "path": "string - use \"desktop\" for Desktop folder",
            "name": "string - filename",
            "content": "string - file content (for write/create_file)"
        },
        "module": "actions.file_controller",
        "func": "file_controller",
        "pass_speak": False
    },
    "computer_settings": {
        "description": "Change computer system settings.",
        "parameters": {
            "action": "string (required)",
            "description": "string - natural language description",
            "value": "string (optional)"
        },
        "module": "actions.computer_settings",
        "func": "computer_settings",
        "pass_speak": False
    },
    "computer_control": {
        "description": "Simulate mouse/keyboard actions (click, type, scroll, key press, screenshots).",
        "parameters": {
            "action": "\"type\" | \"click\" | \"hotkey\" | \"press\" | \"scroll\" | \"screenshot\" | \"screen_find\" | \"screen_click\" (required)",
            "text": "string (for type)",
            "x, y": "int (for click)",
            "keys": "string (for hotkey, e.g. \"ctrl+c\")",
            "key": "string (for press)",
            "direction": "\"up\" | \"down\" (for scroll)",
            "description": "string (for screen_find/screen_click)"
        },
        "module": "actions.computer_control",
        "func": "computer_control",
        "pass_speak": False
    },
    "screen_process": {
        "description": "Analyze or ask questions about what is currently shown on the screen or camera.",
        "parameters": {
            "text": "string (required) - what to analyze or ask about the screen",
            "angle": "\"screen\" | \"camera\" (optional)"
        },
        "module": "actions.screen_processor",
        "func": "screen_process",
        "pass_speak": False
    },
    "send_message": {
        "description": "Send WhatsApp messages to contacts.",
        "parameters": {
            "receiver": "string (required)",
            "message_text": "string (required)",
            "platform": "string (required)"
        },
        "module": "actions.send_message",
        "func": "send_message",
        "pass_speak": False
    },
    "reminder": {
        "description": "Set calendar reminders.",
        "parameters": {
            "date": "string YYYY-MM-DD (required)",
            "time": "string HH:MM (required)",
            "message": "string (required)"
        },
        "module": "actions.reminder",
        "func": "reminder",
        "pass_speak": False
    },
    "desktop_control": {
        "description": "Control desktop settings, organize desktop folders, wallpapers, clean files.",
        "parameters": {
            "action": "\"wallpaper\" | \"organize\" | \"clean\" | \"list\" | \"task\" (required)",
            "path": "string (optional)",
            "task": "string (optional)"
        },
        "module": "actions.desktop",
        "func": "desktop_control",
        "pass_speak": False
    },
    "youtube_video": {
        "description": "Search, play, or summarize YouTube videos.",
        "parameters": {
            "action": "\"play\" | \"summarize\" | \"trending\" (required)",
            "query": "string (for play)"
        },
        "module": "actions.youtube_video",
        "func": "youtube_video",
        "pass_speak": False
    },
    "weather_report": {
        "description": "Get current weather and forecasts for a city.",
        "parameters": {
            "city": "string (required)"
        },
        "module": "actions.weather_report",
        "func": "weather_action",
        "pass_speak": False
    },
    "flight_finder": {
        "description": "Search flights between cities on a date.",
        "parameters": {
            "origin": "string (required)",
            "destination": "string (required)",
            "date": "string (required)"
        },
        "module": "actions.flight_finder",
        "func": "flight_finder",
        "pass_speak": True
    },
    "code_helper": {
        "description": "Write, edit, explain, or run programming code snippets.",
        "parameters": {
            "action": "\"write\" | \"edit\" | \"run\" | \"explain\" (required)",
            "description": "string (required)",
            "language": "string (optional)",
            "output_path": "string (optional)",
            "file_path": "string (optional)"
        },
        "module": "actions.code_helper",
        "func": "code_helper",
        "pass_speak": True
    },
    "dev_agent": {
        "description": "Run an autonomous programmer agent for complex software tasks.",
        "parameters": {
            "description": "string (required)",
            "language": "string (optional)"
        },
        "module": "actions.dev_agent",
        "func": "dev_agent",
        "pass_speak": True
    },
    "create_new_skill": {
        "description": "Create a brand new Python action tool to expand IP Prime's capabilities. Use this when the user requests a custom task that cannot be completed by standard tools.",
        "parameters": {
            "name": "string (required) - alphanumeric with underscores only, e.g. 'calculate_tax'",
            "description": "string (required) - clear, detailed description of what the tool accomplishes",
            "parameters": "object (required) - parameter names mapped to their types and descriptions, e.g. {'amount': 'float (required)'}",
            "python_code": "string (required) - complete, working Python code implementing 'def [name](parameters: dict, player=None, speak=None) -> str:'"
        },
        "module": "actions.create_new_skill",
        "func": "create_new_skill",
        "pass_speak": True
    },
    "file_processor": {
        "description": "Process, index, or search inside any file. Supports: pdf, docx, txt, csv, xlsx, json, xml, code, images, audio, video, zip, pptx.",
        "parameters": {
            "file_path": "string (required) - Full path to the file on disk",
            "action": "string (required) - Action to perform: 'index' (creates smart local index in memory), 'search_index' (searches index for a query), or other file-type specific actions like 'summarize', 'extract_text', 'run', 'explain'",
            "instruction": "string (optional) - Free-form instruction or search query if action is search_index",
            "query": "string (optional) - Alternate field for search query"
        },
        "module": "actions.file_processor",
        "func": "file_processor",
        "pass_speak": True
    }
}

def scan_dynamic_tools() -> dict:
    dynamic_tools = {}
    if not DYNAMIC_DIR.exists():
        return dynamic_tools
    
    for json_file in DYNAMIC_DIR.glob("*.json"):
        try:
            name = json_file.stem
            py_file = DYNAMIC_DIR / f"{name}.py"
            if py_file.exists():
                schema = json.loads(json_file.read_text(encoding="utf-8"))
                dynamic_tools[name] = {
                    "description": schema.get("description", "Dynamic custom tool."),
                    "parameters": schema.get("parameters", {}),
                    "module": f"actions.dynamic.{name}",
                    "func": name,
                    "pass_speak": True
                }
        except Exception as e:
            print(f"[Skills] [Error] Failed to scan dynamic tool {json_file.name}: {e}")
    return dynamic_tools

def get_all_tools() -> dict:
    tools = {}
    tools.update(CORE_TOOLS)
    tools.update(scan_dynamic_tools())
    return tools

def format_tools_for_prompt() -> str:
    tools = get_all_tools()
    lines = []
    for name, info in tools.items():
        lines.append(name)
        for param, desc in info.get("parameters", {}).items():
            lines.append(f"  {param}: {desc}")
        lines.append("")
    return "\n".join(lines)

def execute_tool_action(name: str, parameters: dict, speak=None) -> str:
    tools = get_all_tools()
    if name not in tools:
        raise ValueError(f"Unknown tool '{name}'")
    
    info = tools[name]
    module_path = info["module"]
    func_name = info["func"]
    
    # Import the module dynamically
    try:
        module = importlib.import_module(module_path)
        func = getattr(module, func_name)
    except Exception as e:
        raise RuntimeError(f"Failed to load module/function for tool '{name}': {e}")
    
    # Execute with correct parameters
    try:
        # Check if we should pass speak parameter
        if info.get("pass_speak", False):
            res = func(parameters=parameters, player=None, speak=speak)
        else:
            res = func(parameters=parameters, player=None)
        return res or "Done."
    except Exception as e:
        raise RuntimeError(f"Error executing tool '{name}': {e}")
