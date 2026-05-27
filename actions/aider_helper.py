"""
aider_helper.py — Wrapper and executor helper for Aider-style AI code refactoring.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from actions.prime_utils import get_base_dir, get_api_key

BASE_DIR = get_base_dir()

def _get_api_key() -> str | None:
    return get_api_key() or None

def is_aider_installed() -> bool:
    try:
        # Check if we can import or run aider
        res = subprocess.run(
            [sys.executable, "-m", "aider", "--version"],
            capture_output=True,
            text=True
        )
        return res.returncode == 0
    except Exception:
        return False

def install_aider() -> bool:
    print("[Aider Helper] Aider is not installed. Initiating installation of aider-chat package...")
    try:
        # Install aider-chat using the current python executable
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "aider-chat"],
            check=True
        )
        return True
    except Exception as e:
        print(f"[Aider Helper] Installation failed: {e}")
        return False

def run_aider_coding_task(instruction: str, file_paths: list[str] | None = None, project_path: str | None = None) -> str:
    """Uses Aider AI to perform autonomous multi-file edits and coding tasks in the repository.
    
    Automatically installs Aider if it's missing, configures the environment with Gemini API keys,
    and runs the command non-interactively.
    """
    if not is_aider_installed():
        print("[Aider Helper] Aider not found. Attempting auto-installation...")
        if not install_aider():
            return "Error: Aider AI (aider-chat) is not installed, and automatic installation failed. Please run 'pip install aider-chat' manually."

    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is not configured. Please specify 'gemini_api_key' in your settings to use Aider."

    # Determine project path (default to active workspace)
    if not project_path:
        project_path = str(BASE_DIR)
    
    proj_dir = Path(project_path).resolve()
    if not proj_dir.exists() or not proj_dir.is_dir():
        return f"Error: Target directory '{project_path}' does not exist."

    # Build the Aider CLI arguments
    cmd = [
        sys.executable, "-m", "aider",
        "--model", "gemini/gemini-2.5-flash",
        "--yes",
        "--message", instruction
    ]

    # Append file paths if supplied
    if file_paths:
        for fp in file_paths:
            # Resolve relative paths against the project directory
            path_obj = Path(fp)
            if not path_obj.is_absolute():
                path_obj = proj_dir / path_obj
            if path_obj.exists():
                cmd.append(str(path_obj))

    # Set up environment variables so Aider natively authenticates with Gemini
    env = os.environ.copy()
    env["GEMINI_API_KEY"] = api_key

    try:
        print(f"[Aider Helper] Running Aider task in {proj_dir}: '{instruction}'")
        # Run Aider process in the target directory
        result = subprocess.run(
            cmd,
            cwd=str(proj_dir),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        
        output = []
        if result.stdout:
            output.append("### 💻 Aider execution output:\n" + result.stdout)
        if result.stderr:
            # Check if stderr is actually an error or just Aider's normal log info
            output.append("### ℹ️ Execution Logs:\n" + result.stderr)

        if result.returncode == 0:
            return "\n\n".join(output) or "Aider coding task completed successfully!"
        else:
            return f"Error: Aider process failed with exit code {result.returncode}.\n\n" + "\n\n".join(output)

    except Exception as e:
        return f"Exception occurred while running Aider: {e}"
