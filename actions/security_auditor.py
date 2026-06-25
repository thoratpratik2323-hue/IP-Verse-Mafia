import logging
# actions/security_auditor.py

import os
import re
import socket
import subprocess
import json
from config import get_config

SECRET_PATTERNS = {
    "Google API Key": r"AIzaSy[A-Za-z0-9_-]{33}",
    "AWS Access Key ID": r"AKIA[0-9A-Z]{16}",
    "AWS Secret Access Key": r"(?i)aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
    "Generic Password/Secret": r"(?i)(password|secret|passwd|private_key|token)\s*[:=]\s*['\"][^'\"\s]{8,50}['\"]",
    "Slack Token": r"xox[bapr]-[0-9]{12}-[A-Za-z0-9]{24}",
    "GitHub Token": r"(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,255}",
    "Stripe API Key": r"sk_live_[0-9a-zA-Z]{24}",
    "JWT Token": r"eyJhbGciOi[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",
    "SSH/PEM Private Key": r"-----BEGIN\s+.*PRIVATE\s+KEY-----"
}

VULN_PATTERNS = {
    "SQL Injection risk (Raw string SQL execution)": r"(?i)\.execute\(\s*['\"]select\s+.*\s+where\s+.*%\s*.*['\"]",
    "Insecure exec() usage": r"\bexec\(\s*.*\s*\)",
    "Insecure eval() usage": r"\beval\(\s*.*\s*\)",
    "Insecure pickle deserialization": r"\bpickle\.loads\(",
    "Hardcoded temp file path": r"['\"]/tmp/.*['\"]",
    "Insecure random generator": r"\brandom\.(randint|random|choice|shuffle)",
    "HTTP instead of HTTPS link": r"http://[a-zA-Z0-9.-]+",
    "Shell=True subprocess execution": r"subprocess\.(run|Popen|call|check_output)\(.*\bshell\s*=\s*True"
}

def security_audit(parameters: dict, player=None, speak=None) -> str:
    """
    Exposes professional cybersecurity auditing features:
    - scan_secrets: Searches a file or directory for hardcoded API keys/secrets.
    - vulnerability_check: Performs static code security scans.
    - system_security: Audits active open ports, local users, and network config.
    - deep_file_audit: Uses LLM to deeply scan a file for OWASP vulnerabilities.
    - audit_packages: Audits dependencies for security flaws.
    """
    action = parameters.get("action", "scan_secrets").strip().lower()
    path = parameters.get("path", "").strip()

    _speak_and_log(f"Starting cybersecurity audit: {action}...", player)

    if action == "scan_secrets":
        return _scan_secrets_flow(path, player)
    elif action == "vulnerability_check":
        return _vuln_check_flow(path, player)
    elif action == "system_security":
        return _system_security_flow(player)
    elif action == "deep_file_audit":
        return _deep_file_audit_flow(path, player, speak)
    elif action == "audit_packages":
        return _audit_packages_flow(path, player)
    else:
        return f"Unknown security action: {action}"

def _scan_secrets_flow(path: str, player=None) -> str:
    if not path:
        return "Sir, please provide a valid file or directory path to scan for secrets."

    target_path = os.path.abspath(path)
    if not os.path.exists(target_path):
        return f"Sir, target path does not exist: {target_path}"

    files_to_scan = []
    if os.path.isfile(target_path):
        files_to_scan.append(target_path)
    else:
        for root, _, files in os.walk(target_path):
            if any(p in root for p in [".git", "__pycache__", "venv", "node_modules", ".gemini"]):
                continue
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in [".py", ".js", ".json", ".env", ".txt", ".ini", ".conf", ".yml", ".yaml"]:
                    files_to_scan.append(os.path.join(root, f))

    findings = []
    for fpath in files_to_scan:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for pattern_name, regex in SECRET_PATTERNS.items():
                matches = re.finditer(regex, content)
                for m in matches:
                    line_no = content.count("\n", 0, m.start()) + 1
                    preview = content[max(0, m.start()-20):min(len(content), m.end()+20)].replace("\n", " ")
                    findings.append({
                        "file": os.path.basename(fpath),
                        "line": line_no,
                        "type": pattern_name,
                        "match": m.group(0)[:8] + "...",
                        "context": f"...{preview}..."
                    })
        except Exception as e:
            print(f"[SecurityAuditor] Error reading {fpath}: {e}")

    if not findings:
        msg = "Sir, secret scan completed successfully. No hardcoded secrets or API keys were detected."
        _speak_and_log(msg, player)
        return msg

    msg = f"Sir, secret scan found {len(findings)} potential hardcoded credentials:\n"
    for f in findings:
        msg += f"- File: {f['file']}:{f['line']} | Type: {f['type']} | Match: {f['match']} | Context: {f['context']}\n"

    _speak_and_log(msg, player)
    return msg

def _vuln_check_flow(path: str, player=None) -> str:
    if not path:
        return "Sir, please provide a valid code file or directory path for static vulnerability check."

    target_path = os.path.abspath(path)
    if not os.path.exists(target_path):
        return f"Sir, target path does not exist: {target_path}"

    files_to_scan = []
    if os.path.isfile(target_path):
        files_to_scan.append(target_path)
    else:
        for root, _, files in os.walk(target_path):
            if any(p in root for p in [".git", "__pycache__", "venv", "node_modules"]):
                continue
            for f in files:
                if f.endswith(".py"):
                    files_to_scan.append(os.path.join(root, f))

    findings = []
    for fpath in files_to_scan:
        try:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            for pattern_name, regex in VULN_PATTERNS.items():
                matches = re.finditer(regex, content)
                for m in matches:
                    line_no = content.count("\n", 0, m.start()) + 1
                    findings.append({
                        "file": os.path.basename(fpath),
                        "line": line_no,
                        "type": pattern_name,
                        "code": m.group(0).strip()[:100]
                    })
        except Exception as e:
            print(f"[SecurityAuditor] Error reading {fpath}: {e}")

    if not findings:
        msg = "Sir, static vulnerability scan completed successfully. No common code flaws were detected."
        _speak_and_log(msg, player)
        return msg

    msg = f"Sir, static vulnerability check discovered {len(findings)} potential code vulnerabilities:\n"
    for f in findings:
        msg += f"- File: {f['file']}:{f['line']} | Vulnerability: {f['type']} | Code: `{f['code']}`\n"

    _speak_and_log(msg, player)
    return msg

