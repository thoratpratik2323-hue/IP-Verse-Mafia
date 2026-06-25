import re
import json
from pathlib import Path
from google import genai
from actions.model_switcher import get_preferred_model

def error_detective(parameters: dict, player=None) -> str:
    traceback_text = parameters.get("traceback_text", "").strip()
    if not traceback_text:
        return "Please paste or provide the traceback/error text, sir."
        
    try:
        from main import _get_api_key
        api_key = _get_api_key()
    except Exception:
        return "I need a Gemini API key to run the Error Detective, sir."
        
    # Attempt to parse file paths and line numbers from traceback
    # E.g., File "C:\path\to\file.py", line 45, in some_func
    pattern = r'File\s+"([^"]+)",\s+line\s+(\d+)'
    matches = re.findall(pattern, traceback_text)
    
    code_context = ""
    target_file = None
    target_line = None
    
    if matches:
        # Get the last match as it's usually the origin of the error (closest to crash point)
        for filepath_str, line_str in reversed(matches):
            p = Path(filepath_str)
            # Skip standard library and site-packages to focus on user code
            if "site-packages" in filepath_str or "Python" in filepath_str or "lib" in filepath_str.lower():
                continue
            if p.exists() and p.is_file():
                target_file = p
                target_line = int(line_str)
                break
        
        # If no user files found, fallback to the absolute last entry in traceback
        if not target_file:
            filepath_str, line_str = matches[-1]
            p = Path(filepath_str)
            if p.exists() and p.is_file():
                target_file = p
                target_line = int(line_str)
                
    if target_file and target_line:
        try:
            lines = target_file.read_text(encoding="utf-8").splitlines()
            start = max(0, target_line - 6)
            end = min(len(lines), target_line + 5)
            context_lines = []
            for idx in range(start, end):
                pointer = ">>> " if idx + 1 == target_line else "    "
                context_lines.append(f"{pointer}{idx + 1}: {lines[idx]}")
            code_context = (
                f"\n--- Code Context from {target_file.name} ---\n"
                + "\n".join(context_lines)
                + "\n----------------------------------------\n"
            )
        except Exception as e:
            code_context = f"\n(Attempted to read code context but failed: {e})\n"

    try:
        client = genai.Client(api_key=api_key)
        model = get_preferred_model("coding")
        
        prompt = (
            "You are the Error Detective. Explain the following error / traceback.\n"
            "Identify exactly what failed, which line caused it, and why it occurred.\n"
            "Provide a beginner-friendly explanation and clear steps to fix it in warm, helpful Hinglish.\n\n"
            f"Traceback:\n{traceback_text}\n"
        )
        if target_file:
            prompt += f"\nTarget File: {target_file.resolve()}\nLine: {target_line}\n"
        if code_context:
            prompt += code_context
            
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        
        output = []
        output.append("### 🔍 [ERROR DETECTIVE] Analysis Result")
        if target_file:
            output.append(f"**Target File:** `{target_file.name}` (Line {target_line})")
        output.append("\n" + response.text)
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Error Detective analysis failed: {e}, sir."
