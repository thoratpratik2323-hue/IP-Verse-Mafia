# actions/mythos_sentinel.py
"""
IP Prime — Mythos Sentinel Cybersecurity Engine
Focuses on advanced static security analysis, local open port vulnerability check,
CTF decode helper bridge, and cybersecurity tutor interface under the Mythos persona.
"""

import json
import csv
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    if not API_CONFIG_PATH.exists():
        return ""
    try:
        with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
            return config.get("gemini_api_key", "")
    except Exception:
        return ""

def _read_source_file(filepath: Path) -> str:
    """Reads a single file safely."""
    try:
        return filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading file: {e}"

def _scan_directory_files(dirpath: Path) -> str:
    """Collects up to 20 code files from directory for audit."""
    extensions = {".py", ".js", ".ts", ".c", ".cpp", ".h", ".java", ".go", ".rs", ".php", ".cs"}
    files = sorted(
        f for f in dirpath.rglob("*")
        if f.is_file() and f.suffix in extensions
        and not any(part.startswith(".") or part in ("__pycache__", "node_modules", "venv", ".venv") for part in f.parts)
    )[:20]

    if not files:
        return ""

    parts = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            parts.append(f"// === FILE: {f.relative_to(dirpath)} ===\n{content[:4000]}")
        except Exception:
            pass
    return "\n\n".join(parts)

def run_mythos_audit(target: str, player=None) -> str:
    """
    Performs a security-specific static audit with the Mythos persona.
    Focuses heavily on low-level memory leaks, buffer overflows, pointer vulnerabilities,
    logic bypasses, and patches.
    """
    def log(msg: str):
        if player:
            player.write_log(f"[MythosSentinel] {msg}")
        print(f"[MythosSentinel] {msg}")

    p = Path(target)
    if not p.exists():
        return f"Error: Path not found: {target}"

    log(f"Reading target source for Claude Mythos Audit: {target}")
    if p.is_file():
        source_code = _read_source_file(p)
        label = p.name
    else:
        source_code = _scan_directory_files(p)
        label = f"Directory: {p.name}"

    if not source_code.strip():
        return f"No code files found in {target} to audit."

    # Truncate source
    source_truncated = source_code[:20000]
    is_truncated = len(source_code) > 20000

    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing. Configure it in config/api_keys.json, sir."

    log("Initiating Claude Mythos audit engine via Gemini...")
    mythos_prompt = f"""You are Claude Mythos, a senior defensive cybersecurity analyst and low-level code auditor. 
Your specialty is finding memory unsafety, buffer overflows, memory leaks, race conditions, authentication bypasses, logical validation flaws, injection vectors, and design vulnerabilities in source code.

Provide a comprehensive, professional, and educational security audit of the following code. Write in a precise, helpful, and cyberpunk-toned style.

Target File/Project: {label}
{f"(Note: Some source files were truncated to fit context limits)" if is_truncated else ""}

Return a JSON document with the following schema:
{{
  "overall_security_score": 0-100,
  "summary": "High-level summary of security findings",
  "vulnerabilities": [
    {{
      "title": "Title of vulnerability",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "type": "e.g. Memory Leak, Buffer Overflow, SQLi, Logical Bypass",
      "file_line": "Filename and line range if applicable",
      "explanation": "Detailed explanation of how this vulnerability could be triggered theoretically.",
      "remediation": "Detailed secure patching advice and code snippet."
    }}
  ],
  "general_security_recommendations": [
    "General code safety recommendations"
  ]
}}

Return ONLY valid JSON. No markdown syntax wrapper, no notes outside the JSON block.

Source Code:
```
{source_truncated}
```"""

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=mythos_prompt
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-1.5-flash",
                contents=mythos_prompt
            )

        raw = response.text.strip()
        # Clean markdown wrappers if returned
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        data = json.loads(raw)
    except Exception as e:
        log(f"Audit generation failed or response parsing erred: {e}")
        return f"Mythos Audit failed: {e}\n\nRaw Model Output:\n{response.text if 'response' in locals() else 'None'}"

    # Format the report nicely
    score = data.get("overall_security_score", "N/A")
    summary = data.get("summary", "")
    vulns = data.get("vulnerabilities", [])
    recs = data.get("general_security_recommendations", [])

    lines = [
        "==========================================================",
        "          🛡️  CLAUDE MYTHOS SECURITY SENTINEL REPORT       ",
        "==========================================================",
        f"Target      : {label}",
        f"Safety Score: {score}/100",
        f"Summary     : {summary}",
        "----------------------------------------------------------",
        f"🚨 VULNERABILITIES DETECTED: {len(vulns)}",
    ]

    for i, v in enumerate(vulns, 1):
        lines.append(f"\n[{i}] {v.get('severity', 'LOW')} | {v.get('type', 'General')}")
        lines.append(f"    Title       : {v.get('title')}")
        lines.append(f"    Location    : {v.get('file_line')}")
        lines.append(f"    Description : {v.get('explanation')}")
        lines.append(f"    Remediation : {v.get('remediation')}")

    if recs:
        lines.append("\n💡 DEFENSIVE RECOMMENDATIONS:")
        for r in recs:
            lines.append(f"  * {r}")

    lines.append("\n[END OF REPORT] Mythos Sentinel Analysis Completed.")
    return "\n".join(lines)


def get_process_mapping() -> Dict[int, str]:
    """Generates a mapping from PID to Process Name on Windows."""
    mapping = {}
    try:
        res = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="replace")
        reader = csv.reader(res.stdout.splitlines())
        for row in reader:
            if len(row) >= 2:
                try:
                    name, pid_str = row[0], row[1]
                    mapping[int(pid_str)] = name
                except ValueError:
                    pass
    except Exception:
        pass
    return mapping


