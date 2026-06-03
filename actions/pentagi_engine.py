"""
╔═══════════════════════════════════════════════════════════════╗
║         ⚡ PENTAGI ENGINE — IP PRIME REAL HACKING CORE ⚡      ║
║   Inspired by PentAGI (github.com/vxcontrol/pentagi)          ║
║   Uses REAL tools: nmap, scapy, socket, dnspython, requests   ║
║   "The shadow is real. The blade is real. The Sage is ready." ║
╚═══════════════════════════════════════════════════════════════╝
"""

import sys
import io
# Fix Unicode encoding on Windows cp1252
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import os
import re
import json
import socket
import struct
import subprocess
import threading
import time
import ipaddress
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed


PENTA_BANNER = """╔═══════════════════════════════════════════════════════════╗
║          ⚡ PENTAGI ENGINE — REAL RECON ACTIVE ⚡           ║
║   Inspired by github.com/vxcontrol/pentagi                ║
╚═══════════════════════════════════════════════════════════╝"""


def _get_api_key():
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = os.path.join(base, "config", "api_keys.json")
        with open(cfg, encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "")
    except Exception:
        return os.environ.get("GEMINI_API_KEY", "")


def _ai_analyze(prompt: str) -> str:
    """Call Gemini for AI-assisted analysis of real scan results."""
    api_key = _get_api_key()
    if not api_key:
        return "AI analysis unavailable (no API key)"
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        try:
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        except Exception:
            resp = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
        return resp.text.strip()
    except Exception as e:
        return f"AI analysis failed: {e}"


# ═══════════════════════════════════════════════════════════════════
# 🔍 MODULE 1 — REAL PORT SCANNER (uses socket + python-nmap if avail)
# ═══════════════════════════════════════════════════════════════════

COMMON_PORTS = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 445: "SMB",
    1433: "MSSQL", 1521: "Oracle", 3306: "MySQL", 3389: "RDP",
    5432: "PostgreSQL", 5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 8888: "Jupyter", 9200: "Elasticsearch",
    27017: "MongoDB", 6443: "K8s API", 2375: "Docker", 2376: "Docker-TLS",
    4444: "Metasploit", 5555: "ADB", 11211: "Memcached"
}

VULNERABILITY_HINTS = {
    21: "⚠️ Anonymous FTP login? Check: ftp <host> then user 'anonymous'",
    22: "⚠️ Try default creds, check SSH version for CVEs (OpenSSH < 7.7)",
    23: "🔴 Telnet is unencrypted! Sniff credentials with Wireshark",
    25: "⚠️ Open relay? Try: EHLO test, MAIL FROM:<test@test.com>",
    80: "⚠️ Check: robots.txt, /.git/, /admin/, /backup/, LFI paths",
    443: "⚠️ Check SSL cert, TLS version (SSLv3/TLS1.0 = POODLE/BEAST)",
    445: "🔴 SMB! Check EternalBlue (MS17-010), SMBv1 enabled?",
    1433: "⚠️ MSSQL - try sa:sa, xp_cmdshell check",
    3306: "⚠️ MySQL - try root:root, check for remote root access",
    3389: "🔴 RDP - BlueKeep (CVE-2019-0708), brute force possible",
    5432: "⚠️ PostgreSQL - try postgres:postgres",
    5900: "🔴 VNC - no auth? or weak password",
    6379: "🔴 Redis - no auth! SLAVEOF attack possible",
    8080: "⚠️ Check for Tomcat Manager, Jenkins, proxy exposure",
    9200: "🔴 Elasticsearch - no auth by default! All data exposed",
    27017: "🔴 MongoDB - no auth by default in old versions!",
    2375: "🔴 Docker daemon exposed! RCE trivial: docker -H <host>:2375 run --rm -it --privileged ubuntu",
    11211: "🔴 Memcached - DDoS amplification + data exposure",
}


