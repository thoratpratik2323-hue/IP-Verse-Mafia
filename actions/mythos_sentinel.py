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
from typing import Dict

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
{"(Note: Some source files were truncated to fit context limits)" if is_truncated else ""}

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
                model="gemini-flash-latest",
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


def run_mythos_patcher(code: str, language: str, player=None) -> str:
    """
    Identifies vulnerabilities in a code snippet and refactors it to be secure,
    implementing secure logic bounds, input sanitization, and overflow protection.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    prompt = f"""You are Claude Mythos, a senior secure code refactoring engineer.
Audit the following {language} snippet for security flaws. Provide a complete patched secure rewrite of the code, and explain what vulnerability you mitigated.

Return your response in a JSON document with this exact schema:
{{
  "vulnerability_found": "Explanation of vulnerabilities detected",
  "secure_rewrite": "Provide the complete, compiler-ready patched source code code here",
  "explanation_of_fix": "Explain specifically what changes you made to prevent memory corruption, injection, or logical issues."
}}

Snippet:
```
{code}
```
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt
            )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        data = json.loads(raw)
        
        lines = [
            "==========================================================",
            "          🛠️  CLAUDE MYTHOS SECURE AUTO-PATCHER            ",
            "==========================================================",
            f"VULNERABILITY ID: {data.get('vulnerability_found')}",
            "",
            "⚙️ SECURE CODE REWRITE:",
            "----------------------------------------------------------",
            data.get('secure_rewrite', '// No rewrite generated.'),
            "----------------------------------------------------------",
            "",
            f"REMEDIATION EXPLANATION: {data.get('explanation_of_fix')}",
            "=========================================================="
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Secure Patch execution erred: {e}"


def run_stride_threat_model(architecture: str, player=None) -> str:
    """
    Evaluates system architectures against the Microsoft STRIDE framework.
    (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    prompt = f"""You are Claude Mythos, threat modeling expert. Assess the following system architecture description using the Microsoft STRIDE threat classification. Identify threat risks and map security controls.

Architecture:
{architecture}

Return your assessment as a JSON document:
{{
  "executive_summary": "Summary of system exposure",
  "stride_threats": {{
    "spoofing": {{"threat": "description of spoofing threat", "mitigation": "mitigation approach"}},
    "tampering": {{"threat": "description", "mitigation": "mitigation"}},
    "repudiation": {{"threat": "description", "mitigation": "mitigation"}},
    "info_disclosure": {{"threat": "description", "mitigation": "mitigation"}},
    "denial_of_service": {{"threat": "description", "mitigation": "mitigation"}},
    "elevation_of_privilege": {{"threat": "description", "mitigation": "mitigation"}}
  }},
  "security_controls": [
    "Recommended architecture security controls"
  ]
}}
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt
            )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        data = json.loads(raw)
        
        lines = [
            "==========================================================",
            "          🔒 CLAUDE MYTHOS STRIDE THREAT MODEL             ",
            "==========================================================",
            f"System Summary: {data.get('executive_summary')}",
            ""
        ]
        
        threats = data.get("stride_threats", {})
        for category, info in threats.items():
            lines.append(f"◈ {category.upper()}:")
            lines.append(f"  - Threat    : {info.get('threat')}")
            lines.append(f"  - Mitigation: {info.get('mitigation')}\n")

        lines.append("----------------------------------------------------------")
        lines.append("💡 ARCHITECTURAL CONTROLS:")
        for control in data.get("security_controls", []):
            lines.append(f"  * {control}")
        lines.append("==========================================================")
        return "\n".join(lines)
    except Exception as e:
        return f"Threat modeling analysis failed: {e}"


def run_asm_audit(assembly_text: str, player=None) -> str:
    """
    Decompiles and explains x86/ARM assembly instructions, identifying buffer offset risks,
    integer errors, and unsafe system calls.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    prompt = f"""You are Claude Mythos, a reverse engineering specialist. 
Examine this assembly/pseudocode listing. Detail the execution logic line-by-line and point out any memory unsafe boundaries or logic bypass vulnerabilities present.

Listing:
{assembly_text}

Return your assessment as a JSON document:
{{
  "compilation_targets": "Expected compiler/architecture context",
  "flow_analysis": "Step by step execution explanation",
  "potential_vulns": "Any overflow bounds or stack corruption issues detected",
  "ctf_notes": "Defensive recommendations or bypass keys for flag capture"
}}
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt
            )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        data = json.loads(raw)
        lines = [
            "==========================================================",
            "          🧩 CLAUDE MYTHOS ASSEMBLY/REVERSE AUDIT         ",
            "==========================================================",
            f"Arch Context   : {data.get('compilation_targets')}",
            "",
            "📖 EXECUTION FLOW ANALYSIS:",
            data.get('flow_analysis', ''),
            "",
            "🚨 CRITICAL OVERFLOW & BOUNDS RISKS:",
            data.get('potential_vulns', 'None identified.'),
            "",
            "⛳ CTF STRATEGY NOTES:",
            data.get('ctf_notes', 'N/A'),
            "=========================================================="
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Assembly audit failed: {e}"


def run_dependency_audit(manifest_path: str, player=None) -> str:
    """
    Statically audits requirements.txt or package.json files using Gemini,
    mapping library names to security considerations.
    """
    p = Path(manifest_path)
    if not p.exists() or not p.is_file():
        return f"Manifest file not found: {manifest_path}"

    content = _read_source_file(p)
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    prompt = f"""You are Claude Mythos, dependency compliance manager. Audit this library manifest file for security liabilities. Highlight packages with historical vulnerabilities and recommend clean patching.

Manifest Content:
{content}

Return your assessment as a JSON document:
{{
  "analyzed_manifest": "File format type",
  "alerts": [
    {{"library": "package-name", "cve_risks": "Description of vulnerability issues", "patch_version": "safe version target"}}
  ]
}}
"""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=prompt
            )

        raw = response.text.strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        data = json.loads(raw)
        alerts = data.get("alerts", [])
        
        lines = [
            "==========================================================",
            "          📦 CLAUDE MYTHOS DEPENDENCY AUDIT               ",
            "==========================================================",
            f"Manifest File  : {p.name}",
            f"Identified Format: {data.get('analyzed_manifest')}",
            f"Flagged Packages : {len(alerts)}",
            ""
        ]
        
        for i, alert in enumerate(alerts, 1):
            lines.append(f"[{i}] Package: '{alert.get('library')}'")
            lines.append(f"    Safety Risk : {alert.get('cve_risks')}")
            lines.append(f"    Patch Target: {alert.get('patch_version')}\n")
            
        lines.append("[END OF MANIFEST SCANS]")
        return "\n".join(lines)
    except Exception as e:
        return f"Dependency audit failed: {e}"



