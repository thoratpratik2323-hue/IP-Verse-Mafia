"""
autonomous_autopilot.py — Programmatic OS mouse/keyboard actions planner and Aider self-healing refactor engine.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/autonomous_autopilot.py
import ast
import json
import time
from pathlib import Path
from actions.prime_utils import get_api_key

def _get_gemini_client():
    """Returns a google-genai client using the central API key."""
    try:
        from google import genai
        api_key = get_api_key()
        if api_key:
            return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[Autonomous Autopilot] Client init failed: {e}")
    return None

# ==========================================
# 1. Self-Healing Refactoring Loop (Aider-style)
# ==========================================
def self_healing_refactor(file_path: str, instruction: str, max_attempts: int = 5, player=None) -> str:
    """Modifies a file based on instructions and runs iterative compile checks, auto-correcting errors recursively."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API configure nahi hai, sir."
        
    path = Path(file_path)
    if not path.exists():
        return f"Target file exist nahi karti, sir: {file_path}"
        
    logs = [
        "### ⚡ Self-Healing Refactoring Loop (Aider-style)",
        f"**Target File:** `{path.name}`",
        f"**Instruction:** \"{instruction}\"",
        f"**Max Safety Loops:** {max_attempts} iterations",
        ""
    ]
    
    current_code = path.read_text(encoding="utf-8")
    iteration = 0
    success = False
    
    while iteration < max_attempts:
        iteration += 1
        if player:
            player.write_thought(f"Self-healing iteration #{iteration} of refactoring loop...")
            
        logs.append(f"**[Iteration #{iteration}]** Generating code edits with Gemini...")
        
        try:
            from google.genai import types
            system_instruction = (
                "You are an elite, autonomous software developer (Aider-style). "
                "You are provided with a source code file and an instruction to modify it. "
                "Apply the modification cleanly. Return ONLY the complete modified source code. "
                "Do not include any explanation markdown wrappers or conversational intro/outro text, just the raw code."
            )
            
            prompt = (
                f"Instruction: {instruction}\n\n"
                f"Original File Contents:\n```\n{current_code}\n```"
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.2
                )
            )
            modified_code = response.text
            if "```" in modified_code:
                code_blocks = ast.literal_eval(repr(modified_code)).split("```")
                # Parse markdown code blocks
                for idx, block in enumerate(code_blocks):
                    if idx % 2 == 1:
                        # Skip language specifier
                        lines = block.splitlines()
                        if lines and (lines[0].strip().lower() in {"python", "py", "javascript", "js", "typescript", "ts", "json", "html", "css"}):
                            modified_code = "\n".join(lines[1:])
                        else:
                            modified_code = block
                        break
                        
            # Compile check
            try:
                ast.parse(modified_code)
                # If syntax checks out, save the file
                path.write_text(modified_code, encoding="utf-8")
                logs.append("- [OK] Syntax verification passed successfully.")
                success = True
                break
            except SyntaxError as se:
                error_trace = f"SyntaxError at Line {se.lineno}, Offset {se.offset}: {se.msg}\nCode block:\n{se.text}"
                logs.append(f"- [FAIL] Syntax verification failed: `{se.msg}` (Line {se.lineno})")
                logs.append("- Triggering recursive self-healing correction...")
                
                # Feedback loop: feed error trace back for the next iteration
                instruction = (
                    f"CRITICAL: The previous edit generated a syntax error! Please fix this error exactly:\n"
                    f"{error_trace}\n\n"
                    f"Original target instruction: {instruction}"
                )
                current_code = modified_code
        except Exception as e:
            logs.append(f"- [FAIL] API execution error: {e}")
            break
            
    if success:
        logs.append(f"\n✅ **Refactoring loop completed successfully, sir!** Code compiles with 0 errors in {iteration} rounds.")
    else:
        logs.append(f"\n❌ **Refactoring loop failed after {max_attempts} attempts, sir.** Safety limit hit without resolving errors.")
        
    return "\n".join(logs)

# ==========================================
# 2. GUI Task Planner & Execution (PyAutoGUI)
# ==========================================
def execute_gui_automation(nl_instructions: str, player=None) -> str:
    """Translates natural language GUI commands into safe PyAutoGUI python statements and executes them."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API required for GUI translation, sir."
        
    if player:
        player.write_thought("Translating natural instructions to PyAutoGUI operations...")
        
    try:
        from google.genai import types
        system_instruction = (
            "You are a desktop macro automation engineer. Translate the natural language GUI "
            "instructions into a list of safe PyAutoGUI statements. "
            "Available tools: pyautogui.click(x, y), pyautogui.write('text'), pyautogui.press('key'), "
            "pyautogui.hotkey('k1', 'k2'), time.sleep(seconds). "
            "For click coordinate estimation, assume screen resolution is 1920x1080 unless specified. "
            "Return a clean JSON block exactly like this: "
            "{\"statements\": [\"pyautogui.click(100, 200)\", \"pyautogui.write('hello')\"]}"
        )
        
        prompt = f"Translate these GUI instructions, sir: '{nl_instructions}'"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        
        data = json.loads(response.text.strip())
        statements = data.get("statements", [])
        
        logs = [
            "### 🖱️ GUI Task Automation Checklist",
            f"**Natural Intent:** \"{nl_instructions}\"",
            "**Generated PyAutoGUI Scripts:**",
        ]
        for stmt in statements:
            logs.append(f"- `{stmt}`")
            
        logs.append("\nStarting execution (Safety Failsafe active: move cursor to corner to abort)...")
        
        # Execute PyAutoGUI actions
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.5
            
            for stmt in statements:
                # Restrict execution to safe calls only
                if stmt.strip().startswith(("pyautogui.", "time.sleep")):
                    eval(stmt, {"pyautogui": pyautogui, "time": time})
                    logs.append(f"- [OK] Executed: `{stmt}`")
                    
            logs.append("\n✅ **GUI automation completed successfully, sir!**")
        except Exception as e:
            logs.append(f"\n❌ Execution aborted/failed: {e}")
            
        return "\n".join(logs)
    except Exception as e:
        return f"GUI translation failed: {e}, sir."

# ==========================================
# Main Dispatcher
# ==========================================
def autonomous_autopilot(parameters: dict, player=None) -> str:
    """Main dispatcher for Autonomous Autopilot action module."""
    action = parameters.get("action", "self_healing")
    
    if action == "self_healing":
        fp = parameters.get("file_path", "")
        instr = parameters.get("instruction", "")
        max_att = int(parameters.get("max_attempts", 5))
        if not fp or not instr:
            return "Please provide 'file_path' and 'instruction' parameters, sir."
        return self_healing_refactor(fp, instr, max_att, player)
        
    elif action == "gui_automation":
        instr = parameters.get("instruction", "")
        if not instr:
            return "Please provide 'instruction' natural language parameter, sir."
        return execute_gui_automation(instr, player)
        
    return f"Invalid autonomous autopilot action: '{action}', sir."
