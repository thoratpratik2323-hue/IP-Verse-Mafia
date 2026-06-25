import logging
import json
from pathlib import Path
from memory.encryption import encrypt_string, decrypt_string

BASE_DIR = Path(__file__).resolve().parent.parent
MEM_DIR = BASE_DIR / "data" / "project_memories"

def _load_project_data(p_name: str) -> list:
    p_file = MEM_DIR / f"{p_name}.json"
    if not p_file.exists():
        return []
    try:
        raw = p_file.read_text(encoding="utf-8").strip()
        if not raw:
            return []
        if not (raw.startswith("{") or raw.startswith("[")):
            raw = decrypt_string(raw)
        return json.loads(raw)
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
    return []

def _save_project_data(p_name: str, data: list):
    MEM_DIR.mkdir(parents=True, exist_ok=True)
    p_file = MEM_DIR / f"{p_name}.json"
    try:
        raw_json = json.dumps(data, indent=2, ensure_ascii=False)
        p_file.write_text(encrypt_string(raw_json), encoding="utf-8")
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)

def project_memory(parameters: dict, player=None) -> str:
    action = parameters.get("action", "list").lower().strip()
    p_name = parameters.get("project_name", "").strip().lower()
    note = parameters.get("note", "").strip()
    
    p_name = "".join(c for c in p_name if c.isalnum() or c in ("-", "_"))
    
    if action == "list":
        if not MEM_DIR.exists():
            return "No projects registered in context memory, sir."
        projects = [f.stem for f in MEM_DIR.glob("*.json")]
        if not projects:
            return "No projects registered in context memory, sir."
        return "### [PROJECT MEMORIES] Registered Workspaces:\n" + "\n".join(f"- {p}" for p in projects)
        
    if not p_name:
        return "Please specify a project name, sir."
        
    notes = _load_project_data(p_name)
    
    if action in ("add_note", "save"):
        if not note:
            return "Please provide note content to remember for this project, sir."
        notes.append(note)
        _save_project_data(p_name, notes)
        return f"Added context note to project '{p_name}': '{note}', sir."
        
    elif action == "load":
        if not notes:
            return f"Project '{p_name}' has no saved context notes, sir."
            
        output = [f"### [PROJECT CONTEXT] Project: {p_name}\n"]
        for idx, n in enumerate(notes, 1):
            output.append(f"{idx}. {n}")
            
        try:
            sticky_path = BASE_DIR / "memory" / "sticky_notes.txt"
            ctx_block = f"\n\n[PROJECT CONTEXT: {p_name.upper()}]\n" + "\n".join(notes)
            sticky_path.write_text(ctx_block, encoding="utf-8")
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
            
        return "\n".join(output) + "\n\n(Context has been injected into active memory, sir!)"
        
    else:
        return "Unknown project memory action, sir."