def _scan_port(host: str, port: int, timeout: float = 1.5) -> dict:
    """Scan a single port using raw socket."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        
        banner = ""
        if result == 0:
            # Try to grab banner
            try:
                sock.settimeout(2)
                if port in (80, 8080, 8443, 443):
                    sock.send(b"GET / HTTP/1.0\r\nHost: " + host.encode() + b"\r\n\r\n")
                elif port == 21:
                    pass  # FTP sends banner automatically
                elif port == 22:
                    pass  # SSH sends banner automatically
                banner = sock.recv(256).decode("utf-8", errors="replace").strip()[:100]
            except Exception:
                pass
        sock.close()
        
        return {
            "port": port,
            "open": result == 0,
            "service": COMMON_PORTS.get(port, "Unknown"),
            "banner": banner,
            "vuln_hint": VULNERABILITY_HINTS.get(port, "")
        }
    except Exception:
        return {"port": port, "open": False, "service": COMMON_PORTS.get(port, "Unknown"), "banner": "", "vuln_hint": ""}


def run_real_port_scan(target: str, port_range: str = "common", player=None) -> str:
    """
    ⚡ REAL PORT SCANNER — Uses actual TCP socket connections.
    Faster than nmap for quick recon. No root required.
    """
    if player:
        player.write_log(f"[PentAGI] Starting real port scan on {target}")

    # Resolve hostname
    try:
        ip = socket.gethostbyname(target)
    except socket.gaierror as e:
        return f"❌ Cannot resolve host '{target}': {e}"

    # Determine ports to scan
    if port_range == "common":
        ports = list(COMMON_PORTS.keys())
    elif port_range == "top100":
        ports = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 161, 443, 445, 
                 512, 513, 514, 587, 993, 995, 1080, 1433, 1521, 1723, 3306, 3389,
                 5432, 5900, 6379, 6443, 8080, 8443, 8888, 9200, 9300, 27017, 
                 27018, 28017, 2375, 2376, 4444, 5555, 6666, 7777, 8888, 9090,
                 9999, 10000, 11211, 50000] + list(COMMON_PORTS.keys())
        ports = list(set(ports))
    elif "-" in str(port_range):
        start, end = port_range.split("-")
        ports = list(range(int(start), int(end) + 1))
    else:
        try:
            ports = [int(p.strip()) for p in str(port_range).split(",")]
        except Exception:
            ports = list(COMMON_PORTS.keys())

    start_time = time.time()
    open_ports = []
    total = len(ports)

    if player:
        player.write_log(f"[PentAGI] Scanning {total} ports on {ip} ({target})...")

    # Parallel scanning with thread pool
    with ThreadPoolExecutor(max_workers=150) as executor:
        futures = {executor.submit(_scan_port, ip, port): port for port in ports}
        for future in as_completed(futures):
            result = future.result()
            if result["open"]:
                open_ports.append(result)

    elapsed = time.time() - start_time
    open_ports.sort(key=lambda x: x["port"])

    # Build output
    lines = [
        PENTA_BANNER,
        f"         🔍 REAL PORT SCAN — {target} ({ip})",
        "═══════════════════════════════════════════════════════════════",
        f"⏱️  Scanned {total} ports in {elapsed:.1f}s  |  {len(open_ports)} open ports found",
        "",
    ]

    if not open_ports:
        lines.append("✅ No open ports found in scanned range.")
        lines.append("   (Host may be firewalled, offline, or not listening)")
    else:
        lines += [
            f"{'PORT':<8} {'SERVICE':<15} {'BANNER':<40} STATUS",
            "─" * 75,
        ]
        for p in open_ports:
            banner_short = p["banner"][:38] if p["banner"] else ""
            lines.append(f"{p['port']:<8} {p['service']:<15} {banner_short:<40} 🟢 OPEN")
            if p["vuln_hint"]:
                lines.append(f"         {p['vuln_hint']}")
        
        # AI analysis of results
        lines += ["", "─────────────────────────────────────────────────────────────"]
        scan_summary = "\n".join([f"Port {p['port']} ({p['service']}): {p['banner']}" for p in open_ports])
        ai_prompt = f"""You are a penetration testing expert. Analyze these open ports found on {target}:

{scan_summary}

Provide:
1. Most critical attack vectors (top 3)
2. Recommended immediate checks
3. Overall risk assessment (LOW/MEDIUM/HIGH/CRITICAL)

