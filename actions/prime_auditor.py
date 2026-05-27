# actions/prime_auditor.py
"""
IP Prime — Security & Quality Auditor
Runs a deep static analysis pass on any file or project directory.
Returns a severity-tagged report: CRITICAL / HIGH / MEDIUM / LOW
"""

import json
import subprocess
import sys
from pathlib import Path

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR        = _get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
        return config.get("coding_api_key") or config["gemini_api_key"]


def _read_source(target: str) -> tuple[str, str]:
    """Read a file or all Python/JS files in a directory. Returns (combined_source, display_label)."""
    p = Path(target)
    if not p.exists():
        return "", f"Path not found: {target}"

    if p.is_file():
        try:
            return p.read_text(encoding="utf-8", errors="replace"), p.name
        except Exception as e:
            return "", f"Could not read file: {e}"

    # Directory mode — collect up to 30 source files
    extensions = {".py", ".js", ".ts", ".java", ".cpp", ".c", ".cs", ".go", ".rb", ".php", ".rs"}
    files = sorted(
        f for f in p.rglob("*")
        if f.is_file() and f.suffix in extensions
        and not any(part.startswith(".") or part in ("__pycache__", "node_modules", "venv", ".venv")
                    for part in f.parts)
    )[:30]

    if not files:
        return "", f"No supported source files found in: {target}"

    combined = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            combined.append(f"# === {f.relative_to(p)} ===\n{content[:3000]}")
        except Exception:
            pass

    return "\n\n".join(combined), f"{p.name}/ ({len(files)} files)"


def _check_pip_vulnerabilities(target: str) -> str:
    """Run pip-audit or safety to check for known CVEs in requirements."""
    p = Path(target)
    req_file = p if p.is_file() and "requirement" in p.name.lower() else None
    if not req_file:
        req_file = next(
            (p / f for f in ("requirements.txt", "requirements-dev.txt", "Pipfile")
             if (p / f if p.is_dir() else p.parent / f).exists()),
            None
        )
    if not req_file or not req_file.exists():
        return ""

    # Try pip-audit (preferred)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip_audit", "-r", str(req_file), "--format", "json"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        if result.returncode == 0 or result.stdout.strip():
            data = json.loads(result.stdout)
            vulns = [v for item in data.get("dependencies", []) for v in item.get("vulns", [])]
            if not vulns:
                return "✅ No known CVEs found in dependencies."
            lines = [f"⚠️ {v['id']} ({v.get('fix_versions', ['?'])[0] if v.get('fix_versions') else 'no fix'}): {v['description'][:120]}" for v in vulns[:10]]
            return "DEPENDENCY CVEs:\n" + "\n".join(lines)
    except Exception:
        pass

    return ""


