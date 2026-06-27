"""
claude_code_helper.py — Integrates Claude Code CLI via the free-claude-code local proxy.

Enables zero-cost Claude Code agent execution using existing Gemini and NVIDIA NIM keys.
"""

import os
import sys
import json
import time
import subprocess
import socket
from pathlib import Path
from typing import Any, Optional

BASE_DIR        = Path(__file__).resolve().parent.parent
PROXY_DIR       = BASE_DIR / "actions" / "free-claude-code"
API_KEYS_PATH   = BASE_DIR / "config" / "api_keys.json"
PROXY_LOG       = BASE_DIR / "logs" / "claude_code_proxy.log"

def is_port_open(host: str, port: int) -> bool:
    """Checks if a local port is already occupied/listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex((host, port)) == 0

def check_and_install_dependencies():
    """Ensures fastapi, uvicorn, httpx, and python-dotenv are installed."""
    try:
        import fastapi
        import uvicorn
        import httpx
        import dotenv
    except ImportError:
        print("[Claude Code Helper] Installing required python libraries...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "httpx", "python-dotenv", "loguru"],
            capture_output=True,
            text=True
        )

def setup_env():
    """Generates the .env configuration for free-claude-code using api_keys.json."""
    if not API_KEYS_PATH.exists():
        return False
    
    try:
        with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            
        gemini_key = cfg.get("gemini_api_key", "")
        nvidia_key = cfg.get("coding_api_key", "")
        
        env_lines = [
            f"GEMINI_API_KEY={gemini_key}",
            f"NVIDIA_API_KEY={nvidia_key}",
            "DEFAULT_PROVIDER=gemini",
            "PORT=8082",
            "HOST=127.0.0.1",
            "AUTH_TOKEN=freecc"
        ]
        
        PROXY_DIR.mkdir(parents=True, exist_ok=True)
        env_path = PROXY_DIR / ".env"
        with open(env_path, "w", encoding="utf-8") as env_f:
            env_f.write("\n".join(env_lines) + "\n")
            
        print("[Claude Code Helper] .env file successfully configured.")
        return True
    except Exception as e:
        print(f"[Claude Code Helper] Setup env failed: {e}")
        return False

def clone_proxy() -> bool:
    """Clones free-claude-code from GitHub if it does not exist."""
    if (PROXY_DIR / "server.py").exists():
        return True
        
    print("[Claude Code Helper] Cloning free-claude-code proxy repository...")
    try:
        subprocess.run(
            ["git", "clone", "https://github.com/Alishahryar1/free-claude-code.git", str(PROXY_DIR)],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except Exception as e:
        print(f"[Claude Code Helper] Failed to clone proxy: {e}")
        return False

def start_proxy_server() -> bool:
    """Starts the uvicorn FastAPI server in the background."""
    if is_port_open("127.0.0.1", 8082):
        print("[Claude Code Helper] Proxy server already active on port 8082.")
        return True

    print("[Claude Code Helper] Launching proxy server in the background...")
    PROXY_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    # Open log file
    log_f = open(PROXY_LOG, "a", encoding="utf-8")
    
    try:
        # Run uvicorn server:app
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "server:app", "--host", "127.0.0.1", "--port", "8082"],
            cwd=str(PROXY_DIR),
            stdout=log_f,
            stderr=log_f,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        )
        
        # Wait up to 10 seconds for startup
        for _ in range(20):
            time.sleep(0.5)
            if is_port_open("127.0.0.1", 8082):
                print("[Claude Code Helper] Proxy server successfully started.")
                return True
        return False
    except Exception as e:
        print(f"[Claude Code Helper] Failed to start uvicorn: {e}")
        return False

def stop_proxy_server() -> str:
    """Stops the proxy server on Windows by killing the listening process."""
    if not is_port_open("127.0.0.1", 8082):
        return "Proxy server is not running."

    try:
        if os.name == "nt":
            # Find PID using netstat
            output = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True
            ).stdout
            
            pid = None
            for line in output.splitlines():
                if "127.0.0.1:8082" in line or "0.0.0.0:8082" in line or "[::]:8082" in line:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        break
            
            if pid:
                subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                return f"Successfully terminated proxy server (PID {pid})."
            else:
                return "Could not resolve PID of proxy process."
        else:
            subprocess.run(["pkill", "-f", "uvicorn.*8082"], capture_output=True)
            return "Proxy server terminated."
    except Exception as e:
        return f"Failed to terminate proxy: {e}"

def execute_claude_task(instruction: str) -> str:
    """Executes a non-interactive Claude Code CLI command on the workspace."""
    if not clone_proxy():
        return "Error: Could not retrieve free-claude-code proxy, sir."
        
    check_and_install_dependencies()
    setup_env()
    
    if not start_proxy_server():
        return "Error: Could not launch local proxy server on port 8082, sir."

    print(f"[Claude Code Helper] Sending instruction: '{instruction}'")
    
    # Configure custom environment variables
    env = os.environ.copy()
    env["ANTHROPIC_BASE_URL"] = "http://127.0.0.1:8082"
    env["ANTHROPIC_AUTH_TOKEN"] = "freecc"
    env["ANTHROPIC_API_KEY"] = "freecc"
    env["PYTHONUTF8"] = "1"

    cmd = [
        "npx.cmd", "-y", "@anthropic-ai/claude-code",
        "-p", instruction,
        "--dangerously-skip-permissions",
        "--allowedTools", "Bash,Read,Edit"
    ]
    
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(BASE_DIR),
            env=env,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        output = proc.stdout or ""
        error = proc.stderr or ""
        
        # Clean escape sequences or styling from console outputs
        clean_out = output.replace("\x1b", "").replace("[2K", "")
        
        response = []
        if clean_out.strip():
            response.append(f"### [CLAUDE CODE OUTPUT]\n{clean_out}")
        if error.strip() and proc.returncode != 0:
            response.append(f"### [CLAUDE CODE ERROR (Code {proc.returncode})]\n{error}")
            
        if not response:
            return "Claude Code completed execution with zero output, sir."
            
        return "\n\n".join(response)
    except subprocess.TimeoutExpired:
        return "Error: Claude Code execution timed out after 3 minutes, sir."
    except Exception as e:
        return f"Error executing Claude Code: {e}"

def claude_code_helper(parameters: dict[str, Any], player: Optional[Any] = None, speak: Optional[Any] = None) -> str:
    """Main dispatcher entrypoint for the claude_code tool."""
    action = parameters.get("action", "run").lower().strip()
    instruction = parameters.get("instruction", "")
    
    if player and hasattr(player, "write_log"):
        player.write_log(f"ClaudeCode: {action}")
        
    if action == "run":
        if not instruction:
            return "Please provide a valid developer 'instruction' to run, sir."
        return execute_claude_task(instruction)
    elif action == "start_proxy":
        clone_proxy()
        check_and_install_dependencies()
        setup_env()
        if start_proxy_server():
            return "Proxy server is running successfully on port 8082, sir."
        return "Failed to launch proxy server."
    elif action == "stop_proxy":
        return stop_proxy_server()
    elif action == "status":
        running = is_port_open("127.0.0.1", 8082)
        cloned = (PROXY_DIR / "server.py").exists()
        return (
            f"### [CLAUDE CODE STATUS]\n"
            f"• Cloned: {'Yes' if cloned else 'No'}\n"
            f"• Proxy Running: {'Yes (Active on 8082)' if running else 'No (Port 8082 open)'}"
        )
    else:
        return f"Unknown action: '{action}', sir."
