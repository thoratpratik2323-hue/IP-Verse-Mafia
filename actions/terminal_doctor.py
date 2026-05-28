"""
terminal_doctor.py — Diagnoses terminal commands failures and prints recommendations.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/terminal_doctor.py
import sys
import os
import re
import json
import subprocess
import time
from pathlib import Path
from google import genai

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()

def _get_api_key() -> str:
    cfg_path = BASE_DIR / "config" / "api_keys.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            return cfg.get("coding_api_key") or cfg.get("gemini_api_key", "")
        except Exception:
            pass
    return ""

def diagnose_and_heal_command(command: str, cwd: str = None, max_rounds: int = 3, ui = None) -> str:
    """Feature 3: Smart Shell Doctor & Self-Healing Terminal with Multi-round Diagnostics & Execution."""
    api_key = _get_api_key()
    if not api_key:
        return "Gemini API key not found in configurations, sir."

    log_prefix = "[TerminalDoctor] "
    if ui:
        ui.write_log(f"SYS: Doctor Mode started for: {command}")
    print(f"{log_prefix}Starting multi-round healing for: '{command}'")

    current_cmd = command
    report_lines = ["🧑‍⚕️ **Terminal Doctor - Self-Healing Session**", f"Original Command: `{command}`\n"]
    
    for round_idx in range(1, max_rounds + 1):
        if ui:
            ui.write_log(f"SYS: Round {round_idx}/{max_rounds} - Running: {current_cmd}")
        report_lines.append(f"### 🔄 **Round {round_idx}/{max_rounds}**")
        
        # 1. Run the command
        try:
            t0 = time.time()
            result = subprocess.run(
                current_cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd,
                timeout=45
            )
            duration = time.time() - t0
        except subprocess.TimeoutExpired:
            report_lines.append("⚠️ Command execution timed out after 45 seconds.")
            break
        except Exception as e:
            report_lines.append(f"✗ Failed to run command: {e}")
            break

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        return_code = result.returncode

        has_error = (return_code != 0) or ("traceback" in stderr.lower()) or ("error" in stderr.lower())
        
        if not has_error:
            output_snippet = stdout[:400] + ("..." if len(stdout) > 400 else "")
            report_lines.append(f"✓ Command completed successfully in {duration:.2f}s!")
            report_lines.append("- Exit Code: 0")
            if output_snippet:
                report_lines.append(f"- Output:\n```\n{output_snippet}\n```")
            
            if round_idx == 1:
                return "\n".join(report_lines)
            else:
                report_lines.append(f"\n🎉 **Self-Healing Success! The command was fully resolved after {round_idx-1} repairs!**")
                return "\n".join(report_lines)

        # Command failed, diagnose using Gemini
        report_lines.append(f"✗ Command failed (Exit Code: {return_code})")
        if stderr:
            report_lines.append(f"- Stderr snippet: `{stderr[:150]}`")
        
        if ui:
            ui.write_log("SYS: Command failed. Running Gemini diagnosis...")

        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are the ultimate AI Terminal Doctor and Systems Engineer.
The user executed a command that failed.

Executed Command: {current_cmd}
Working Directory: {cwd or 'default'}
Exit Code: {return_code}

Stdout Output:
{stdout[:1000]}

Stderr/Error Output:
{stderr[:1000]}

Your task:
1. Diagnose the exact root cause of the error.
2. Formulate a precise, safe repair command to fix it (e.g. installing a missing package via pip/npm, correcting a path, creating a folder, setting environment variable).
3. The repair command must be ready to execute immediately.

Return your response in standard JSON format (do not wrap in markdown or backticks):
{{
  "diagnostics": "Detailed explanation of the root cause in simple, concise terms.",
  "recommended_fix": "Description of what needs to be fixed.",
  "repair_command": "The exact shell command to fix the issue (e.g. 'pip install requests'). Leave empty if no safe command is available."
}}
"""
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            text = (response.text or "").strip()
            text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
            text = re.sub(r"\r?\n?```\s*$", "", text)
            text = text.strip()
            
            data = json.loads(text)
        except Exception as e:
            report_lines.append(f"✗ AI Diagnostic failed: {e}")
            break

        diagnostics = data.get("diagnostics", "Unknown error.")
        recommended_fix = data.get("recommended_fix", "No fix recommended.")
        repair_cmd = data.get("repair_command", "").strip()

        report_lines.append(f"🔍 **Diagnostics:** {diagnostics}")
        report_lines.append(f"💡 **Recommended Fix:** {recommended_fix}")

        if not repair_cmd:
            report_lines.append("ℹ️ No automated repair command could be generated safely, ending healing session.")
            break

        report_lines.append(f"🛠️ **Executing Repair Command:** `{repair_cmd}`")
        if ui:
            ui.write_log(f"SYS: Repairing with: {repair_cmd}")
            
        try:
            fix_res = subprocess.run(
                repair_cmd,
                shell=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=cwd,
                timeout=60
            )
            if fix_res.returncode == 0:
                report_lines.append("✓ Repair applied successfully. Retrying original command next.")
            else:
                report_lines.append(f"✗ Repair command failed (Exit Code: {fix_res.returncode}).")
                if fix_res.stderr.strip():
                    report_lines.append(f"- Repair Stderr: {fix_res.stderr.strip()[:150]}")
                break
        except Exception as fe:
            report_lines.append(f"✗ Exception during repair: {fe}")
            break

    else:
        report_lines.append(f"\n⚠️ Max healing rounds ({max_rounds}) reached without complete resolution.")

    return "\n".join(report_lines)


