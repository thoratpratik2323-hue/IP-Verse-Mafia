"""
cmd_control.py — Natural language to PowerShell translator.
Ported from Jarvis (S.A.T.U.R.D.A.Y) to IP Prime.
"""

import subprocess
import json
import numpy as np
from actions.openrouter_helper import client

def cmd_control(parameters: dict, player=None) -> str:
    task = parameters.get("task", "").strip()
    if not task:
        return "Error: No task provided."

    # Ask the OpenRouter LLM to translate the task into a single Windows PowerShell command
    prompt = (
        f"Translate the following natural language task into a single, executable Windows PowerShell command.\n"
        f"Return ONLY the raw command. No markdown formatting (like ```powershell or ```), no quotes, no explanation.\n\n"
        f"Task: {task}\n\n"
        f"Command:"
    )
    
    try:
        command = client.chat(
            prompt=prompt,
            system="You are a natural language to Windows PowerShell command translator. Return ONLY the raw command, nothing else.",
            temperature=0.0
        ).strip()
        
        # Clean any markdown block backticks if the model returned them
        if command.startswith("```"):
            lines = command.splitlines()
            # Remove first line (```lang) and last line (```)
            clean_lines = [l for l in lines if not l.startswith("```")]
            command = "\n".join(clean_lines).strip()
            
        if command.startswith("powershell"):
            command = command[10:].strip()
            
        print(f"[cmd_control] Translated: '{task}' -> '{command}'")
        if player:
            try:
                player.write_thought(f"Running PowerShell command: {command}")
            except Exception:
                pass
        
        # Run the command on Windows using powershell
        result = subprocess.run(
            ["powershell", "-Command", command],
            capture_output=True,
            text=True,
            shell=True,
            timeout=30
        )
        
        output = (result.stdout or "").strip()
        error = (result.stderr or "").strip()
        
        ret = ""
        if output:
            ret += f"Stdout:\n{output}\n"
        if error:
            ret += f"Stderr:\n{error}\n"
            
        if not ret:
            ret = f"Command executed successfully (Exit code: {result.returncode})."
            
        return ret
    except Exception as e:
        return f"Error executing task '{task}': {e}"