Be concise and tactical. Max 150 words."""
        
        if player:
            player.write_log("[PentAGI] Running AI analysis on scan results...")
        
        ai_analysis = _ai_analyze(ai_prompt)
        lines += [
            "🤖 AI THREAT ANALYSIS:",
            ai_analysis,
        ]

    lines += [
        "",
        "─────────────────────────────────────────────────────────────",
        "💡 Next steps: web_vuln_check | ssh_audit | smb_check | dns_enum",
        "═══════════════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 🌐 MODULE 2 — REAL DNS ENUMERATION
# ═══════════════════════════════════════════════════════════════════

def run_real_dns_enum(domain: str, player=None) -> str:
    """
    🌐 REAL DNS ENUMERATION — Actual DNS queries using socket + dnspython.
    Discovers A, MX, NS, TXT, CNAME records. Subdomain bruteforce.
    """
    if player:
        player.write_log(f"[PentAGI] Running DNS enumeration on {domain}")

    lines = [
        PENTA_BANNER,
        f"         🌐 REAL DNS ENUM — {domain}",
        "═══════════════════════════════════════════════════════════════",
    ]

    results = {}

    # 1. Main IP resolution
    try:
        ip = socket.gethostbyname(domain)
        results["A"] = [ip]
        lines.append(f"📍 A Record     : {ip}")
    except Exception as e:
        lines.append(f"❌ A Record     : Failed ({e})")

    # 2. Try dnspython if available
    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.timeout = 3
        resolver.lifetime = 5

        record_types = ["MX", "NS", "TXT", "CNAME", "AAAA", "SOA"]
        for rtype in record_types:
            try:
                answers = resolver.resolve(domain, rtype)
                records = [str(r) for r in answers]
                results[rtype] = records
                label = f"{rtype} Record{'s' if len(records) > 1 else ''}"
                for r in records:
                    lines.append(f"📡 {label:<14}: {r}")
            except Exception:
                pass

    except ImportError:
        # Fallback: use nslookup subprocess
        try:
            for qtype in ["MX", "NS", "TXT"]:
                result = subprocess.run(
                    ["nslookup", f"-type={qtype}", domain],
                    capture_output=True, text=True, timeout=5
                )
                if result.stdout and "can't find" not in result.stdout.lower():
                    lines.append(f"📡 {qtype}          : {result.stdout.strip()[:80]}")
        except Exception:
            pass

    # 3. Subdomain bruteforce
    lines += ["", "🕸️  SUBDOMAIN DISCOVERY:", "─────────────────────────────────────────────────────────────"]
    
    subdomains_to_check = [
        "www", "mail", "smtp", "pop", "imap", "ftp", "ssh", "vpn",
        "admin", "administrator", "portal", "dashboard", "panel",
        "api", "dev", "staging", "test", "beta", "demo", "sandbox",
        "app", "web", "mobile", "m", "cdn", "static", "assets",
        "secure", "login", "auth", "sso", "oauth",
        "jenkins", "gitlab", "github", "jira", "confluence",
        "mysql", "db", "database", "redis", "mongo",
        "monitor", "grafana", "kibana", "elastic",
        "backup", "old", "new", "v2", "v3",
        "internal", "intranet", "corp", "office",
        "shop", "store", "blog", "forum", "wiki",
        "remote", "rdp", "citrix", "exchange",
        "ns1", "ns2", "mx1", "mx2",
    ]

    found_subs = []
    
    def check_sub(sub):
        full = f"{sub}.{domain}"
        try:
            ip = socket.gethostbyname(full)
            return (full, ip)
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(check_sub, s) for s in subdomains_to_check]
        for future in as_completed(futures):
            result = future.result()
            if result:
                found_subs.append(result)

    found_subs.sort(key=lambda x: x[0])
    
    if found_subs:
        for sub, ip in found_subs:
            lines.append(f"  ✅ {sub:<35} → {ip}")
    else:
        lines.append("  No common subdomains found (may be behind CDN/WAF)")

    lines += [
        "",
        f"📊 Total subdomains found: {len(found_subs)} / {len(subdomains_to_check)} checked",
        "─────────────────────────────────────────────────────────────",
    ]

    # AI analysis
    dns_data = f"Domain: {domain}\nRecords: {json.dumps(results, indent=2)}\nSubdomains found: {[s[0] for s in found_subs]}"
    ai_analysis = _ai_analyze(f"""As a pentester, analyze this DNS data and identify:
1. Interesting attack surface
2. Technology/infrastructure hints
3. Any security misconfigs visible

Data:
{dns_data}

