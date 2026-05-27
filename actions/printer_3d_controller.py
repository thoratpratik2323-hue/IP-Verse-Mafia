"""
printer_3d_controller.py — OctoPrint 3D printer API control module for IP Prime.

Connects to OctoPrint REST APIs via OCTOPRINT_URL and OCTOPRINT_API_KEY to monitor
temperatures, manage print files, and start/pause/cancel G-code print jobs.
"""

from __future__ import annotations

import logging
import os
import requests
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("ip_prime.printer_3d_controller")

BASE_DIR = Path(__file__).resolve().parent.parent

def _get_api_headers() -> tuple[str, dict[str, str]]:
    url = os.environ.get("OCTOPRINT_URL", "http://localhost:5000").strip()
    key = os.environ.get("OCTOPRINT_API_KEY", "").strip()
    headers = {
        "X-Api-Key": key,
        "Content-Type": "application/json"
    }
    return url, headers

def get_printer_temps() -> str:
    """Queries printer extruder and heatbed temperature telemetry."""
    url, headers = _get_api_headers()
    
    if not os.environ.get("OCTOPRINT_API_KEY"):
        logger.info("OctoPrint credentials missing. Using simulation mode.")
        return (
            "### [3D PRINTER] Temperature Sensors (Simulated):\n"
            "• **Nozzle Extruder**: 205.4 °C (Target: 210.0 °C)\n"
            "• **Heatbed Surface**: 60.1 °C (Target: 60.0 °C)\n"
            "• **Chamber Ambient**: 28.5 °C\n\n"
            "Thermal parameters running safe, sir!"
        )

    try:
        res = requests.get(f"{url}/api/printer", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            temp = data.get("temperature", {})
            tool0 = temp.get("tool0", {})
            bed = temp.get("bed", {})
            return (
                f"### [3D PRINTER] Telemetry:\n"
                f"• Nozzle Temp: {tool0.get('actual', 0.0)} °C (Target: {tool0.get('target', 0.0)} °C)\n"
                f"• Bed Temp: {bed.get('actual', 0.0)} °C (Target: {bed.get('target', 0.0)} °C)\n"
            )
    except Exception as e:
        logger.error("OctoPrint API temp query failed: %s", e)
    return "Failed to connect to 3D printer API channels, sir."

def get_print_status() -> str:
    """Retrieves active print job progress percentages and estimated remaining time."""
    url, headers = _get_api_headers()
    
    if not os.environ.get("OCTOPRINT_API_KEY"):
        return (
            "### [3D PRINTER] Active Print Job (Simulated):\n"
            "• **File Name**: `cyberpunk_mask_v2.gcode`\n"
            "• **Progress**: **45.2% Complete**\n"
            "• **Nozzle Temp**: 210 °C\n"
            "• **Time Remaining**: 2h 15m\n"
        )

    try:
        res = requests.get(f"{url}/api/job", headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            progress = data.get("progress", {})
            job = data.get("job", {})
            file_name = job.get("file", {}).get("name", "N/A")
            pct = progress.get("completion", 0.0)
            eta = progress.get("printTimeLeft", 0)
            
            eta_str = f"{eta // 60}m" if eta else "Calculating..."
            return (
                f"### [3D PRINTER] Status:\n"
                f"• File Name: {file_name}\n"
                f"• Progress: {pct:.1f}% Complete\n"
                f"• Time Remaining: {eta_str}\n"
            )
    except Exception as e:
        logger.error("OctoPrint job status check failed: %s", e)
    return "Failed to query print job status, sir."

def manage_print_job(action: str, file_name: Optional[str] = None) -> str:
    """Dispatches start, pause, or cancel directives to printer jobs."""
    url, headers = _get_api_headers()
    
    if not os.environ.get("OCTOPRINT_API_KEY"):
        return f"Simulated printer directive success: {action.upper()} sent for job '{file_name or 'current'}'!"

    try:
        if action == "start" and file_name:
            # First select and start print
            payload = {"command": "select", "print": True}
            res = requests.post(f"{url}/api/files/local/{file_name}", json=payload, headers=headers, timeout=8)
        else:
            payload = {"command": action} # pause / cancel
            res = requests.post(f"{url}/api/job", json=payload, headers=headers, timeout=8)
            
        if res.status_code in [200, 204]:
            return f"3D Printer successfully executed print job command: {action.upper()}!"
    except Exception as e:
        logger.error("OctoPrint action POST failed: %s", e)
        
    return f"Failed to execute 3D printer command: {action.upper()}, sir."

def list_print_files() -> str:
    """Lists files uploaded on the printer local storage."""
    url, headers = _get_api_headers()
    if not os.environ.get("OCTOPRINT_API_KEY"):
        return (
            "### [3D PRINTER] Local G-code Files (Simulated):\n"
            "1. `cyberpunk_mask_v2.gcode` (14.2 MB)\n"
            "2. `phone_stand_outfit.gcode` (4.5 MB)\n"
        )
    try:
        res = requests.get(f"{url}/api/files", headers=headers, timeout=8)
        if res.status_code == 200:
            files = res.json().get("files", [])
            output = ["### [3D PRINTER] Files list:\n"]
            for idx, f in enumerate(files[:10], 1):
                output.append(f"{idx}. **{f.get('name')}** ({f.get('size', 0) / 1024 / 1024:.1f} MB)")
            return "\n".join(output)
    except Exception as e:
        logger.error("Failed to query OctoPrint Gcode files: %s", e)
    return "Could not load printer files, sir."

def printer_3d_controller(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main dispatcher for printer_3d_controller action."""
    action = parameters.get("action", "status").lower().strip()
    file_name = parameters.get("file_name", "")
    
    if action == "status":
        return get_print_status()
    elif action == "temps":
        return get_printer_temps()
    elif action == "start":
        return manage_print_job("start", file_name)
    elif action == "pause":
        return manage_print_job("pause")
    elif action == "cancel":
        return manage_print_job("cancel")
    elif action == "files":
        return list_print_files()
    else:
        return "Unknown 3D printer control action parameter, sir."