def _run_audit(target: str, player=None) -> str:
    """Main audit function. Returns a formatted severity report."""
    def log(msg: str):
        print(f"[PrimeAudit] {msg}")
        if player:
            player.write_log(f"[PrimeAudit] {msg}")

    log(f"Starting security & quality audit on: {target}")

    source, label = _read_source(target)
    if not source:
        return label  # error message

    # Truncate to avoid token overflow
    source_truncated = source[:18000]
    truncated = len(source) > 18000

    log("Sending to Gemini for deep analysis...")

    try:
        from google import genai
        client = genai.Client(api_key=_get_api_key())

        prompt = f"""You are an expert security engineer and code quality analyst. Perform a comprehensive audit on the following source code.

File/Project: {label}
{f"(Note: Large project — showing first 18000 chars, {len(source) - 18000} chars truncated)" if truncated else ""}

Analyze for:
1. SECURITY: hardcoded secrets/API keys/passwords, SQL injection, command injection, path traversal, eval() misuse, insecure deserialization, missing input validation, SSRF, XSS, CSRF, unencrypted sensitive data
2. PERFORMANCE: blocking I/O in async context, N+1 query patterns, unnecessary global state, memory leaks, inefficient loops, redundant file reads in hot paths
3. CODE QUALITY: dead/unreachable code, magic numbers without constants, missing error handling, functions >50 lines, God objects/classes, missing type hints, duplicate logic
4. DEPENDENCY RISKS: outdated imports, deprecated APIs, insecure library usage

Return your findings as a structured JSON object with this exact schema:
{{
  "summary": "2-3 sentence executive summary",
  "score": 0-100,
  "findings": [
    {{
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "category": "SECURITY|PERFORMANCE|QUALITY|DEPENDENCY",
      "title": "Short title",
      "description": "What the issue is",
      "location": "filename:linerange or function name if detectable",
      "fix": "Concrete fix recommendation"
    }}
  ],
  "quick_wins": ["list of 3-5 easy fixes that can be done immediately"]
}}

Return ONLY valid JSON. No markdown, no explanation.

Source Code:
```
{source_truncated}
```"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        raw = response.text.strip()
        # Strip markdown fences if present
        import re
        raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        raw = raw.strip()

        data = json.loads(raw)

    except json.JSONDecodeError as e:
        log(f"JSON parse error: {e}. Returning raw response.")
        return f"Audit completed but response was not clean JSON:\n\n{raw[:2000]}"
    except Exception as e:
        return f"Audit failed: {e}"

    # Format the output
    score = data.get("score", "N/A")
    summary = data.get("summary", "")
    findings = data.get("findings", [])
    quick_wins = data.get("quick_wins", [])

    # Severity order for sorting
    sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda f: sev_order.get(f.get("severity", "LOW"), 4))

    severity_icons = {
        "CRITICAL": "🔴 CRITICAL",
        "HIGH":     "🟠 HIGH",
        "MEDIUM":   "🟡 MEDIUM",
        "LOW":      "🟢 LOW",
    }

    lines = [
        "╔══════════════════════════════════════════════════════════╗",
        "║  IP PRIME SECURITY & QUALITY AUDIT REPORT               ║",
        "╚══════════════════════════════════════════════════════════╝",
        "",
        f"📁 Target  : {label}",
        f"🏆 Score   : {score}/100",
        f"📋 Summary : {summary}",
        "",
        f"──── FINDINGS ({len(findings)}) ────",
    ]

    for i, f in enumerate(findings, 1):
        sev = f.get("severity", "LOW")
        cat = f.get("category", "")
        title = f.get("title", "")
        desc = f.get("description", "")
        loc = f.get("location", "")
        fix = f.get("fix", "")
        lines.append(f"\n[{i}] {severity_icons.get(sev, sev)} | {cat}")
        lines.append(f"    Title    : {title}")
        if loc:
            lines.append(f"    Location : {loc}")
        lines.append(f"    Issue    : {desc}")
        lines.append(f"    Fix      : {fix}")

    if quick_wins:
        lines.append("\n──── QUICK WINS ────")
        for qw in quick_wins:
            lines.append(f"  ✅ {qw}")

    # CVE check
    cve_result = _check_pip_vulnerabilities(target)
    if cve_result:
        lines.append("\n──── CVE SCAN ────")
        lines.append(cve_result)

    log(f"Audit complete. Score: {score}/100. Findings: {len(findings)}")

    # Also push critical findings to the HUD
    try:
        from actions.web_hud import log_event
        critical_count = sum(1 for f in findings if f.get("severity") == "CRITICAL")
        high_count = sum(1 for f in findings if f.get("severity") == "HIGH")
        log_event(f"[Audit] {label}: Score {score}/100 | 🔴 {critical_count} Critical | 🟠 {high_count} High")
    except Exception:
        pass

    return "\n".join(lines)


def prime_audit(parameters: dict, player=None) -> str:
    """Main tool entry point called from main.py dispatcher."""
    p = parameters or {}
    target = p.get("target", "").strip()
    if not target:
        return "Please provide a file path or project directory to audit, sir."
    return _run_audit(target, player=player)
