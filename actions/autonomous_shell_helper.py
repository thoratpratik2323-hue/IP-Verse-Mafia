"""
actions/autonomous_shell_helper.py — Autonomous Terminal Execution & Solana Telemetry Helper.

Provides autonomous command execution, environment analysis, self-healing command retry loops,
and mock Solana Web3 wallet telemetry operations for demo/testing environments.
"""
import sys
import subprocess
import json
import re
from pathlib import Path

# Setup paths
def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()



def run_autonomous_loop(goal: str, max_steps: int = 5, player=None) -> str:
    """concept from ANUS CLI: Runs an autonomous shell execution loop to achieve a goal."""
    if not goal:
        return "Goal cannot be empty, sir."

    from actions.prime_utils import call_unified_model
    
    steps_run = []
    
    print(f"[ANUS CLI] Starting autonomous task loop for goal: '{goal}'")
    if player:
        player.write_log(f"[ANUS CLI] Starting autonomous loop for goal: '{goal}'")

    for step in range(1, max_steps + 1):
        # 1. Build prompt for LLM to decide the next terminal command
        history_text = ""
        for idx, (cmd, output, code) in enumerate(steps_run):
            history_text += f"\nStep {idx+1}:\nCommand Run: {cmd}\nExit Code: {code}\nOutput Summary: {output[:500]}\n"

        prompt = f"""You are the ANUS CLI Autonomous Shell Agent inside IP Prime.
Your goal is to achieve this exact user objective: "{goal}"

Current Step: {step} of {max_steps}
Previous Step History:
{history_text or "No commands executed yet."}

Your job:
1. Analyze the objective and previous outputs.
2. Determine the next logical terminal command to execute locally on this Windows system.
3. If the objective is fully satisfied or no further commands are needed, declare that you are finished.

You must respond in one of these two exact formats, and nothing else (no markdown wrappers, no conversational filler):
- To run a command:
COMMAND: <your exact terminal command here>

- To finish the objective:
FINISHED: <a concise summary in Hinglish explaining what you accomplished and the final result for Pratik Sir>
"""

        try:
            response = call_unified_model(contents=prompt, category="coding")
            resp_text = response.text.strip()
        except Exception as e:
            return f"Autonomous agent model call failed: {e}"

        # Parse command or finished
        if resp_text.startswith("FINISHED:"):
            summary = resp_text.replace("FINISHED:", "").strip()
            msg = f"Autonomous loop finished successfully at step {step}/{max_steps}, sir.\n\nSummary:\n{summary}"
            if player:
                player.write_log("[ANUS CLI] Goal completed.")
            return msg

        elif resp_text.startswith("COMMAND:"):
            cmd = resp_text.replace("COMMAND:", "").strip()
            
            # Security safeguard: block destructive command patterns
            destructive = ["rmdir /s /q c:\\", "del /f /s /q c:\\", "format", "shutdown", "mkfs"]
            if any(d in cmd.lower() for d in destructive):
                return f"Safety block: Aborted autonomous step due to highly dangerous command: {cmd}"

            print(f"[ANUS CLI] Step {step} — Executing: {cmd}")
            if player:
                player.write_log(f"[ANUS CLI] Step {step} — Executing: {cmd}")

            try:
                proc = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True,
                    timeout=45, encoding="utf-8", errors="replace"
                )
                stdout = proc.stdout.strip()
                stderr = proc.stderr.strip()
                code = proc.returncode
                
                output_summary = f"Stdout: {stdout}\nStderr: {stderr}" if stderr else stdout
                if not output_summary:
                    output_summary = "Executed with no stdout/stderr output."

                steps_run.append((cmd, output_summary, code))
            except subprocess.TimeoutExpired:
                steps_run.append((cmd, "Command execution timed out after 45 seconds.", -1))
            except Exception as e:
                steps_run.append((cmd, f"Command execution failed: {e}", -1))
        else:
            # Handle standard/irregular responses
            if "finish" in resp_text.lower() or "accomplished" in resp_text.lower():
                return f"Autonomous loop finished at step {step}/{max_steps}, sir.\n\nSummary:\n{resp_text}"
            
            # Otherwise, try to extract command
            cmd_match = re.search(r"COMMAND:\s*(.*)", resp_text, re.IGNORECASE)
            if cmd_match:
                cmd = cmd_match.group(1).strip()
                steps_run.append((cmd, "Parsed command from irregular format.", 0))
            else:
                return f"Autonomous loop encountered format parsing error at step {step}. Response was:\n{resp_text}"

    # If steps ran out without finishing
    history_text = "\n".join([f"- Command: {cmd} (Exit Code: {code})" for cmd, _, code in steps_run])
    return (
        f"Autonomous loop reached maximum limit of {max_steps} steps without explicit completion declaration, sir.\n\n"
        f"Execution Trace:\n{history_text}"
    )

def autonomous_shell_helper(parameters: dict, player=None) -> str:
    """
    Main dispatcher for autonomous shell execution.

    Parameters (dict keys):
        action (str)     : autonomous_run
        goal (str)       : Target objective for autonomous terminal run
        max_steps (int)  : Maximum command iterations for autonomous run (default: 5)

    Returns:
        str: Result message for the user.
    """
    p = parameters or {}
    action = p.get("action", "autonomous_run").lower().strip()
    goal = p.get("goal", "").strip()
    max_steps = int(p.get("max_steps", 5))

    if action == "autonomous_run":
        return run_autonomous_loop(goal, max_steps, player)
    else:
        return f"Invalid autonomous shell action: '{action}', sir."


# Backwards-compatible alias — main.py now imports autonomous_shell_helper
autonomous_cli_helper = autonomous_shell_helper