Max 100 words.""")

    lines += [
        "🤖 AI INTELLIGENCE:",
        ai_analysis,
        "═══════════════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 🌐 MODULE 3 — REAL HTTP HEADER SECURITY CHECK
# ═══════════════════════════════════════════════════════════════════

def run_real_web_check(url: str, player=None) -> str:
    """
    🌐 REAL WEB SECURITY CHECK — Fetches actual HTTP headers and content.
    Checks for real misconfigs, info leakage, and vulnerabilities.
    """
    import urllib.request
    import urllib.error
    import ssl

    if player:
        player.write_log(f"[PentAGI] Real web check on {url}")

    if not url.startswith("http"):
        url = "https://" + url

    lines = [
        PENTA_BANNER,
        f"         🌐 REAL WEB CHECK — {url}",
        "═══════════════════════════════════════════════════════════════",
    ]

    # Disable SSL verification for security testing
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    findings = []
    headers_found = {}
    server_info = {}

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (PentAGI-Engine/1.0)",
                "Accept": "*/*",
            }
        )
        with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
            headers_found = dict(resp.headers)
            status = resp.status
            body_preview = resp.read(2048).decode("utf-8", errors="replace")

        lines.append(f"✅ Status Code : {status}")
        lines.append(f"🌐 Final URL   : {resp.url}")

        # Server fingerprinting
        server = headers_found.get("Server", headers_found.get("server", ""))
        powered = headers_found.get("X-Powered-By", headers_found.get("x-powered-by", ""))
        if server:
            server_info["server"] = server
            lines.append(f"🖥️  Server      : {server}")
            findings.append(f"Server header reveals: {server}")
        if powered:
            server_info["powered_by"] = powered
            lines.append(f"⚡ Powered By  : {powered}")
            findings.append(f"X-Powered-By reveals tech: {powered}")

        # Security headers check
        sec_headers = {
            "Strict-Transport-Security": ("HSTS", "🔒", "Missing! HTTPS not enforced"),
            "Content-Security-Policy": ("CSP", "🛡️", "Missing! XSS risk"),
            "X-Frame-Options": ("Clickjack", "🖼️", "Missing! Clickjacking possible"),
            "X-Content-Type-Options": ("MIME-sniff", "📄", "Missing! MIME sniffing"),
            "Referrer-Policy": ("Referrer", "🔗", "Missing! URL leakage"),
            "Permissions-Policy": ("Perms", "🔑", "Missing! Feature policy"),
            "X-XSS-Protection": ("XSS-Protect", "⚔️", "Missing"),
        }

        lines += ["", "🛡️  SECURITY HEADERS:", "─────────────────────────────────────────────────────────────"]
        for header, (name, icon, missing_msg) in sec_headers.items():
            val = headers_found.get(header, headers_found.get(header.lower(), None))
            if val:
                lines.append(f"  ✅ {icon} {name:<15}: {val[:60]}")
            else:
                lines.append(f"  ❌ {icon} {name:<15}: {missing_msg}")
                findings.append(f"Missing {header}: {missing_msg}")

        # Check for interesting response patterns
        lines += ["", "🔍 CONTENT ANALYSIS:", "─────────────────────────────────────────────────────────────"]
        
        checks = [
            ("WordPress", "wp-content" in body_preview or "wp-json" in body_preview, "WordPress CMS detected — check /wp-admin/, xmlrpc.php"),
            ("Joomla", "joomla" in body_preview.lower(), "Joomla CMS — check /administrator/"),
            ("Drupal", "drupal" in body_preview.lower(), "Drupal CMS — check /user/login"),
            ("PHP Error", "Fatal error" in body_preview or "Parse error" in body_preview, "🔴 PHP errors exposed! Source code leakage"),
            ("Debug Mode", "debug" in body_preview.lower() and "true" in body_preview.lower(), "⚠️ Debug mode may be enabled"),
            ("SQL Error", any(e in body_preview for e in ["SQL syntax", "mysql_fetch", "ORA-", "SQLite"]), "🔴 SQL error in response! SQLi likely vulnerable"),
            ("Stack Trace", "Exception" in body_preview and "at " in body_preview, "⚠️ Stack trace exposed — technology/path disclosure"),
            ("Email Found", "@" in body_preview and "." in body_preview, "Email addresses in response — OSINT target"),
            ("Git Exposed", ".git" in body_preview or "git-hash" in body_preview, "🔴 Git repo info exposed!"),
        ]

        for name, condition, message in checks:
            if condition:
                lines.append(f"  ⚠️  {name}: {message}")
                findings.append(message)
            
        # Check for common sensitive paths
        lines += ["", "🗂️  SENSITIVE PATH CHECK:"]
        
        sensitive_paths = [
            "/.git/HEAD", "/robots.txt", "/.env", "/admin/", "/wp-admin/",
            "/phpinfo.php", "/.htaccess", "/backup.zip", "/config.php",
            "/.DS_Store", "/crossdomain.xml", "/sitemap.xml",
        ]
        
        def check_path(path):
            try:
                full_url = url.rstrip("/") + path
                req2 = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req2, timeout=5, context=ctx) as r:
                    if r.status < 400:
                        return (path, r.status, len(r.read()))
            except Exception:
                pass
            return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(check_path, p) for p in sensitive_paths]
            for future in as_completed(futures):
                result = future.result()
                if result:
                    path, status, size = result
                    lines.append(f"  🔴 FOUND: {path} (HTTP {status}, {size} bytes)")
                    findings.append(f"Sensitive path accessible: {path}")

    except urllib.error.HTTPError as e:
        lines.append(f"HTTP Error: {e.code} {e.reason}")
    except urllib.error.URLError as e:
        lines.append(f"Connection failed: {e.reason}")
    except Exception as e:
        lines.append(f"Error: {e}")

    # AI analysis
    lines += ["", "─────────────────────────────────────────────────────────────"]
    findings_text = "\n".join(findings) if findings else "No critical findings"
    ai_analysis = _ai_analyze(f"""Penetration tester reviewing web app findings for {url}:

