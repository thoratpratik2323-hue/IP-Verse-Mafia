import json
import re
import sys
from pathlib import Path

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
DYNAMIC_DIR = BASE_DIR / "actions" / "dynamic"

def create_new_skill(parameters: dict, player=None, speak=None) -> str:
    name = parameters.get("name", "").strip()
    description = parameters.get("description", "").strip()
    params_schema = parameters.get("parameters", {})
    python_code = parameters.get("python_code", "").strip()
    
    if not name:
        return "Error: Skill name is required."
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", name):
        return f"Error: Skill name '{name}' is invalid. Must be alphanumeric and start with a letter or underscore."
    if not description:
        return "Error: Skill description is required."
    if not python_code:
        return "Error: Python code is required."
        
    # Syntax check
    try:
        compile(python_code, f"<dynamic_skill_{name}>", "exec")
    except SyntaxError as e:
        return f"Error: Syntax error in python_code: {e}"
        
    # Ensure dynamic directory exists
    DYNAMIC_DIR.mkdir(parents=True, exist_ok=True)
    
    # Paths
    py_path = DYNAMIC_DIR / f"{name}.py"
    json_path = DYNAMIC_DIR / f"{name}.json"
    
    try:
        py_path.write_text(python_code, encoding="utf-8")
        
        metadata = {
            "name": name,
            "description": description,
            "parameters": params_schema
        }
        json_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        
        msg = f"Successfully created and registered dynamic skill '{name}', sir."
        if speak:
            speak(msg)
            
        print(f"[Skills] Created dynamic skill: {name}")
        return f"Success: Dynamic skill '{name}' registered. Description: {description}"
    except Exception as e:
        return f"Error: Failed to write skill files: {e}"