def run_system_vuln_check(player=None) -> str:
    """
    Checks active listening TCP/UDP ports on Windows via netstat.
    Correlates with process names and alerts on vulnerable exposures.
    """
    if player:
        player.write_log("[MythosSentinel] Starting local network audit...")

    pid_map = get_process_mapping()
    lines = [
        "==========================================================",
        "          🔍 MYTHOS LOCAL NETWORK AUDIT REPORT            ",
        "==========================================================",
        "Scanning active listening ports and processes...",
        ""
    ]

    try:
        # Run netstat -ano
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, errors="replace")
        netstat_lines = result.stdout.splitlines()
    except Exception as e:
        return f"Failed to query network connections: {e}"

    # Standard insecure ports
    insecure_ports = {
        21: ("FTP", "Unencrypted file transfers, credentials sent in cleartext."),
        22: ("SSH", "Secure shell (verify strong key auth, disable root password login)."),
        23: ("Telnet", "Extremely vulnerable, plaintext communications."),
        25: ("SMTP", "Simple Mail Transfer (check for open mail relay vulnerabilities)."),
        53: ("DNS", "Domain Name System (check for DNS spoofing or amplification vector)."),
        80: ("HTTP", "Unencrypted web traffic, sensitive cookies/data at risk of interception."),
        110: ("POP3", "Unencrypted mail retrieval."),
        135: ("RPC", "Windows RPC Endpoint Mapper (frequent target of remote exploits)."),
        139: ("NetBIOS", "NetBIOS Session Service (expose structural system paths)."),
        443: ("HTTPS", "Secure Web (check certificate validity and TLS version settings)."),
        445: ("SMB", "Microsoft SMB (extremely critical! WannaCry/EternalBlue exploit vector)."),
        1433: ("MSSQL", "Microsoft SQL Server database listener."),
        3306: ("MySQL", "MySQL database listener."),
        3389: ("RDP", "Remote Desktop Protocol (ensure network level authentication is active)."),
        8080: ("HTTP-Alt", "Alternative HTTP web server / proxy port.")
    }

    found_listening = []
    
    # regex to match: protocol, local addr, remote addr, state, pid
    # E.g.:  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1160
    # E.g.:  UDP    0.0.0.0:5353           *:*                                    2384
    pattern = re.compile(r"^\s*(TCP|UDP)\s+(\S+)\s+(\S+)(?:\s+(LISTENING|ESTABLISHED|TIME_WAIT|CLOSE_WAIT))?\s+(\d+)\s*$")

    for line in netstat_lines:
        m = pattern.match(line)
        if not m:
            continue
        proto, local_addr, remote_addr, state, pid_str = m.groups()
        pid = int(pid_str)

        # Only care about LISTENING TCP ports or UDP bindings
        if proto == "TCP" and state != "LISTENING":
            continue

        # Extract port
        port_match = re.search(r":(\d+)$", local_addr)
        if not port_match:
            continue
        port = int(port_match.group(1))

        proc_name = pid_map.get(pid, "Unknown Process")
        found_listening.append({
            "proto": proto,
            "port": port,
            "local": local_addr,
            "pid": pid,
            "process": proc_name
        })

    # Sort by port
    found_listening = sorted(found_listening, key=lambda x: x["port"])

    security_alerts = []
    lines.append(f"{'PROTO':<6} | {'PORT':<6} | {'PID':<6} | {'PROCESS NAME':<25} | {'LOCAL ADDRESS'}")
    lines.append("-" * 75)

    for entry in found_listening:
        lines.append(f"{entry['proto']:<6} | {entry['port']:<6} | {entry['pid']:<6} | {entry['process']:<25} | {entry['local']}")
        
        # Check if port is in insecure list
        if entry["port"] in insecure_ports:
            service_name, risk_desc = insecure_ports[entry["port"]]
            security_alerts.append(
                f"⚠️  ALERT: Port {entry['port']} ({service_name}) bound by '{entry['process']}' (PID {entry['pid']})\n"
                f"   Risk: {risk_desc}"
            )

    if security_alerts:
        lines.append("\n🚨 NETWORK VULNERABILITY ALERTS:")
        for alert in security_alerts:
            lines.append(alert)
    else:
        lines.append("\n🟢 No listening ports on standard insecure ports detected.")

    lines.append("\nLocal network safety scan complete.")
    return "\n".join(lines)


def mythos_sentinel(parameters: dict, player=None) -> str:
    """Main entry point for tool execution."""
    action = parameters.get("action", "").lower().strip()
    if not action:
        return "Error: parameter 'action' is required (audit, network_audit, tutor, decode)."

    if action == "audit":
        target = parameters.get("target", "").strip()
        if not target:
            return "Error: target file/folder is required for audit action."
        return run_mythos_audit(target, player=player)

    elif action == "network_audit":
        return run_system_vuln_check(player=player)

    elif action == "tutor":
        # Forward parameters to cyber_tutor
        try:
            from actions.cyber_tutor import cyber_tutor
            tutor_params = dict(parameters)
            tutor_params["action"] = parameters.get("sub_action", "list")
            return cyber_tutor(tutor_params, player=player)
        except Exception as e:
            return f"Error loading Cybersecurity Tutor: {e}"

    elif action == "decode":
        # Forward parameters to ctf_helper
        try:
            from actions.ctf_helper import ctf_helper
            ctf_params = dict(parameters)
            ctf_params["action"] = parameters.get("sub_action", "")
            return ctf_helper(ctf_params, player=player)
        except Exception as e:
            return f"Error loading CTF Helper: {e}"

    else:
        return f"Unknown action: '{action}'."