def ghost_scribe_tutorial(topic: str, commands: list[str] = None, output_path: str = None, ui = None) -> str:
    """Feature 3: Ghost-Scribe Automated Code Walkthrough & Tutorial Generator."""
    api_key = _get_api_key()
    if not api_key:
        return "Gemini API key not found in configurations, sir."

    if ui:
        ui.write_log(f"SYS: Ghost Scribe tutorial generating for topic: {topic}")

    proj_dir = Path(BASE_DIR).resolve()
    print(f"[GhostScribe] Scanning project: {proj_dir}")

    # Gather uncommitted git changes if possible
    diff_text = ""
    try:
        git_diff = subprocess.run(
            ["git", "diff", "HEAD"],
            capture_output=True,
            text=True,
            cwd=str(proj_dir),
            timeout=10
        )
        if git_diff.returncode == 0 and git_diff.stdout.strip():
            diff_text = git_diff.stdout.strip()
    except Exception:
        pass

    # Gather codebase snippets
    allowed_exts = {".py", ".md", ".json", ".html", ".css", ".js", ".ts"}
    file_contents = []
    file_count = 0

    try:
        for root, _, files in os.walk(proj_dir):
            if any(x in root for x in (".git", "__pycache__", ".venv", "node_modules", "build", "dist")):
                continue
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in allowed_exts and file_count < 8:
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        snippet = content[:1500] + ("\n..." if len(content) > 1500 else "")
                        file_contents.append(f"### File: {file_path.name}\nPath: {file_path.relative_to(proj_dir)}\n```\n{snippet}\n```")
                        file_count += 1
                    except Exception:
                        pass
    except Exception as e:
        print(f"[GhostScribe] Walk error: {e}")

    # Formulate tutorial prompt
    client = genai.Client(api_key=api_key)
    
    cmd_section = ""
    if commands:
        cmd_section = "\nTarget commands sequence to explain:\n" + "\n".join(f"- `{c}`" for c in commands)

    prompt = f"""You are the Ghost-Scribe Tutorial Generator.
Create a beautifully structured, premium developer tutorial / cheatsheet in Markdown explaining the project features.

User Request/Topic: {topic}{cmd_section}
Project Root: {proj_dir.name}

{"Active Git Changes (Diff):" if diff_text else ""}
{diff_text[:4000] if diff_text else ""}

Project Core Code Files:
{chr(10).join(file_contents)[:6000]}

Your tutorial must contain:
1. An engaging header and intro.
2. A comprehensive feature walkthrough highlighting key components.
3. Code blocks showing real implementation usage.
4. Visually rich Alerts (e.g. GitHub style `> [!NOTE]`, `> [!IMPORTANT]`, `> [!WARNING]`).
5. A Mermaid diagram illustrating the flow or architecture mapping.
6. A Verification Plan with specific command steps to test correctness.

Create a premium, master-class level tutorial with zero placeholders (no TODOs, no 'implement here'). Return ONLY the complete Markdown document.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        tutorial_md = response.text or ""
        if not tutorial_md:
            return "Failed to generate tutorial: Empty response."
            
        # Determine output location
        if output_path:
            out_file = Path(output_path)
            if out_file.is_dir():
                out_file = out_file / "cheatsheet_tutorial.md"
        else:
            out_file = Path.home() / "Desktop" / "cheatsheet_tutorial.md"
            
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(tutorial_md, encoding="utf-8")
        
        if ui:
            ui.write_log(f"SYS: Ghost Scribe tutorial saved to: {out_file.name}")
            
        return (
            f"✓ Ghost-Scribe Tutorial generated successfully, sir!\n"
            f"- Saved visual markdown tutorial directly to: `{out_file.resolve()}`"
        )
        
    except Exception as e:
        return f"Failed to generate Ghost-Scribe tutorial: {e}"