# ═══════════════════════════════════════════════════════════════════════════════
# 🧙 THE SAGE — ELITE HACKER ARSENAL (10 NEW MODULES)
# "Knowledge without action is merely philosophy. Action without knowledge is
#  blindness. The Sage walks the line between both."
# ═══════════════════════════════════════════════════════════════════════════════

def _sage_call(prompt: str, api_key: str) -> str:
    """Internal helper: makes a Gemini call with Sage fallback logic."""
    from google import genai
    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    except Exception:
        response = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
    return response.text.strip()


def _sage_json_call(prompt: str, api_key: str) -> dict:
    """Internal helper: makes a Gemini call and parses JSON response."""
    raw = _sage_call(prompt, api_key)
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        raw = raw.strip()
    return json.loads(raw)


SAGE_BANNER = """╔═══════════════════════════════════════════════════════════╗
║         🧙 THE SAGE — MYTHOS CYBERSECURITY ORACLE         ║
║   "In stillness, the shadow reveals all it conceals."     ║
╚═══════════════════════════════════════════════════════════╝"""


def run_recon_engine(target: str, player=None) -> str:
    """
    🔍 RECON ENGINE — OSINT on domain/IP: WHOIS-like analysis, DNS records,
    subdomains, geolocation, open port hints, and attack surface mapping.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    def log(msg): 
        if player: player.write_log(f"[SageRecon] {msg}")

    log(f"Initiating reconnaissance on target: {target}")

    prompt = f"""You are The Sage — a master OSINT and reconnaissance expert with decades of experience in cybersecurity. 
You perform passive intelligence gathering. Analyze the given target and provide the most thorough, realistic reconnaissance report possible.
Think like a penetration tester doing passive recon before active exploitation.

Target: {target}

Return a JSON document:
{{
  "sage_verdict": "One wise, dramatic sentence about this target's security posture",
  "target_type": "domain | ip | organization | email",
  "whois_intel": "Organization, registrar, registration dates, contact info patterns (simulate realistic inference)",
  "dns_records": ["List of likely DNS records: A, MX, NS, TXT, CNAME patterns"],
  "subdomains": ["List of likely subdomains based on common patterns: www, mail, api, admin, vpn, dev, staging, etc."],
  "geolocation": "Likely hosting location, CDN, cloud provider inference",
  "open_ports": ["List of commonly open ports for this type of target"],
  "technologies": ["Likely tech stack: web server, framework, CMS, etc."],
  "attack_surface": ["Potential attack vectors and entry points"],
  "osint_sources": ["Public sources to check: Shodan, Censys, VirusTotal, etc."],
  "sage_wisdom": "Strategic advice for a penetration tester approaching this target"
}}

