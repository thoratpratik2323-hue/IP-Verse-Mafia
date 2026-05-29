"""
warp_helper.py — Automates Warp terminal commands chains.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/warp_helper.py
import os
import sys
import json
import re
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
GEMINI_MODEL = "gemini-2.5-flash"

def _get_api_key() -> str:
    config_path = BASE_DIR / "config" / "api_keys.json"
    if not config_path.exists():
        return ""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("coding_api_key") or config.get("gemini_api_key", "")
    except Exception:
        return ""

def _get_gemini():
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("Coding API Key or Gemini API Key is missing inside config/api_keys.json.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(GEMINI_MODEL)

def _clean_yaml(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
    text = re.sub(r"\n?```$", "", text)
    return text.strip()

def _get_warp_workflows_dir() -> Path:
    # Warp stores local custom workflows in %APPDATA%\warp\Warp\data\workflows\ on Windows
    appdata = os.getenv("APPDATA")
    if appdata:
        p = Path(appdata) / "warp" / "Warp" / "data" / "workflows"
        return p
    # Fallback to home dir
    return Path.home() / ".warp" / "workflows"

def warp_helper(parameters: dict, player=None) -> str:
    """
    Action: warp_helper
    Manages and JIT-generates ultra-premium custom Warp Terminal Workflows (.yaml)
    directly into Warp's application config path or project directory.
    """
    params = parameters or {}
    action = params.get("action", "generate").lower().strip()
    workflow_name = params.get("name", "").strip()
    description = params.get("description", "").strip()
    project_path = params.get("project_path", "").strip()

    warp_dir = _get_warp_workflows_dir()

    if action == "list":
        if player:
            player.write_log("[Warp Helper] Scanning custom workflows directory...")
        
        if not warp_dir.exists():
            return "Pratik Sir, no custom Warp workflows directory found yet. Run 'generate' to create one!"
        
        files = list(warp_dir.glob("*.yaml")) + list(warp_dir.glob("*.yml"))
        if not files:
            return f"Pratik Sir, your custom Warp workflows directory (`{warp_dir}`) is currently empty."
        
        results = ["### 📋 Active Custom Warp Workflows inside APPDATA:\n"]
        for idx, f in enumerate(files, 1):
            results.append(f"{idx}. **{f.name}** (`{f.resolve()}`)")
        
        return "\n".join(results)

    elif action == "view":
        if not workflow_name:
            return "Pratik Sir, please provide the name of the workflow you want to view."
        
        # Ensure suffix
        if not workflow_name.endswith(".yaml") and not workflow_name.endswith(".yml"):
            workflow_name += ".yaml"
            
        target_file = warp_dir / workflow_name
        if not target_file.exists():
            return f"Pratik Sir, I could not find a workflow named '{workflow_name}' inside `{warp_dir}`."
        
        try:
            content = target_file.read_text(encoding="utf-8")
            return f"### 📄 Custom Warp Workflow: `{workflow_name}`\n\n```yaml\n{content}\n```"
        except Exception as e:
            return f"Could not read workflow: {e}"

    # Default action: generate
    if not description:
        return "Pratik Sir, please describe what command pipeline or setup workflow you want to generate."
    
    if not workflow_name:
        # Standardize name
        workflow_name = "custom_warp_workflow"
    
    # Sanitize file name
    workflow_name = re.sub(r"[^\w\-]", "_", workflow_name.replace(" ", "_").lower())
    if not workflow_name.endswith(".yaml"):
        workflow_name += ".yaml"

    if player:
        player.write_log(f"[Warp Helper] Engineering AI Warp Workflow for: '{description[:40]}...'")

    prompt = f"""You are a master developer expert in constructing Warp Terminal Workflows.
Warp Terminal Workflows use a strict, clean YAML format to define command pipelines with custom placeholders/arguments.

Goal Description:
{description}

Create a premium, production-grade Warp Terminal Workflow YAML that accomplishes this.
Ensure it satisfies the following format exactly:

```yaml
name: A beautiful descriptive name for the menu (e.g. Build and Deploy React)
command: |-
  # You can include comments and multiple commands here
  # Use double curly braces for arguments like {{my_arg}}
  npm run build
  scp -r ./dist user@{{server_ip}}:/var/www
description: Detailed description of what the workflow does.
tags:
  - web
  - build
arguments:
  - name: server_ip
    description: The target production server IP address
    default_value: 192.168.1.1
```

Return ONLY the raw YAML code block. No explanations, no extra talk, no markdown other than the yaml fence block.
"""

    try:
        model = _get_gemini()
        response = model.generate_content(prompt)
        yaml_content = _clean_yaml(response.text)
    except Exception as e:
        return f"Pratik Sir, failed to generate workflow via Gemini: {e}"

    # Write target
    if project_path:
        target_dir = Path(project_path) / ".warp" / "workflows"
    else:
        target_dir = warp_dir

    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        out_file = target_dir / workflow_name
        out_file.write_text(yaml_content, encoding="utf-8")
        
        if player:
            player.write_log(f"[Warp Helper] Successfully wrote workflow to {out_file.name}")
            
        location_type = "Project folder" if project_path else "Warp APPDATA config"
        return (
            f"### 🚀 Custom Warp Workflow Generated successfully, Pratik Sir!\n\n"
            f"- **Workflow Name**: `{workflow_name}`\n"
            f"- **Location**: {location_type} (`{out_file}`)\n"
            f"- **How to use**:\n"
            f"  1. Open **Warp Terminal**.\n"
            f"  2. Press `CTRL + SHIFT + R` (or Command Palette) to open the Workflows search.\n"
            f"  3. You will see your new workflow listed under **\"My Workflows\"** ready to run with dynamic argument placeholders!\n\n"
            f"#### 📄 Generated YAML Preview:\n"
            f"```yaml\n{yaml_content}\n```"
        )
    except Exception as e:
        return f"Failed to save workflow file: {e}"