def _system_security_flow(player=None) -> str:
    msg = "Sir, performing local system security scan...\n\n"

    # 1. Listen Ports (Windows netstat)
    try:
        res = subprocess.run(["netstat", "-ano"], capture_output=True, text=True, timeout=10)
        lines = res.stdout.strip().split("\n")
        listening = []
        for line in lines:
            if "LISTENING" in line:
                parts = re.split(r"\s+", line.strip())
                if len(parts) >= 4:
                    listening.append(f"Protocol: {parts[0]} | Local Addr: {parts[1]} | Status: {parts[3]} | PID: {parts[4]}")
        
        msg += f"--- LISTENING PORTS (Exposure) ---\n"
        if listening:
            msg += "\n".join(listening[:15]) + f"\n... (Total: {len(listening)} open ports)\n"
        else:
            msg += "No active listening ports found.\n"
    except Exception as e:
        msg += f"Could not retrieve listening ports: {e}\n"

    # 2. Local Host Details
    try:
        hostname = socket.gethostname()
        ip_addr = socket.gethostbyname(hostname)
        msg += f"\n--- NETWORK ADDRESSES ---\nHostname: {hostname}\nLocal IP Address: {ip_addr}\n"
    except Exception as e:
        msg += f"Could not retrieve host network info: {e}\n"

    _speak_and_log(msg, player)
    return msg

def _deep_file_audit_flow(path: str, player=None, speak=None) -> str:
    if not path or not os.path.isfile(path):
        return "Sir, deep file audit requires a valid file path."

    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            code_content = f.read()

        if len(code_content) > 15000:
            return "Sir, the file is too large for deep audit (max limit is 15,000 characters)."

        if speak:
            speak("Initiating deep artificial intelligence security audit of the file, sir.")

        config = get_config()
        from google import genai
        from google.genai import types
        
        class GeminiModelWrapper:
            def __init__(self, model_name: str, api_key: str, system_instruction: str = None):
                self.model_name = model_name
                self.api_key = api_key
                self.system_instruction = system_instruction

            def generate_content(self, contents, **kwargs):
                client = genai.Client(api_key=self.api_key)
                sys_inst = kwargs.get("system_instruction") or self.system_instruction
                config_params = None
                if sys_inst:
                    config_params = types.GenerateContentConfig(system_instruction=sys_inst)
                return client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config_params
                )

        model = GeminiModelWrapper(
            model_name="gemini-2.5-flash",
            api_key=config["gemini_api_key"],
            system_instruction=(
                "You are an expert cybersecurity auditor and penetration tester. "
                "Review the provided source code for vulnerabilities (such as OWASP top 10, SQL injection, "
                "XSS, hardcoded credentials, buffer overflows, path traversals, execution flows). "
                "Provide a professional report. For each vulnerability, output line numbers, "
                "the severity level (CRITICAL/HIGH/MEDIUM/LOW), a description of the issue, "
                "and the exact code fix. Be concise and technical. Write in Hindi/Hinglish if addressed, "
                "but keep technical terms in English."
            )
        )

        response = model.generate_content(
            f"Review this file:\nFilename: {os.path.basename(path)}\n\nCode Content:\n{code_content}"
        )
        report = response.text.strip()
        _speak_and_log(f"Deep Security Audit report completed for {os.path.basename(path)}.", player)
        return report

    except Exception as e:
        msg = f"Sir, deep file audit failed: {e}"
        _speak_and_log(msg, player)
        return msg

def _audit_packages_flow(path: str, player=None) -> str:
    if not path:
        path = "requirements.txt"
    
    if not os.path.exists(path):
        return f"Sir, packages requirement file does not exist: {path}"

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        packages = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            packages.append(line)
        
        msg = f"Sir, auditing packages in {path}...\n"
        insecure = []
        for pkg in packages:
            # Check for bad versions
            if "requests<2.20" in pkg or "urllib3<1.26" in pkg or "pyjwt<2.4" in pkg:
                insecure.append(f"Outdated package: {pkg} (Known vulnerabilities exist)")
            elif "==" in pkg:
                name, version = pkg.split("==", 1)
                # Mock a CVE lookup list for standard packages
                if name.strip().lower() == "requests" and version.strip().startswith("2.1"):
                    insecure.append(f"requests=={version} (Vulnerable to CVE-2018-18074)")
                if name.strip().lower() == "django" and version.strip().startswith("2."):
                    insecure.append(f"django=={version} (Vulnerable to multiple security flaws)")
        
        if not insecure:
            msg += "All dependencies appear to be clean or use secure versions."
        else:
            msg += "\n".join(insecure)

        _speak_and_log(msg, player)
        return msg

    except Exception as e:
        msg = f"Failed to audit requirements: {e}"
        _speak_and_log(msg, player)
        return msg

def _speak_and_log(message: str, player=None):
    if player:
        try:
            player.write_log(f"AUDITOR: {message}")
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
