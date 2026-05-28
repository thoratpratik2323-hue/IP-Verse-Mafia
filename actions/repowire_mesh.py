import subprocess
import json
import logging
from pathlib import Path
import os

logger = logging.getLogger("ip_prime.repowire_mesh")

def register_peer(player=None) -> str:
    """Registers IP Prime as a peer on the local Repowire daemon."""
    try:
        # Assuming we are running in the current directory as the project
        project_dir = os.getcwd()
        
        result = subprocess.run(
            ["repowire", "peer", "new", project_dir, "--backend", "ip-prime"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return f"\U0001f310 Registered IP Prime on Repowire mesh for repo {project_dir}"
        else:
            return f"Failed to register on Repowire mesh: {result.stderr}"
    except FileNotFoundError:
        return "Error: 'repowire' command not found. Please install it globally."
    except Exception as e:
        return f"Error registering on Repowire mesh: {e}"

def list_peers(player=None) -> str:
    """Lists all active agents currently on the Repowire mesh."""
    try:
        result = subprocess.run(
            ["repowire", "peer", "list"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            return f"Active Repowire Peers:\n{result.stdout}"
        else:
            return f"Failed to list peers: {result.stderr}"
    except FileNotFoundError:
        return "Error: 'repowire' command not found."
    except Exception as e:
        return f"Error listing peers: {e}"

def ask_peer(peer_name: str, question: str, player=None) -> str:
    """Asks a question to a specific peer on the Repowire mesh."""
    # We simulate the MCP ask tool via CLI for IP Prime integration
    try:
        # The exact CLI arguments for asking may depend on repowire versions.
        # Often it's an MCP proxy call or CLI command like `repowire ask`
        result = subprocess.run(
            ["repowire", "ask", "--peer", peer_name, "--message", question],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return f"\U0001f4e8 Sent message to {peer_name}:\n{result.stdout}"
        else:
            return f"Failed to send message to {peer_name}: {result.stderr}"
    except FileNotFoundError:
        return "Error: 'repowire' command not found."
    except Exception as e:
        return f"Error sending message: {e}"

def broadcast(message: str, player=None) -> str:
    """Broadcasts a message to all peers on the Repowire mesh."""
    try:
        result = subprocess.run(
            ["repowire", "broadcast", "--message", message],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return f"\U0001f4e3 Broadcasted message successfully."
        else:
            return f"Failed to broadcast message: {result.stderr}"
    except FileNotFoundError:
        return "Error: 'repowire' command not found."
    except Exception as e:
        return f"Error broadcasting message: {e}"

def repowire_mesh(parameters: dict, player=None) -> str:
    """
    Main dispatcher for Repowire Mesh interactions.
    actions: register, list, ask, broadcast
    """
    action = parameters.get("action")
    
    if action == "register":
        return register_peer(player)
    elif action == "list":
        return list_peers(player)
    elif action == "ask":
        peer_name = parameters.get("peer_name")
        question = parameters.get("question")
        if not peer_name or not question:
            return "Error: peer_name and question are required for 'ask' action."
        return ask_peer(peer_name, question, player)
    elif action == "broadcast":
        message = parameters.get("message")
        if not message:
            return "Error: message is required for 'broadcast' action."
        return broadcast(message, player)
    else:
        return f"Error: Unknown action '{action}' for repowire_mesh."