Return ONLY valid JSON. No markdown wrapper."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            f"         🔍 RECON ENGINE — TARGET: {target}",
            "═══════════════════════════════════════════════════════════════",
            f"⚡ SAGE VERDICT: {data.get('sage_verdict')}",
            f"🎯 Target Type : {data.get('target_type')}",
            "",
            "🌐 WHOIS INTELLIGENCE:",
            f"  {data.get('whois_intel')}",
            "",
            "📡 DNS RECORDS:",
        ]
        for rec in data.get("dns_records", []):
            lines.append(f"  • {rec}")
        lines += ["", "🕸️  DISCOVERED SUBDOMAINS:"]
        for sub in data.get("subdomains", []):
            lines.append(f"  • {sub}")
        lines += [
            "",
            f"📍 GEOLOCATION: {data.get('geolocation')}",
            "",
            "🔓 OPEN PORTS LIKELY:",
        ]
        for port in data.get("open_ports", []):
            lines.append(f"  • {port}")
        lines += ["", "💻 TECHNOLOGIES DETECTED:"]
        for tech in data.get("technologies", []):
            lines.append(f"  • {tech}")
        lines += ["", "⚔️  ATTACK SURFACE:"]
        for vector in data.get("attack_surface", []):
            lines.append(f"  ▶ {vector}")
        lines += ["", "📚 OSINT SOURCES TO INVESTIGATE:"]
        for src in data.get("osint_sources", []):
            lines.append(f"  → {src}")
        lines += [
            "",
            "─────────────────────────────────────────────────────────────",
            f"🧙 SAGE WISDOM: {data.get('sage_wisdom')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Recon Engine failed: {e}"


def run_payload_forge(attack_type: str, context: str = "", player=None) -> str:
    """
    💣 PAYLOAD FORGE — Generates ethical pentesting payloads for CTF/security research.
    Covers XSS, SQLi, CSRF, LFI, RFI, Command Injection, SSRF, XXE.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageForge] Forging payloads for: {attack_type}")

    prompt = f"""You are The Sage — a master exploit developer and CTF champion. 
Generate a comprehensive, educational payload arsenal for the specified attack type. These are for legitimate security testing, CTF competitions, and penetration testing labs only.

Attack Type: {attack_type}
Context: {context if context else "General purpose / CTF / Lab environment"}

Return a JSON document:
{{
  "sage_intro": "Brief wise statement about this attack class",
  "attack_class": "The OWASP/CWE category",
  "payloads": [
    {{
      "name": "Payload name",
      "payload": "The actual payload string",
      "purpose": "What this payload achieves",
      "bypass_technique": "Any WAF bypass or encoding trick used"
    }}
  ],
  "detection_evasion": ["Ways to evade detection / WAF bypass techniques"],
  "testing_methodology": "Step-by-step approach to test for this vulnerability",
  "sage_warning": "Wise ethical reminder"
}}

Return ONLY valid JSON. No markdown wrapper. Generate at least 8-10 varied payloads."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            f"         💣 PAYLOAD FORGE — {attack_type.upper()}",
            "═══════════════════════════════════════════════════════════════",
            f"⚡ SAGE INTRO: {data.get('sage_intro')}",
            f"📂 Attack Class: {data.get('attack_class')}",
            "",
            "💥 GENERATED PAYLOAD ARSENAL:",
            "─────────────────────────────────────────────────────────────",
        ]
        for i, p in enumerate(data.get("payloads", []), 1):
            lines += [
                f"[{i}] {p.get('name')}",
                f"    PAYLOAD  : {p.get('payload')}",
                f"    PURPOSE  : {p.get('purpose')}",
                f"    BYPASS   : {p.get('bypass_technique')}",
                "",
            ]
        lines += [
            "🛡️  EVASION TECHNIQUES:",
        ]
        for ev in data.get("detection_evasion", []):
            lines.append(f"  • {ev}")
        lines += [
            "",
            f"📋 TESTING METHODOLOGY:\n  {data.get('testing_methodology')}",
            "",
            "─────────────────────────────────────────────────────────────",
            f"⚠️  SAGE WARNING: {data.get('sage_warning')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Payload Forge failed: {e}"


def run_hash_crack(hash_value: str, player=None) -> str:
    """
    🔐 HASH CRACKER — Identifies hash type and provides cracking strategy.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageHash] Analyzing hash: {hash_value[:20]}...")

    prompt = f"""You are The Sage — a master cryptanalyst. Analyze this hash value and provide complete cracking intelligence.

Hash: {hash_value}

Return a JSON document:
{{
  "sage_insight": "Wise observation about this hash",
  "hash_type": "Most likely hash algorithm (MD5/SHA1/SHA256/SHA512/bcrypt/NTLM/etc.)",
  "hash_length": "Length in bytes",
  "confidence": "HIGH/MEDIUM/LOW",
  "other_possible_types": ["Other possible hash types"],
  "cracking_tools": [
    {{"tool": "hashcat", "command": "exact hashcat command with mode flag", "mode": "mode number"}},
    {{"tool": "john", "command": "exact john command"}},
    {{"tool": "online", "url": "best online cracker URL", "notes": "usage notes"}}
  ],
  "wordlists": ["Recommended wordlists: rockyou.txt, etc."],
  "rainbow_tables": "Rainbow table lookup advice",
  "attack_modes": ["Dictionary, Brute-force, Rule-based, Combinator — recommended order"],
  "estimated_crack_time": "Estimated crack time for common hardware",
  "sage_strategy": "Overall wise cracking strategy recommendation"
}}

Return ONLY valid JSON. No markdown wrapper."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            "         🔐 HASH CRACKER — SAGE ANALYSIS",
            "═══════════════════════════════════════════════════════════════",
            f"HASH     : {hash_value}",
            f"⚡ INSIGHT: {data.get('sage_insight')}",
            "",
            f"📊 HASH TYPE     : {data.get('hash_type')} (Confidence: {data.get('confidence')})",
            f"📏 HASH LENGTH   : {data.get('hash_length')}",
        ]
        if data.get("other_possible_types"):
            lines.append(f"❓ ALSO COULD BE : {', '.join(data.get('other_possible_types', []))}")
        lines += [
            "",
            "⚔️  CRACKING COMMANDS:",
            "─────────────────────────────────────────────────────────────",
        ]
        for tool in data.get("cracking_tools", []):
            lines += [
                f"🔧 {tool.get('tool', '').upper()}:",
                f"   {tool.get('command', '')}",
                f"   {tool.get('notes', tool.get('url', ''))}",
                "",
            ]
        lines += [
            f"📚 WORDLISTS: {', '.join(data.get('wordlists', []))}",
            f"🌈 RAINBOW TABLES: {data.get('rainbow_tables')}",
            "",
            "📋 ATTACK ORDER:",
        ]
        for mode in data.get("attack_modes", []):
            lines.append(f"  → {mode}")
        lines += [
            "",
            f"⏱️  ESTIMATED CRACK TIME: {data.get('estimated_crack_time')}",
            "─────────────────────────────────────────────────────────────",
            f"🧙 SAGE STRATEGY: {data.get('sage_strategy')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Hash Cracker failed: {e}"


def run_web_scan(url: str, player=None) -> str:
    """
    🌐 WEB VULNERABILITY SCANNER — OWASP Top 10 analysis for a target URL.
    Checks headers, common misconfigs, injection points, CORS, clickjacking.
    """
    import urllib.request
    import urllib.error

    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageWebScan] Scanning: {url}")

    # Try to fetch headers passively
    headers_info = "Could not retrieve headers (offline/blocked)"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Security Scanner)"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            h = dict(resp.headers)
            security_headers = {
                k: v for k, v in h.items()
                if any(kw in k.lower() for kw in [
                    "x-frame", "content-security", "x-xss", "strict-transport",
                    "x-content-type", "referrer-policy", "permissions-policy",
                    "access-control"
                ])
            }
            headers_info = json.dumps(security_headers, indent=2) if security_headers else "No security headers detected!"
    except Exception as e:
        headers_info = f"Header fetch attempt failed: {e}"

    prompt = f"""You are The Sage — a master web application security expert specializing in OWASP Top 10.
Analyze the security posture of this web target and provide a thorough vulnerability assessment.

Target URL: {url}
Retrieved Security Headers:
{headers_info}

Perform a comprehensive OWASP Top 10 analysis and return a JSON document:
{{
  "sage_verdict": "Overall security posture verdict",
  "security_score": 0-100,
  "headers_analysis": {{
    "missing_critical": ["List of missing critical security headers"],
    "present_good": ["Security headers that ARE present"],
    "misconfigured": ["Headers that exist but have weak values"]
  }},
  "owasp_findings": [
    {{
      "category": "OWASP Top 10 category (e.g. A01:Injection)",
      "risk": "CRITICAL|HIGH|MEDIUM|LOW",
      "finding": "What was found or likely present",
      "test_vector": "How to test for this manually",
      "remediation": "How to fix"
    }}
  ],
  "cors_analysis": "CORS policy assessment",
  "tls_advice": "TLS/SSL configuration recommendations",
  "recommended_tools": ["Next-step tools: Burp Suite, OWASP ZAP, etc."],
  "sage_wisdom": "Master-level pentesting wisdom for this target"
}}

Return ONLY valid JSON. No markdown wrapper."""

    try:
        data = _sage_json_call(prompt, api_key)
        score = data.get("security_score", 0)
        score_bar = "█" * (score // 10) + "░" * (10 - score // 10)
        lines = [
            SAGE_BANNER,
            f"         🌐 WEB SCANNER — TARGET: {url}",
            "═══════════════════════════════════════════════════════════════",
            f"⚡ VERDICT  : {data.get('sage_verdict')}",
            f"📊 SCORE    : [{score_bar}] {score}/100",
            "",
            "🛡️  SECURITY HEADERS ANALYSIS:",
        ]
        h = data.get("headers_analysis", {})
        lines.append("  ✅ Present:")
        for hdr in h.get("present_good", []):
            lines.append(f"     • {hdr}")
        lines.append("  ❌ Missing (CRITICAL):")
        for hdr in h.get("missing_critical", []):
            lines.append(f"     • {hdr}")
        lines.append("  ⚠️  Misconfigured:")
        for hdr in h.get("misconfigured", []):
            lines.append(f"     • {hdr}")
        lines += ["", "🔴 OWASP TOP 10 FINDINGS:", "─────────────────────────────────────────────────────────────"]
        for i, finding in enumerate(data.get("owasp_findings", []), 1):
            lines += [
                f"[{i}] {finding.get('risk')} | {finding.get('category')}",
                f"    Finding     : {finding.get('finding')}",
                f"    Test Vector : {finding.get('test_vector')}",
                f"    Remediation : {finding.get('remediation')}",
                "",
            ]
        lines += [
            f"🔗 CORS    : {data.get('cors_analysis')}",
            f"🔒 TLS/SSL : {data.get('tls_advice')}",
            "",
            "🔧 RECOMMENDED NEXT TOOLS:",
        ]
        for tool in data.get("recommended_tools", []):
            lines.append(f"  → {tool}")
        lines += [
            "",
            "─────────────────────────────────────────────────────────────",
            f"🧙 SAGE WISDOM: {data.get('sage_wisdom')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Web Scanner failed: {e}"


def run_exploit_suggest(software: str, version: str = "", player=None) -> str:
    """
    🧬 EXPLOIT SUGGESTER — Maps software + version to known CVEs and exploit strategies.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageExploit] Researching: {software} {version}")

    prompt = f"""You are The Sage — a master vulnerability researcher with encyclopedic knowledge of CVEs and exploit development.
Provide a comprehensive exploit intelligence report for the given software.

Software: {software}
Version: {version if version else "Unknown/Latest"}

Return a JSON document:
{{
  "sage_assessment": "Strategic assessment of this software's attack potential",
  "software_category": "What type of software this is",
  "severity_rating": "CRITICAL|HIGH|MEDIUM|LOW",
  "known_cves": [
    {{
      "cve_id": "CVE-YYYY-XXXXX",
      "cvss_score": "X.X",
      "description": "Vulnerability description",
      "exploit_type": "RCE|LPE|DoS|InfoDisclosure|etc.",
      "exploit_available": true/false,
      "exploit_db_id": "EDB-XXXXX or N/A",
      "patch_version": "Version that fixes this"
    }}
  ],
  "attack_vectors": ["Most effective attack approaches"],
  "exploitation_difficulty": "EASY|MEDIUM|HARD|EXPERT",
  "post_exploitation": ["What can be done after successful exploitation"],
  "detection_indicators": ["IoCs and detection signatures"],
  "mitigation": ["Immediate mitigations before patching"],
  "sage_warning": "Ethical reminder and responsible disclosure note"
}}

Return ONLY valid JSON. No markdown wrapper. Be specific with real CVE patterns."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            f"         🧬 EXPLOIT SUGGESTER — {software} {version}",
            "═══════════════════════════════════════════════════════════════",
            f"⚡ ASSESSMENT  : {data.get('sage_assessment')}",
            f"🎯 Category    : {data.get('software_category')}",
            f"🔴 Severity    : {data.get('severity_rating')}",
            f"⚔️  Difficulty  : {data.get('exploitation_difficulty')}",
            "",
            "💀 KNOWN CVEs:",
            "─────────────────────────────────────────────────────────────",
        ]
        for cve in data.get("known_cves", []):
            exploit_flag = "✅ Exploit Available" if cve.get("exploit_available") else "⚠️ No Public Exploit"
            lines += [
                f"📌 {cve.get('cve_id')} | CVSS: {cve.get('cvss_score')} | {cve.get('exploit_type')}",
                f"   {cve.get('description')}",
                f"   {exploit_flag} | EDB: {cve.get('exploit_db_id')} | Fixed in: {cve.get('patch_version')}",
                "",
            ]
        lines += ["⚔️  ATTACK VECTORS:"]
        for vec in data.get("attack_vectors", []):
            lines.append(f"  ▶ {vec}")
        lines += ["", "🏴 POST-EXPLOITATION:"]
        for pe in data.get("post_exploitation", []):
            lines.append(f"  • {pe}")
        lines += ["", "🔍 DETECTION INDICATORS:"]
        for ioc in data.get("detection_indicators", []):
            lines.append(f"  → {ioc}")
        lines += ["", "🛡️  IMMEDIATE MITIGATIONS:"]
        for mit in data.get("mitigation", []):
            lines.append(f"  ✓ {mit}")
        lines += [
            "",
            "─────────────────────────────────────────────────────────────",
            f"⚠️  SAGE WARNING: {data.get('sage_warning')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Exploit Suggester failed: {e}"


def run_osint_dossier(target: str, target_type: str = "domain", player=None) -> str:
    """
    🕵️ OSINT DOSSIER — Comprehensive intelligence report on domain/email/username/org.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageOSINT] Building dossier on: {target}")

    prompt = f"""You are The Sage — a legendary OSINT investigator with access to all public intelligence methodologies.
Build a comprehensive OSINT dossier on the given target using only legally available public information techniques.

Target: {target}
Target Type: {target_type}

Return a JSON document:
{{
  "sage_profile": "High-level intelligence profile summary",
  "confidence_level": "HIGH/MEDIUM/LOW",
  "identity_intel": {{
    "real_name_or_org": "Inferred identity or organization",
    "location": "Geographic location hints",
    "timezone": "Likely timezone",
    "language": "Primary language"
  }},
  "digital_footprint": [
    {{"platform": "Platform name", "username": "likely handle", "profile_url": "example URL pattern", "activity": "Activity level/type"}}
  ],
  "technical_artifacts": {{
    "email_patterns": ["Likely email format patterns"],
    "ip_ranges": ["Associated IP ranges or ASNs"],
    "domain_history": "Domain registration history patterns"
  }},
  "social_connections": ["Key associated entities or connections"],
  "data_breach_exposure": "Likely breach exposure based on age/type of target",
  "investigation_tools": [
    {{"tool": "Tool name", "url": "URL", "use_case": "What to use it for"}}
  ],
  "timeline": ["Key events or activity patterns"],
  "sage_intelligence": "Master analyst conclusion and next investigation steps"
}}

Return ONLY valid JSON. No markdown wrapper."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            f"         🕵️ OSINT DOSSIER — TARGET: {target}",
            "═══════════════════════════════════════════════════════════════",
            f"⚡ PROFILE      : {data.get('sage_profile')}",
            f"📊 CONFIDENCE  : {data.get('confidence_level')}",
            "",
            "🆔 IDENTITY INTELLIGENCE:",
        ]
        identity = data.get("identity_intel", {})
        for k, v in identity.items():
            lines.append(f"  {k.replace('_', ' ').title()}: {v}")
        lines += ["", "🌐 DIGITAL FOOTPRINT:"]
        for fp in data.get("digital_footprint", []):
            lines += [
                f"  📱 {fp.get('platform')}:",
                f"     Handle  : {fp.get('username')}",
                f"     URL     : {fp.get('profile_url')}",
                f"     Activity: {fp.get('activity')}",
                "",
            ]
        tech = data.get("technical_artifacts", {})
        lines += [
            "⚙️  TECHNICAL ARTIFACTS:",
            f"  Email Patterns : {', '.join(tech.get('email_patterns', []))}",
            f"  IP/ASN Ranges  : {', '.join(tech.get('ip_ranges', []))}",
            f"  Domain History : {tech.get('domain_history')}",
            "",
            "🔗 SOCIAL CONNECTIONS:",
        ]
        for conn in data.get("social_connections", []):
            lines.append(f"  • {conn}")
        lines += [
            "",
            f"💾 DATA BREACH EXPOSURE: {data.get('data_breach_exposure')}",
            "",
            "🛠️  INVESTIGATION TOOLS:",
        ]
        for tool in data.get("investigation_tools", []):
            lines.append(f"  [{tool.get('tool')}] {tool.get('url')} — {tool.get('use_case')}")
        lines += [
            "",
            "📅 ACTIVITY TIMELINE:",
        ]
        for event in data.get("timeline", []):
            lines.append(f"  → {event}")
        lines += [
            "",
            "─────────────────────────────────────────────────────────────",
            f"🧙 SAGE INTELLIGENCE: {data.get('sage_intelligence')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"OSINT Dossier failed: {e}"


def run_blue_team_defender(threat_scenario: str, player=None) -> str:
    """
    🛡️ BLUE TEAM DEFENDER — Generates SIEM rules, firewall rules, IDS signatures.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageBlueTeam] Building defenses for: {threat_scenario[:50]}")

    prompt = f"""You are The Sage — a legendary Blue Team defender and SOC architect who has protected critical infrastructure for decades.
Generate comprehensive defensive rules and detection signatures for the described threat scenario.

Threat Scenario: {threat_scenario}

Return a JSON document:
{{
  "sage_defense_doctrine": "Core defensive philosophy for this threat",
  "threat_classification": "APT group / malware family / attack technique classification",
  "mitre_ttps": ["MITRE ATT&CK TTPs: e.g. T1059.001 PowerShell Execution"],
  "siem_rules": [
    {{"platform": "Splunk/Elastic/QRadar", "rule_name": "rule name", "rule": "actual rule query syntax", "explanation": "what it detects"}}
  ],
  "firewall_rules": [
    {{"type": "Windows Firewall/iptables/pf", "rule": "exact rule syntax", "purpose": "purpose"}}
  ],
  "ids_signatures": [
    {{"platform": "Snort/Suricata", "signature": "alert rule syntax", "sid": "SID number"}}
  ],
  "yara_rule": "Complete YARA rule for malware detection",
  "iocs": {{
    "ip_addresses": ["Suspicious IPs to block"],
    "domains": ["Malicious domains"],
    "file_hashes": ["MD5/SHA256 hashes"],
    "registry_keys": ["Malicious registry keys to monitor"],
    "file_paths": ["Suspicious file paths"]
  }},
  "incident_response_steps": ["Step-by-step IR playbook"],
  "sage_counter_strategy": "Master-level defensive counter-strategy"
}}

Return ONLY valid JSON. No markdown wrapper. Generate real, deployable rules."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            "         🛡️ BLUE TEAM DEFENDER — ACTIVE DEFENSE",
            "═══════════════════════════════════════════════════════════════",
            f"⚡ DOCTRINE    : {data.get('sage_defense_doctrine')}",
            f"🎯 Threat Class: {data.get('threat_classification')}",
            "",
            "🗺️  MITRE ATT&CK TTPs:",
        ]
        for ttp in data.get("mitre_ttps", []):
            lines.append(f"  • {ttp}")
        lines += ["", "📊 SIEM DETECTION RULES:", "─────────────────────────────────────────────────────────────"]
        for rule in data.get("siem_rules", []):
            lines += [
                f"🔍 [{rule.get('platform')}] {rule.get('rule_name')}",
                f"   {rule.get('rule')}",
                f"   → {rule.get('explanation')}",
                "",
            ]
        lines += ["🔥 FIREWALL RULES:"]
        for fw in data.get("firewall_rules", []):
            lines += [
                f"  [{fw.get('type')}] {fw.get('rule')}",
                f"  Purpose: {fw.get('purpose')}",
                "",
            ]
        lines += ["🚨 IDS/IPS SIGNATURES:"]
        for sig in data.get("ids_signatures", []):
            lines += [
                f"  [{sig.get('platform')}] SID:{sig.get('sid')}",
                f"  {sig.get('signature')}",
                "",
            ]
        lines += [
            "🔬 YARA RULE:",
            data.get("yara_rule", "N/A"),
            "",
            "📍 INDICATORS OF COMPROMISE:",
        ]
        iocs = data.get("iocs", {})
        for k, vals in iocs.items():
            if vals:
                lines.append(f"  {k.replace('_', ' ').upper()}:")
                for v in vals:
                    lines.append(f"    • {v}")
        lines += ["", "🚒 INCIDENT RESPONSE PLAYBOOK:"]
        for i, step in enumerate(data.get("incident_response_steps", []), 1):
            lines.append(f"  {i}. {step}")
        lines += [
            "",
            "─────────────────────────────────────────────────────────────",
            f"🧙 SAGE COUNTER-STRATEGY: {data.get('sage_counter_strategy')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Blue Team Defender failed: {e}"


def run_crypto_breaker(cipher_text: str, hints: str = "", player=None) -> str:
    """
    🔑 CRYPTO BREAKER — Analyzes encrypted/encoded text and suggests decryption strategy.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageCrypto] Analyzing ciphertext: {cipher_text[:30]}...")

    prompt = f"""You are The Sage — a grandmaster cryptanalyst who has broken every cipher from Caesar to AES.
Analyze this ciphertext and provide complete decryption intelligence.

Ciphertext: {cipher_text}
Hints: {hints if hints else "None provided"}

Return a JSON document:
{{
  "sage_read": "What The Sage perceives immediately about this ciphertext",
  "likely_encoding": "First layer: base64/hex/url-encode/etc.",
  "cipher_type": "Most likely cipher type",
  "confidence": "HIGH/MEDIUM/LOW",
  "frequency_analysis": "Letter/character frequency observations",
  "key_length_estimate": "Estimated key length if applicable",
  "decryption_attempts": [
    {{
      "method": "Decryption method name",
      "key_or_params": "Key or parameters used",
      "result": "Decrypted text or partial result",
      "success": true/false
    }}
  ],
  "tools_to_use": [
    {{"tool": "Tool/website name", "url": "URL", "how": "How to use for this cipher"}}
  ],
  "python_code": "Python code to decrypt this",
  "ctf_meta": "CTF-specific notes (steganography hints, hidden data, etc.)",
  "sage_solution": "The Sage's best decryption path recommendation"
}}

Return ONLY valid JSON. No markdown wrapper. Try actual decryption attempts where possible."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            "         🔑 CRYPTO BREAKER — SAGE CRYPTANALYSIS",
            "═══════════════════════════════════════════════════════════════",
            f"INPUT    : {cipher_text[:80]}{'...' if len(cipher_text) > 80 else ''}",
            "",
            f"⚡ SAGE READ   : {data.get('sage_read')}",
            f"📦 ENCODING    : {data.get('likely_encoding')}",
            f"🔐 CIPHER TYPE : {data.get('cipher_type')} (Confidence: {data.get('confidence')})",
            f"📊 FREQUENCY   : {data.get('frequency_analysis')}",
            f"🔑 KEY LENGTH  : {data.get('key_length_estimate')}",
            "",
            "⚗️  DECRYPTION ATTEMPTS:",
            "─────────────────────────────────────────────────────────────",
        ]
        for attempt in data.get("decryption_attempts", []):
            status = "✅ SUCCESS" if attempt.get("success") else "❌ FAILED"
            lines += [
                f"{status} | {attempt.get('method')}",
                f"  Key/Params: {attempt.get('key_or_params')}",
                f"  Result    : {attempt.get('result')}",
                "",
            ]
        lines += ["🔧 RECOMMENDED TOOLS:"]
        for tool in data.get("tools_to_use", []):
            lines.append(f"  [{tool.get('tool')}] {tool.get('url')} — {tool.get('how')}")
        lines += [
            "",
            "🐍 PYTHON DECRYPTION CODE:",
            "─────────────────────────────────────────────────────────────",
            data.get("python_code", "# No code generated"),
            "─────────────────────────────────────────────────────────────",
            f"🏴 CTF NOTES: {data.get('ctf_meta')}",
            "",
            f"🧙 SAGE SOLUTION: {data.get('sage_solution')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Crypto Breaker failed: {e}"


def run_network_mapper(player=None) -> str:
    """
    📡 NETWORK MAPPER — Maps local network devices using ARP/ping sweep.
    """
    if player: player.write_log("[SageNetmap] Mapping local network...")

    lines_out = [
        SAGE_BANNER,
        "         📡 NETWORK MAPPER — LOCAL RECON",
        "═══════════════════════════════════════════════════════════════",
        "Initiating ARP sweep + host discovery...",
        "",
    ]

    try:
        # Get local IP and subnet
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        lines_out.append(f"🖥️  Local Host   : {hostname}")
        lines_out.append(f"📍 Local IP     : {local_ip}")

        # Try arp -a (works on Windows & Linux/Mac)
        arp_result = subprocess.run(["arp", "-a"], capture_output=True, text=True, errors="replace", timeout=15)
        arp_lines = arp_result.stdout.splitlines()

        devices = []
        arp_pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([\w\-:]+)\s+(\w+)")
        for line in arp_lines:
            m = arp_pattern.search(line)
            if m:
                ip, mac, addr_type = m.group(1), m.group(2), m.group(3)
                if not ip.endswith(".255") and not ip.startswith("224."):
                    devices.append({"ip": ip, "mac": mac, "type": addr_type})

        lines_out += [
            "",
            f"🔍 ARP TABLE — {len(devices)} devices discovered:",
            "─────────────────────────────────────────────────────────────",
            f"{'IP ADDRESS':<18} {'MAC ADDRESS':<20} {'TYPE':<12} {'VENDOR HINT'}",
            "─" * 70,
        ]

        # MAC vendor prefixes (common)
        vendor_map = {
            "00:50:56": "VMware", "00:0c:29": "VMware VM", "08:00:27": "VirtualBox",
            "dc:a6:32": "Raspberry Pi", "b8:27:eb": "Raspberry Pi", "00:1a:11": "Google",
            "f0:18:98": "Apple", "3c:22:fb": "Apple", "ac:de:48": "Apple",
            "00:1b:63": "Apple", "a4:c3:f0": "Google Nest", "18:b4:30": "Nest Labs",
        }

        for dev in devices:
            mac_prefix = dev["mac"][:8].upper().replace("-", ":")
            vendor = next((v for k, v in vendor_map.items() if mac_prefix.startswith(k.upper())), "Unknown Vendor")
            lines_out.append(f"{dev['ip']:<18} {dev['mac']:<20} {dev['type']:<12} {vendor}")

        lines_out += [
            "",
            "─────────────────────────────────────────────────────────────",
            "🧙 SAGE NOTE: Run Nmap for deeper service discovery.",
            "   Try: nmap -sV -O <target_ip> for full OS + service fingerprinting",
            "   Try: nmap -sS -p- --open <subnet> for stealth TCP SYN scan",
            "═══════════════════════════════════════════════════════════════",
        ]

    except Exception as e:
        lines_out.append(f"Network mapper error: {e}")

    return "\n".join(lines_out)


def run_shell_crafter(shell_type: str, lhost: str = "10.10.10.1", lport: str = "4444", player=None) -> str:
    """
    🐚 SHELL CRAFTER — Generates reverse/bind shell one-liners for pentesting/CTF.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageShell] Crafting {shell_type} shell...")

    prompt = f"""You are The Sage — a master exploit developer who can craft shells in any language or environment.
Generate a comprehensive shell arsenal for penetration testing and CTF scenarios.

Shell Type: {shell_type}
LHOST (attacker IP): {lhost}
LPORT (listener port): {lport}

Return a JSON document:
{{
  "sage_note": "Tactical wisdom about shell selection",
  "shells": [
    {{
      "name": "Shell name",
      "language": "bash/python/powershell/php/ruby/perl/netcat/socat/etc.",
      "payload": "The exact shell command/payload",
      "listener": "The exact listener command to run on attacker machine",
      "stealth_rating": "1-10 stealth rating",
      "notes": "When to use this variant"
    }}
  ],
  "payload_encoders": ["Ways to encode/obfuscate the payload"],
  "upgrade_shell": ["Commands to upgrade from dumb shell to fully interactive TTY"],
  "msfvenom_examples": ["msfvenom commands for advanced payloads"],
  "sage_tactic": "Master-level shell selection strategy"
}}

Return ONLY valid JSON. No markdown wrapper. Include at least 8-10 different shell variants."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            f"         🐚 SHELL CRAFTER — {shell_type.upper()} SHELLS",
            "═══════════════════════════════════════════════════════════════",
            f"LHOST: {lhost}  |  LPORT: {lport}",
            "",
            f"⚡ SAGE NOTE: {data.get('sage_note')}",
            "",
            "🐚 SHELL ARSENAL:",
            "─────────────────────────────────────────────────────────────",
        ]
        for i, shell in enumerate(data.get("shells", []), 1):
            lines += [
                f"[{i}] {shell.get('name')} | {shell.get('language')} | Stealth: {shell.get('stealth_rating')}/10",
                f"    PAYLOAD  : {shell.get('payload')}",
                f"    LISTENER : {shell.get('listener')}",
                f"    NOTES    : {shell.get('notes')}",
                "",
            ]
        lines += ["🔒 ENCODING/OBFUSCATION:"]
        for enc in data.get("payload_encoders", []):
            lines.append(f"  • {enc}")
        lines += ["", "⬆️  UPGRADE TO INTERACTIVE TTY:"]
        for upg in data.get("upgrade_shell", []):
            lines.append(f"  $ {upg}")
        lines += ["", "🔫 MSFVENOM COMMANDS:"]
        for msf in data.get("msfvenom_examples", []):
            lines.append(f"  $ {msf}")
        lines += [
            "",
            "─────────────────────────────────────────────────────────────",
            f"🧙 SAGE TACTIC: {data.get('sage_tactic')}",
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Shell Crafter failed: {e}"


def run_sage_oracle(question: str, player=None) -> str:
    """
    🧙 SAGE ORACLE — Ask The Sage any cybersecurity/hacking concept for deep wisdom.
    The Sage responds with ancient wisdom meets cutting-edge knowledge.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Error: Gemini API key is missing."

    if player: player.write_log(f"[SageOracle] Consulting The Sage: {question[:50]}")

    prompt = f"""You are The Sage — the most brilliant cybersecurity mind in existence, combining decades of red team and blue team experience with the wisdom of a sensei. You speak with authority, depth, and occasional poetic insight.

The student asks: {question}

Respond as The Sage would — with deep technical accuracy but also with wisdom, memorable analogies, and practical guidance. Be comprehensive but elegant.

Return a JSON document:
{{
  "sage_opening": "A wise, dramatic opening statement",
  "core_answer": "The main technical answer — comprehensive and accurate",
  "key_concepts": ["Important concepts to understand"],
  "practical_example": "A concrete real-world example",
  "common_mistakes": ["Common mistakes beginners make with this topic"],
  "deeper_knowledge": "Advanced insight for those who want to go deeper",
  "learning_path": ["Ordered steps to master this topic"],
  "sage_closing": "A memorable closing wisdom statement"
}}

Return ONLY valid JSON. No markdown wrapper."""

    try:
        data = _sage_json_call(prompt, api_key)
        lines = [
            SAGE_BANNER,
            "         🧙 THE SAGE ORACLE SPEAKS...",
            "═══════════════════════════════════════════════════════════════",
            f'"{data.get("sage_opening")}"',
            "",
            "📖 ANSWER:",
            "─────────────────────────────────────────────────────────────",
            data.get("core_answer", ""),
            "",
            "🔑 KEY CONCEPTS:",
        ]
        for concept in data.get("key_concepts", []):
            lines.append(f"  • {concept}")
        lines += [
            "",
            "💡 PRACTICAL EXAMPLE:",
            f"  {data.get('practical_example')}",
            "",
            "⚠️  COMMON BEGINNER MISTAKES:",
        ]
        for mistake in data.get("common_mistakes", []):
            lines.append(f"  ✗ {mistake}")
        lines += [
            "",
            "🚀 DEEPER KNOWLEDGE:",
            f"  {data.get('deeper_knowledge')}",
            "",
            "📚 MASTERY LEARNING PATH:",
        ]
        for i, step in enumerate(data.get("learning_path", []), 1):
            lines.append(f"  {i}. {step}")
        lines += [
            "",
            "─────────────────────────────────────────────────────────────",
            f'🧙 THE SAGE CLOSES: "{data.get("sage_closing")}"',
            "═══════════════════════════════════════════════════════════════",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Sage Oracle failed: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DISPATCHER — Updated with all new hacker tools
# ═══════════════════════════════════════════════════════════════════════════════

def mythos_sentinel(parameters: dict, player=None) -> str:
    """Main entry point for tool execution — The Sage Hacker Arsenal."""
    action = parameters.get("action", "").lower().strip()
    if not action:
        return (
            "Error: 'action' parameter required.\n"
            "Available: audit | network_audit | tutor | decode | threat_model | patch_code\n"
            "Elite Hacker: recon | payload_forge | hash_crack | web_scan | exploit_suggest\n"
            "            | osint_dossier | blue_team | crypto_break | network_map | shell_craft\n"
            "Sage Mode  : sage_oracle"
        )

    # ── Legacy tools ──────────────────────────────────────────────────────────
    if action == "audit":
        target = parameters.get("target", "").strip()
        if not target:
            return "Error: target file/folder is required for audit action."
        return run_mythos_audit(target, player=player)

    elif action == "network_audit":
        return run_system_vuln_check(player=player)

    elif action == "threat_model":
        architecture = parameters.get("target", "").strip()
        if not architecture:
            return "Error: architecture description target is required."
        return run_stride_threat_model(architecture, player=player)

    elif action == "patch_code":
        code_content = parameters.get("text", "").strip()
        language = parameters.get("target", "C/C++").strip()
        if not code_content:
            return "Error: text parameter representing vulnerable code is required."
        return run_mythos_patcher(code_content, language, player=player)

    elif action == "tutor":
        return "The local Cybersecurity Tutor tool has been decommissioned. Please leverage my native LLM capabilities directly for tutoring, roadmap planning, and quizzes on cybersecurity topics."

    elif action == "decode":
        sub_action = parameters.get("sub_action", "").lower().strip()
        if sub_action == "asm_auditor":
            return run_asm_audit(parameters.get("text", ""), player=player)
        elif sub_action == "dependency_auditor":
            return run_dependency_audit(parameters.get("file_path", ""), player=player)
        else:
            return f"Decoding operations for '{sub_action}' have been decommissioned from the local helper. Please leverage my native LLM capabilities directly to decode Morse, Base64, Hex, ROT13, Caesar ciphers, or identify hashes."

    # ── ELITE HACKER ARSENAL ──────────────────────────────────────────────────
    elif action == "recon":
        target = parameters.get("target", "").strip()
        if not target:
            return "Error: target (domain/IP/org) is required for recon."
        return run_recon_engine(target, player=player)

    elif action == "payload_forge":
        attack_type = parameters.get("target", parameters.get("attack_type", "XSS")).strip()
        context = parameters.get("text", "").strip()
        return run_payload_forge(attack_type, context, player=player)

    elif action == "hash_crack":
        hash_value = parameters.get("target", parameters.get("text", "")).strip()
        if not hash_value:
            return "Error: hash value is required for hash_crack."
        return run_hash_crack(hash_value, player=player)

    elif action == "web_scan":
        url = parameters.get("target", parameters.get("url", "")).strip()
        if not url:
            return "Error: URL is required for web_scan."
        if not url.startswith("http"):
            url = "https://" + url
        return run_web_scan(url, player=player)

    elif action == "exploit_suggest":
        software = parameters.get("target", parameters.get("software", "")).strip()
        version = parameters.get("version", parameters.get("text", "")).strip()
        if not software:
            return "Error: software name is required for exploit_suggest."
        return run_exploit_suggest(software, version, player=player)

    elif action == "osint_dossier":
        target = parameters.get("target", "").strip()
        target_type = parameters.get("target_type", "domain").strip()
        if not target:
            return "Error: target is required for osint_dossier."
        return run_osint_dossier(target, target_type, player=player)

    elif action == "blue_team":
        scenario = parameters.get("target", parameters.get("text", "")).strip()
        if not scenario:
            return "Error: threat scenario description is required for blue_team."
        return run_blue_team_defender(scenario, player=player)

    elif action == "crypto_break":
        cipher_text = parameters.get("target", parameters.get("text", "")).strip()
        hints = parameters.get("hints", "").strip()
        if not cipher_text:
            return "Error: ciphertext is required for crypto_break."
        return run_crypto_breaker(cipher_text, hints, player=player)

    elif action == "network_map":
        return run_network_mapper(player=player)

    elif action == "shell_craft":
        shell_type = parameters.get("target", parameters.get("shell_type", "reverse")).strip()
        lhost = parameters.get("lhost", "10.10.10.1").strip()
        lport = parameters.get("lport", "4444").strip()
        return run_shell_crafter(shell_type, lhost, lport, player=player)

    elif action == "sage_oracle":
        question = parameters.get("text", parameters.get("target", "")).strip()
        if not question:
            return "Error: question/topic is required for sage_oracle."
        return run_sage_oracle(question, player=player)

    else:
        return f"Unknown action: '{action}'. The Sage knows these paths: audit | network_audit | threat_model | patch_code | tutor | decode | recon | payload_forge | hash_crack | web_scan | exploit_suggest | osint_dossier | blue_team | crypto_break | network_map | shell_craft | sage_oracle"