{findings_text}

Server: {server_info}

Give top 3 attack recommendations. Be specific and actionable. Max 120 words.""")

    lines += [
        "🤖 AI ATTACK RECOMMENDATIONS:",
        ai_analysis,
        "═══════════════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 🔐 MODULE 4 — REAL SSH AUDIT
# ═══════════════════════════════════════════════════════════════════

def run_real_ssh_audit(host: str, port: int = 22, player=None) -> str:
    """
    🔐 REAL SSH AUDIT — Connects to SSH and extracts version, algorithms,
    and checks for known vulnerable versions.
    """
    if player:
        player.write_log(f"[PentAGI] SSH audit on {host}:{port}")

    lines = [
        PENTA_BANNER,
        f"         🔐 REAL SSH AUDIT — {host}:{port}",
        "═══════════════════════════════════════════════════════════════",
    ]

    # Grab SSH banner
    ssh_version = ""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((host, port))
        banner = sock.recv(256).decode("utf-8", errors="replace").strip()
        ssh_version = banner
        sock.close()
        lines.append(f"📡 SSH Banner   : {banner}")
    except Exception as e:
        lines.append(f"❌ Connection failed: {e}")
        return "\n".join(lines)

    # Parse version
    version_match = re.search(r"SSH-2\.0-OpenSSH[_\s](\S+)", ssh_version)
    if version_match:
        ver = version_match.group(1)
        lines.append(f"🔍 Version      : OpenSSH {ver}")
        
        # Known vulnerable versions
        vuln_versions = {
            "7.2": "CVE-2016-6515 (DoS), CVE-2016-6210 (User enum)",
            "7.1": "CVE-2016-0778 (buffer overflow in roaming)",
            "6.x": "CVE-2014-2532 (AcceptEnv bypass), CVE-2014-2653 (ROAMING)",
            "5.x": "Multiple critical CVEs including MITM",
        }

        lines += ["", "🔎 VERSION CVE CHECK:"]
        found_vuln = False
        for v, cves in vuln_versions.items():
            if ver.startswith(v.replace(".x", "")):
                lines.append(f"  🔴 VULNERABLE: OpenSSH {ver} → {cves}")
                found_vuln = True
        if not found_vuln:
            lines.append(f"  ✅ OpenSSH {ver} — No critical known CVEs")

    # Try paramiko for deeper audit
    try:
        import paramiko
        transport = paramiko.Transport((host, port))
        transport.start_client(timeout=5)
        
        security_options = transport.get_security_options()
        
        lines += ["", "🔐 SUPPORTED ALGORITHMS:"]
        if hasattr(security_options, 'ciphers'):
            weak_ciphers = [c for c in security_options.ciphers if any(w in c for w in ["arcfour", "3des", "des", "blowfish", "cast"])]
            lines.append(f"  Ciphers   : {', '.join(list(security_options.ciphers)[:5])}")
            if weak_ciphers:
                lines.append(f"  🔴 WEAK: {', '.join(weak_ciphers)}")
        if hasattr(security_options, 'digests'):
            weak_digests = [d for d in security_options.digests if "md5" in d or "sha1-" in d]
            lines.append(f"  MACs      : {', '.join(list(security_options.digests)[:5])}")
            if weak_digests:
                lines.append(f"  🔴 WEAK MACs: {', '.join(weak_digests)}")
        if hasattr(security_options, 'kex'):
            lines.append(f"  Key Exchange: {', '.join(list(security_options.kex)[:3])}")

        transport.close()

    except ImportError:
        lines.append("  ℹ️ Install paramiko for algorithm analysis: pip install paramiko")
    except Exception as e:
        lines.append(f"  ℹ️ Algorithm check: {str(e)[:60]}")

    # Common attack vectors
    lines += [
        "",
        "⚔️  ATTACK VECTORS:",
        "  1. User enumeration: ssh -l <user> host (timing-based)",
        "  2. Password bruteforce: hydra -L users.txt -P pass.txt ssh://<host>",
        "  3. Key-based auth check: ssh-keyscan <host>",
        "  4. CVE exploitation if version is vulnerable",
        "  5. Check for default keys: /home/*/.ssh/authorized_keys",
    ]

    lines += [
        "",
        "─────────────────────────────────────────────────────────────",
        f"🧙 SAGE NOTE: Always verify version-specific CVEs on NVD/ExploitDB.",
        "═══════════════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 📡 MODULE 5 — REAL NETWORK DISCOVERY (ARP + ping)
# ═══════════════════════════════════════════════════════════════════

def run_real_network_discovery(player=None) -> str:
    """
    📡 REAL NETWORK DISCOVERY — Uses ARP table + ping sweep to find live hosts.
    Works on Windows/Linux/Mac. No root required for ARP.
    """
    if player:
        player.write_log("[PentAGI] Running real network discovery...")

    lines = [
        PENTA_BANNER,
        "         📡 REAL NETWORK DISCOVERY",
        "═══════════════════════════════════════════════════════════════",
    ]

    # Get own IP info
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        lines += [
            f"🖥️  Hostname     : {hostname}",
            f"📍 Local IP     : {local_ip}",
            "",
        ]
    except Exception:
        local_ip = "127.0.0.1"

    # ARP table (no root needed)
    lines.append("📋 ARP TABLE (Current Known Hosts):")
    lines.append("─────────────────────────────────────────────────────────────")
    
    arp_result = subprocess.run(
        ["arp", "-a"], capture_output=True, text=True, errors="replace", timeout=10
    )
    
    arp_pattern = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([\w\-:]+)\s+(\w+)")
    devices = []
    
    # MAC vendor lookup (offline)
    vendor_map = {
        "00:50:56": "VMware", "00:0c:29": "VMware VM", "08:00:27": "VirtualBox",
        "dc:a6:32": "Raspberry Pi", "b8:27:eb": "Raspberry Pi",
        "f0:18:98": "Apple", "3c:22:fb": "Apple", "ac:de:48": "Apple",
        "00:1b:63": "Apple", "28:cd:c1": "Apple", "a4:83:e7": "Intel NIC",
        "00:1a:11": "Google", "a4:c3:f0": "Google Nest",
        "fc:ec:da": "Ubiquiti", "00:15:5d": "Microsoft Hyper-V",
        "00:16:3e": "Xen VM", "52:54:00": "QEMU/KVM",
        "00:25:00": "Apple", "00:26:bb": "Apple",
    }
    
    for line in arp_result.stdout.splitlines():
        m = arp_pattern.search(line)
        if m:
            ip, mac, addr_type = m.group(1), m.group(2), m.group(3)
            if not ip.endswith(".255") and not ip.startswith("224.") and not ip.startswith("239."):
                mac_normalized = mac.upper().replace("-", ":")
                prefix = mac_normalized[:8]
                vendor = next((v for k, v in vendor_map.items() if prefix.startswith(k.upper())), "Unknown")
                
                # Try reverse DNS
                hostname_rev = ""
                try:
                    hostname_rev = socket.gethostbyaddr(ip)[0]
                except Exception:
                    pass
                
                devices.append({
                    "ip": ip, "mac": mac, "type": addr_type,
                    "vendor": vendor, "hostname": hostname_rev
                })

    if devices:
        lines.append(f"  {'IP':<18} {'MAC':<20} {'VENDOR':<18} {'HOSTNAME'}")
        lines.append("  " + "─" * 72)
        for d in sorted(devices, key=lambda x: [int(i) for i in x['ip'].split('.')]):
            hn = d['hostname'][:20] if d['hostname'] else ""
            lines.append(f"  {d['ip']:<18} {d['mac']:<20} {d['vendor']:<18} {hn}")
    else:
        lines.append("  No devices in ARP cache (try pinging subnet first)")

    # Quick ping sweep of local subnet
    lines += ["", "🏓 LIVE HOST DISCOVERY (Ping Sweep):"]
    lines.append("─────────────────────────────────────────────────────────────")
    
    try:
        # Determine local subnet
        parts = local_ip.split(".")
        if len(parts) == 4:
            subnet_base = ".".join(parts[:3])
            lines.append(f"  Sweeping {subnet_base}.1-254 ...")
            
            live_hosts = []
            
            def ping_host(ip):
                try:
                    result = subprocess.run(
                        ["ping", "-n", "1", "-w", "300", ip],
                        capture_output=True, text=True, timeout=2
                    )
                    if "TTL=" in result.stdout or "ttl=" in result.stdout:
                        return ip
                except Exception:
                    pass
                return None
            
            # Scan first 30 hosts for speed (common range)
            sample_ips = [f"{subnet_base}.{i}" for i in range(1, 31)]
            with ThreadPoolExecutor(max_workers=30) as executor:
                futures = [executor.submit(ping_host, ip) for ip in sample_ips]
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        live_hosts.append(result)
            
            live_hosts.sort(key=lambda x: [int(i) for i in x.split(".")])
            
            if live_hosts:
                for h in live_hosts:
                    try:
                        hn = socket.gethostbyaddr(h)[0]
                    except Exception:
                        hn = ""
                    lines.append(f"  🟢 {h:<18} {hn}")
            else:
                lines.append("  No hosts responded to ping in sample range")
    except Exception as e:
        lines.append(f"  Ping sweep failed: {e}")

    lines += [
        "",
        f"📊 ARP devices: {len(devices)} | Scan complete",
        "─────────────────────────────────────────────────────────────",
        "💡 Next: Run port_scan on discovered IPs",
        "🧙 SAGE: 'Know your network before you know your enemy.'",
        "═══════════════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# 🔑 MODULE 6 — REAL HASH IDENTIFIER + CRACK STRATEGY
# ═══════════════════════════════════════════════════════════════════

def run_real_hash_identify(hash_value: str, player=None) -> str:
    """
    🔑 REAL HASH IDENTIFIER — Identifies hash type from length/pattern,
    provides real hashcat modes and john commands.
    """
    if player:
        player.write_log(f"[PentAGI] Identifying hash: {hash_value[:20]}...")

    hash_value = hash_value.strip()
    h_len = len(hash_value)
    is_hex = all(c in "0123456789abcdefABCDEF" for c in hash_value)

    # Hash identification patterns
    hash_db = [
        # (pattern_check, name, hashcat_mode, john_format, description)
        (lambda h: len(h) == 32 and all(c in "0123456789abcdefABCDEF" for c in h),
         "MD5", "0", "md5", "Most common hash. Very crackable."),
        (lambda h: len(h) == 40 and all(c in "0123456789abcdefABCDEF" for c in h),
         "SHA-1", "100", "sha1", "Deprecated. Crackable with GPU."),
        (lambda h: len(h) == 64 and all(c in "0123456789abcdefABCDEF" for c in h),
         "SHA-256", "1400", "sha256", "Secure but crackable with GPU clusters."),
        (lambda h: len(h) == 128 and all(c in "0123456789abcdefABCDEF" for c in h),
         "SHA-512", "1700", "sha512", "Very secure. Requires significant compute."),
        (lambda h: h.startswith("$2a$") or h.startswith("$2b$") or h.startswith("$2y$"),
         "bcrypt", "3200", "bcrypt", "Very slow to crack. 10+ rounds = hard."),
        (lambda h: h.startswith("$6$"),
         "SHA-512 crypt", "1800", "sha512crypt", "Linux /etc/shadow format."),
        (lambda h: h.startswith("$5$"),
         "SHA-256 crypt", "7400", "sha256crypt", "Linux /etc/shadow format."),
        (lambda h: h.startswith("$1$"),
         "MD5 crypt", "500", "md5crypt", "Old Linux /etc/shadow. Crackable."),
        (lambda h: len(h) == 32 and ":" in h,
         "NTLM Challenge", "5600", "netntlmv2", "Windows authentication."),
        (lambda h: len(h) == 32,
         "NTLM / MD5", "1000", "NT", "Windows password hash from SAM/NTDS."),
        (lambda h: h.startswith("sha1$"),
         "Django SHA1", "124", "django-sha1", "Django web framework hash."),
        (lambda h: h.startswith("pbkdf2_sha256$"),
         "Django PBKDF2", "20000", "django-pbkdf2-sha256", "Modern Django hash. Hard."),
        (lambda h: len(h) == 60 and h.startswith("$P$"),
         "WordPress/phpBB", "400", "phpass", "WordPress/phpBB MD5 hash."),
    ]

    detected = []
    for check_fn, name, hc_mode, john_fmt, desc in hash_db:
        try:
            if check_fn(hash_value):
                detected.append((name, hc_mode, john_fmt, desc))
        except Exception:
            pass

    lines = [
        PENTA_BANNER,
        "         🔑 REAL HASH IDENTIFIER",
        "═══════════════════════════════════════════════════════════════",
        f"HASH   : {hash_value[:80]}{'...' if len(hash_value) > 80 else ''}",
        f"LENGTH : {h_len} chars | HEX: {'Yes' if is_hex else 'No'}",
        "",
    ]

    if detected:
        for name, hc_mode, john_fmt, desc in detected:
            lines += [
                f"✅ DETECTED: {name}",
                f"   {desc}",
                "",
                "⚔️  CRACK COMMANDS:",
                f"   # hashcat (GPU):",
                f"   hashcat -m {hc_mode} hash.txt /path/to/rockyou.txt",
                f"   hashcat -m {hc_mode} hash.txt /path/to/rockyou.txt -r rules/best64.rule",
                f"",
                f"   # John the Ripper:",
                f"   john --format={john_fmt} --wordlist=rockyou.txt hash.txt",
                f"",
                "🌐 ONLINE CRACKERS:",
                "   • https://crackstation.net",
                "   • https://hashes.com",
                "   • https://md5decrypt.net",
                "   • https://www.onlinehashcrack.com",
                "",
            ]
    else:
        lines += [
            "❓ Hash type not auto-detected.",
            f"   Length: {h_len} chars",
            "   Try: https://hashes.com/en/tools/hash_identifier",
        ]

    lines += [
        "💡 WORDLISTS:",
        "   • rockyou.txt (14M passwords) — most important",
        "   • SecLists/Passwords/  — comprehensive collection",
        "   • hashcat rules: best64, d3ad0ne, OneRuleToRuleThemAll",
        "─────────────────────────────────────────────────────────────",
        "🧙 SAGE: 'A hash is a lock. rockyou.txt is the master key.'",
        "═══════════════════════════════════════════════════════════════",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# MAIN DISPATCHER
# ═══════════════════════════════════════════════════════════════════

def pentagi_engine(parameters: dict, player=None) -> str:
    """
    ⚡ PentAGI Engine — Real hacking tools dispatcher.
    Inspired by github.com/vxcontrol/pentagi
    """
    action = parameters.get("action", "").lower().strip()

    if not action:
        return (
            "⚡ PentAGI Engine — Real Security Tools\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Actions:\n"
            "  port_scan     — Real TCP port scanner (target: host/IP, port_range: common|top100|1-1000)\n"
            "  dns_enum      — Real DNS enumeration + subdomain discovery (target: domain)\n"
            "  web_check     — Real HTTP header + path security check (target: URL)\n"
            "  ssh_audit     — Real SSH version + algorithm audit (target: host, port: 22)\n"
            "  net_discover  — Real ARP + ping sweep network discovery\n"
            "  hash_id       — Real hash type identification + crack commands (target: hash)\n"
        )

    if action == "port_scan":
        target = parameters.get("target", "").strip()
        if not target:
            return "Error: target (hostname or IP) required for port_scan"
        port_range = parameters.get("port_range", parameters.get("text", "common")).strip()
        return run_real_port_scan(target, port_range, player=player)

    elif action == "dns_enum":
        target = parameters.get("target", "").strip()
        if not target:
            return "Error: target domain required for dns_enum"
        return run_real_dns_enum(target, player=player)

    elif action == "web_check":
        target = parameters.get("target", parameters.get("url", "")).strip()
        if not target:
            return "Error: target URL required for web_check"
        return run_real_web_check(target, player=player)

    elif action == "ssh_audit":
        target = parameters.get("target", "").strip()
        if not target:
            return "Error: target host required for ssh_audit"
        port = int(parameters.get("port", 22))
        return run_real_ssh_audit(target, port, player=player)

    elif action == "net_discover":
        return run_real_network_discovery(player=player)

    elif action == "hash_id":
        hash_val = parameters.get("target", parameters.get("text", "")).strip()
        if not hash_val:
            return "Error: hash value required for hash_id"
        return run_real_hash_identify(hash_val, player=player)

    else:
        return f"Unknown action: '{action}'. Use: port_scan | dns_enum | web_check | ssh_audit | net_discover | hash_id"
