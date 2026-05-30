"""
aislop_helper.py — Engineering standards layer and quality gate for AI-generated code.

This module wraps the `scanaislop` Node-based CLI tool to scan and auto-fix 
common anomalies (placeholders, unused imports, dead code) in codebases.
"""

import os
import json
import subprocess
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent

def run_aislop_scan(target_path: str, player=None) -> dict:
    """
    Runs a code quality and AI-slop scan on a target file or directory.
    Uses 'cmd.exe /c npx -y aislop scan <target> --json' to bypass Windows execution policies.
    """
    path_obj = Path(target_path)
    if not path_obj.exists():
        return {"error": f"Path '{target_path}' does not exist.", "score": 0}
        
    cmd = [
        "cmd.exe", "/c", 
        "npx", "-y", "aislop", "scan", str(path_obj), "--json"
    ]
    
    if player:
        player.write_thought(f"Running deterministic AI-slop quality gate scan on: {path_obj.name}...")
        
    try:
        # Run process quietly in background
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            timeout=30,
            cwd=str(BASE_DIR)
        )
        
        # Parse output
        output_str = result.stdout.strip()
        if not output_str:
            # Check if there's any stderr
            err_str = result.stderr.strip()
            if err_str and "error" in err_str.lower():
                return {"error": err_str, "score": 0}
            return {"score": 100, "issues": [], "message": "Zero AI-slop detected! Code is pristine."}
            
        try:
            data = json.loads(output_str)
            return data
        except json.JSONDecodeError:
            # Fallback to parsing raw text lines if JSON failed but we have output
            return {
                "score": 75,
                "raw_output": output_str,
                "issues": [{"file": str(path_obj.name), "message": "Parsed raw CLI scanner output."}]
            }
            
    except subprocess.TimeoutExpired:
        return {"error": "Scan timed out after 30 seconds.", "score": 0}
    except Exception as e:
        return {"error": f"Failed to execute aislop scanner: {e}", "score": 0}

def run_aislop_fix(target_path: str, player=None) -> str:
    """
    Automatically cleans up AI placeholders, unused imports, and slops.
    Runs 'cmd.exe /c npx -y aislop fix <target>'.
    """
    path_obj = Path(target_path)
    if not path_obj.exists():
        return f"Error: Path '{target_path}' does not exist, sir."
        
    cmd = [
        "cmd.exe", "/c", 
        "npx", "-y", "aislop", "fix", str(path_obj)
    ]
    
    if player:
        player.write_thought(f"Executing auto-correction and cleaning up AI stubs in: {path_obj.name}...")
        
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=False,
            timeout=30,
            cwd=str(BASE_DIR)
        )
        
        if result.returncode == 0:
            return f"Auto-fix execution completed successfully, sir! Unused imports and stubs in '{path_obj.name}' have been cleaned up."
        else:
            return f"Fix completed with notice, sir: {result.stdout.strip() or result.stderr.strip()}"
            
    except subprocess.TimeoutExpired:
        return "Auto-fix operation timed out."
    except Exception as e:
        return f"Failed to execute auto-fix: {e}"

def format_scan_results(data: dict, target_name: str) -> str:
    """Formats the JSON scan results into a premium terminal card."""
    if "error" in data:
        return (
            f"### ❌ [AI-SLOP SCANNER] Operational Error\n"
            f"- **Target**: `{target_name}`\n"
            f"- **Details**: {data['error']}\n\n"
            f"> [!WARNING]\n"
            f"> Please ensure Node.js is installed on PATH and npx is accessible, sir."
        )
        
    score = data.get("score", 100)
    
    # Harmonious colors based on score
    if score >= 90:
        badge = "🟢 Pristine"
        grade_desc = "Excellent code quality. Zero or minimal AI stubs."
    elif score >= 75:
        badge = "🟡 Normal"
        grade_desc = "Standard quality. Some minor stubs or unused imports detected."
    else:
        badge = "🔴 Slop Warning"
        grade_desc = "Suboptimal. Significant AI-generated placeholders or dead branches found."
        
    output = [
        f"### 🛡️ [AI-SLOP SCAN] ENGINEERING QUALITY GATE\n",
        f"- **Target scanned**: `{target_name}`",
        f"- **Code Score**: **{score}/100** ({badge})",
        f"- **Verdict**: *{grade_desc}*\n",
        f"---"
    ]
    
    issues = data.get("issues", [])
    if not issues:
        raw = data.get("raw_output", "")
        if raw:
            output.append("#### Detected CLI Diagnostics:")
            output.append(f"```text\n{raw}\n```")
        else:
            output.append("\n🎉 **Inbox clean! No AI stubs or compilation anomalies detected.**\n")
    else:
        output.append("#### 🔍 Detected Anomalies:")
        # Group by file
        grouped = {}
        for issue in issues:
            f = issue.get("file", "General")
            grouped.setdefault(f, []).append(issue)
            
        for file_path, file_issues in grouped.items():
            output.append(f"\n📁 **{Path(file_path).name}**:")
            for issue in file_issues:
                line = f"L{issue.get('line')}" if issue.get("line") else ""
                msg = issue.get("message", "Suboptimal code pattern.")
                issue_type = issue.get("type", "Standard Slop")
                loc = f" ({line})" if line else ""
                output.append(f"  - `[{issue_type}]`{loc}: {msg}")
                
    output.append("\n---")
    if score < 95:
        output.append(f"💡 *Suggestion: You can ask me to run 'aislop_helper action=fix target={target_name}' to auto-clean stubs!*")
        
    return "\n".join(output)

def aislop_helper(parameters: dict, player=None) -> str:
    """Main dispatcher tool for AISlop Quality Gate."""
    action = parameters.get("action", "scan").lower().strip()
    target = parameters.get("target", "").strip()
    
    # Default target to workspace root if empty
    if not target:
        target = str(BASE_DIR)
        
    # Resolve relative paths relative to workspace root
    target_path = Path(target)
    if not target_path.is_absolute():
        target_path = BASE_DIR / target_path
        
    target_str = str(target_path)
    
    if action == "scan":
        results = run_aislop_scan(target_str, player)
        return format_scan_results(results, target_path.name)
    elif action == "fix":
        return run_aislop_fix(target_str, player)
    else:
        return f"Unknown action '{action}' for AISlop helper, sir. Available: scan, fix."
