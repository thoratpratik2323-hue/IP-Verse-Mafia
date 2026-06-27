import json
import subprocess
from pathlib import Path

def ask_antigravity(parameters: dict = None, player = None) -> str:
    params = parameters or {}
    instruction = params.get("instruction", "").strip()
    if not instruction:
        return "No instruction provided for Antigravity."

    # Load configuration to get CLI path and conversation ID
    base_dir = Path(__file__).resolve().parent.parent
    api_config_path = base_dir / "config" / "api_keys.json"
    
    try:
        with open(api_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        
        cli_path = config.get("antigravity_cli_path", str(Path.home() / ".gemini" / "antigravity" / "bin" / "agentapi.bat"))
        conv_id = config.get("antigravity_conversation_id", "ae8ed04c-75cf-4526-b6f4-93c19b13b36b")
    except Exception as e:
        return f"Failed to load Antigravity IPC configuration: {e}"

    if player:
        player.write_thought(f"Routing request to Antigravity: '{instruction[:40]}...'")
        player.write_log(f"IPC: Sending message to Antigravity (Conv: {conv_id[:8]})")

    try:
        # Run agentapi.bat send-message <conv_id> <instruction>
        cmd = [cli_path, "send-message", conv_id, f"Pratik Sir says (delegated via IP Prime): {instruction}"]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            encoding="utf-8",
            errors="ignore"
        )
        
        if result.returncode == 0:
            msg = f"Successfully delegated task to Antigravity: '{instruction}'."
            if player:
                player.write_log("IPC: Antigravity successfully notified.")
            return msg
        else:
            err = result.stderr.strip() or result.stdout.strip()
            return f"Antigravity delegation failed: {err}"
            
    except Exception as e:
        return f"Error executing Antigravity CLI delegation: {e}"
