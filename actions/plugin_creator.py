# actions/plugin_creator.py
import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("saturday.plugin_creator")

BASE_DIR = Path(__file__).resolve().parent.parent
CUSTOM_TOOLS_PATH = BASE_DIR / "config" / "custom_tools.json"

def plugin_creator(parameters: dict, player=None, speak=None) -> str:
    tool_name = parameters.get("tool_name", "").strip()
    description = parameters.get("description", "").strip()
    code = parameters.get("code", "").strip()
    parameter_schema = parameters.get("parameter_schema", {})

    if not tool_name or not code:
        return "Error: Both tool_name and code must be specified."

    # Keep tool names lowercase and alphanumeric
    tool_name = "".join(c for c in tool_name if c.isalnum() or c == "_").lower()
    
    # 1. Save Python code to actions/
    action_path = BASE_DIR / "actions" / f"{tool_name}.py"
    try:
        # Wrap the function if it doesn't already have the entry point signature
        if f"def {tool_name}" not in code:
            # Indent the user's code block
            indented_code = "\n".join("    " + line for line in code.splitlines())
            code = f"""# Custom dynamically created tool
import logging

logger = logging.getLogger("saturday.{tool_name}")

def {tool_name}(parameters: dict, player=None, speak=None) -> str:
{indented_code}
"""
        action_path.write_text(code, encoding="utf-8")
        logger.info("Custom action written to %s", action_path)
    except Exception as e:
        return f"Error: Failed to write action script: {e}"

    # 2. Save schema to custom_tools.json
    try:
        custom_tools = {}
        if CUSTOM_TOOLS_PATH.exists():
            try:
                custom_tools = json.loads(CUSTOM_TOOLS_PATH.read_text(encoding="utf-8"))
            except Exception:
                custom_tools = {}

        # Construct declaration schema for Gemini
        schema = {
            "name": tool_name,
            "description": description or f"Custom Saturday tool: {tool_name}",
            "parameters": parameter_schema or {
                "type": "OBJECT",
                "properties": {},
                "required": []
            }
        }
        custom_tools[tool_name] = schema
        
        CUSTOM_TOOLS_PATH.parent.mkdir(parents=True, exist_ok=True)
        CUSTOM_TOOLS_PATH.write_text(json.dumps(custom_tools, indent=4), encoding="utf-8")
        logger.info("Custom tool schema registered: %s", tool_name)
    except Exception as e:
        return f"Error: Failed to register schema in custom_tools.json: {e}"

    msg = f"Successfully created and registered dynamic tool '{tool_name}'."
    if speak:
        speak(f"सर, मैंने नया टूल {tool_name} बना दिया है।")
    return msg
