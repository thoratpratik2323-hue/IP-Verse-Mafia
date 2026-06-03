"""
╔══════════════════════════════════════════════════════════════════════════╗
║       🌐 MYTHOS INTERNET CORE — IP PRIME LIVE KNOWLEDGE ENGINE 🌐        ║
║                                                                          ║
║  Real Internet Access for Mythos Sentinel:                               ║
║  • NVD/NIST CVE Database (real-time, no key needed)                      ║
║  • ExploitDB live search                                                 ║
║  • GitHub PoC exploit search                                             ║
║  • DuckDuckGo instant answers                                            ║
║  • CIRCL CVE Search API                                                  ║
║  • Any URL reader / web scraper                                          ║
║  • Shodan (if API key set)                                               ║
║  • HaveIBeenPwned breach check                                           ║
║  • crt.sh certificate transparency (subdomain discovery)                 ║
║                                                                          ║
║  "Claude ke jaisi knowledge, Prime ki real execution."                   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import re
import time
import socket
import urllib.request
import urllib.parse
import urllib.error
import ssl
import html
from datetime import datetime
from typing import Optional

# Fix Windows encoding
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# SSL context (ignore certs for security research)
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

BANNER = """╔══════════════════════════════════════════════════════════════╗
║     🌐 MYTHOS INTERNET — LIVE KNOWLEDGE ENGINE 🌐             ║
╚══════════════════════════════════════════════════════════════╝"""


def _get_api_key():
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = os.path.join(base, "config", "api_keys.json")
        with open(cfg, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _http_get(url: str, headers: dict = None, timeout: int = 12) -> str:
    """Safe HTTP GET with retries."""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (IP-Prime-Mythos/2.0; +https://github.com/thoratpratik2323-hue/IP-Verse-Mafia)",
        "Accept": "application/json, text/html, */*",
    }
    if headers:
        default_headers.update(headers)
    try:
        req = urllib.request.Request(url, headers=default_headers)
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX) as resp:
            raw = resp.read()
            return raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"HTTP_ERROR:{e.code}"
    except Exception as e:
        return f"ERROR:{e}"


def _html_to_text(html_content: str, max_chars: int = 3000) -> str:
    """Strip HTML tags and clean text."""
    # Remove scripts and styles
    text = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    # Remove tags
    text = re.sub(r"<[^>]+>", " ", text)
    # Decode HTML entities
    text = html.unescape(text)
    # Clean whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _ai_enhance(prompt: str, max_tokens: int = 800) -> str:
    """Use Gemini to enhance/analyze internet data."""
    keys = _get_api_key()
    api_key = keys.get("gemini_api_key", "")
    if not api_key:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        try:
            resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        except Exception:
            resp = client.models.generate_content(model="gemini-flash-latest", contents=prompt)
        return resp.text.strip()
    except Exception:
        return ""


# ════════════════════════════════════════════════════════════════════
# 1. LIVE CVE SEARCH — NVD/NIST (No API Key Needed)
# ════════════════════════════════════════════════════════════════════

def search_cve_live(query: str, limit: int = 10) -> str:
    """
    🔴 LIVE CVE SEARCH using NVD NIST API (official, free, no key needed).
    Search by software name, CVE ID, or keyword.
    """
    lines = [BANNER, f"         🔴 LIVE CVE SEARCH: '{query}'",
             "══════════════════════════════════════════════════════════════"]

    # Check if it's a CVE ID
    cve_pattern = re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE)
    is_cve_id = cve_pattern.match(query.strip())

    if is_cve_id:
        # Direct CVE lookup
        cve_id = query.strip().upper()
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
    else:
        # Keyword search
        encoded = urllib.parse.quote(query)
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={encoded}&resultsPerPage={limit}"

    raw = _http_get(url)

    if raw.startswith("ERROR") or raw.startswith("HTTP_ERROR"):
        # Fallback: CIRCL CVE search
        lines.append("  NVD API timeout → trying CIRCL CVE Search...")
        circl_url = f"https://cve.circl.lu/api/search/{urllib.parse.quote(query)}"
        raw = _http_get(circl_url)

    try:
        data = json.loads(raw)
        vulnerabilities = data.get("vulnerabilities", [])

        if not vulnerabilities:
            lines.append(f"  No CVEs found for '{query}'")
            return "\n".join(lines)

        lines.append(f"  Found: {data.get('totalResults', len(vulnerabilities))} CVEs | Showing top {len(vulnerabilities)}")
        lines.append("─" * 66)

        for item in vulnerabilities[:limit]:
            cve = item.get("cve", {})
            cve_id = cve.get("id", "N/A")

            # Get CVSS score
            metrics = cve.get("metrics", {})
            score = "N/A"
            severity = "UNKNOWN"
            for metric_key in ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]:
                metric_list = metrics.get(metric_key, [])
                if metric_list:
                    cvss_data = metric_list[0].get("cvssData", {})
                    score = cvss_data.get("baseScore", "N/A")
                    severity = metric_list[0].get("baseSeverity", "N/A")
                    break

            # Get description
            descs = cve.get("descriptions", [])
            desc = next((d["value"] for d in descs if d.get("lang") == "en"), "No description")

            # Color-code severity
            sev_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(severity.upper(), "⚪")

            # Published date
            published = cve.get("published", "")[:10]

            lines += [
                f"",
                f"  {sev_icon} {cve_id}  |  CVSS: {score}  |  {severity}  |  Published: {published}",
                f"  📝 {desc[:180]}{'...' if len(desc) > 180 else ''}",
                f"  🔗 https://nvd.nist.gov/vuln/detail/{cve_id}",
                f"  🔗 https://www.exploit-db.com/search?cve={cve_id}",
            ]

            # References
            refs = cve.get("references", [])[:2]
            for ref in refs:
                lines.append(f"     📎 {ref.get('url', '')[:80]}")

        # AI analysis
        lines.append("\n─" * 33)
        cve_summary = "\n".join([
            f"{item.get('cve', {}).get('id', '')}: " +
            next((d["value"] for d in item.get("cve", {}).get("descriptions", []) if d.get("lang") == "en"), "")[:100]
            for item in vulnerabilities[:5]
        ])
        ai = _ai_enhance(
            f"Security expert: Analyze these CVEs for '{query}' and give top attack priority + mitigation. Be tactical. Max 120 words:\n{cve_summary}"
        )
        if ai:
            lines += ["🤖 AI TACTICAL ANALYSIS:", ai]

    except json.JSONDecodeError:
        lines.append(f"  Parse error. Raw response: {raw[:200]}")

    lines.append("═" * 66)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 2. EXPLOITDB LIVE SEARCH
# ════════════════════════════════════════════════════════════════════

def search_exploitdb_live(query: str) -> str:
    """
    💥 LIVE ExploitDB Search — finds real public exploits.
    """
    lines = [BANNER, f"         💥 LIVE EXPLOITDB: '{query}'",
             "══════════════════════════════════════════════════════════════"]

    encoded = urllib.parse.quote(query)
    url = f"https://www.exploit-db.com/search?q={encoded}"

    raw = _http_get(url, headers={"Accept": "text/html"})

    if raw.startswith("ERROR"):
        lines.append(f"  ExploitDB unavailable: {raw}")
        return "\n".join(lines)

    # Parse exploit IDs from HTML
    edb_ids = re.findall(r'/exploits/(\d+)', raw)
    edb_ids = list(dict.fromkeys(edb_ids))[:10]  # unique, top 10

    # Also parse titles
    titles = re.findall(r'<td class="exploit_title"[^>]*>([^<]+)</td>', raw)

    if not edb_ids:
        lines.append(f"  No exploits found for '{query}'")
        # Try Shodan CVE search as fallback
        lines.append(f"  Try: https://sploitus.com/?query={encoded}")
        lines.append(f"  Try: https://packetstormsecurity.com/search/?q={encoded}")
        return "\n".join(lines)

    lines.append(f"  Found {len(edb_ids)} exploits:")
    lines.append("─" * 66)

    for i, eid in enumerate(edb_ids[:8]):
        title = titles[i] if i < len(titles) else f"Exploit #{eid}"
        lines += [
            f"  💥 EDB-{eid}: {title[:70]}",
            f"     🔗 https://www.exploit-db.com/exploits/{eid}",
            f"     📥 https://www.exploit-db.com/download/{eid}",
            "",
        ]

    # GitHub PoC search
    lines += [
        "─" * 66,
        "🐙 GITHUB PoC EXPLOITS:",
        f"  🔗 https://github.com/search?q={encoded}+exploit&type=repositories",
        f"  🔗 https://github.com/search?q={encoded}+poc&type=code",
        f"  🔗 https://sploitus.com/?query={encoded}",
    ]

    lines.append("═" * 66)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 3. LIVE WEB SEARCH (DuckDuckGo Instant Answers + scrape)
# ════════════════════════════════════════════════════════════════════

def web_search_live(query: str, search_type: str = "general") -> str:
    """
    🔍 LIVE WEB SEARCH — DuckDuckGo instant answers + security-focused results.
    """
    lines = [BANNER, f"         🔍 LIVE WEB SEARCH: '{query}'",
             "══════════════════════════════════════════════════════════════"]

    # DuckDuckGo Instant Answer API (free, no key)
    encoded = urllib.parse.quote(query)
    ddg_url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"

    raw = _http_get(ddg_url)

    try:
        data = json.loads(raw)
        abstract = data.get("Abstract", "")
        abstract_source = data.get("AbstractSource", "")
        abstract_url = data.get("AbstractURL", "")
        answer = data.get("Answer", "")
        related = data.get("RelatedTopics", [])

        if answer:
            lines += ["💡 INSTANT ANSWER:", f"  {answer}", ""]

        if abstract:
            lines += [
                f"📚 FROM {abstract_source}:",
                f"  {abstract[:400]}",
                f"  🔗 {abstract_url}",
                "",
            ]

        if related:
            lines.append("🔗 RELATED RESULTS:")
            for topic in related[:6]:
                if isinstance(topic, dict) and topic.get("Text"):
                    text = topic.get("Text", "")[:100]
                    url = topic.get("FirstURL", "")
                    lines.append(f"  • {text}")
                    if url:
                        lines.append(f"    {url}")

        if not abstract and not answer and not related:
            lines.append(f"  No instant results. Try these:")
            lines += [
                f"  🔍 https://duckduckgo.com/?q={encoded}",
                f"  🔍 https://www.google.com/search?q={encoded}",
            ]

    except json.JSONDecodeError:
        lines.append(f"  Search parse error.")

    # Security-specific additional resources
    if any(kw in query.lower() for kw in ["hack", "exploit", "cve", "vuln", "attack", "pentest", "ctf"]):
        lines += [
            "",
            "🔐 SECURITY RESOURCES:",
            f"  📚 https://nvd.nist.gov/vuln/search/results?query={encoded}",
            f"  💥 https://www.exploit-db.com/search?q={encoded}",
            f"  🕷️  https://sploitus.com/?query={encoded}",
            f"  🐙 https://github.com/search?q={encoded}&type=repositories",
            f"  📖 https://book.hacktricks.xyz/",
            f"  🏆 https://gtfobins.github.io/",
        ]

    lines.append("═" * 66)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 4. URL READER / WEB SCRAPER
# ════════════════════════════════════════════════════════════════════

def read_url_live(url: str, summarize: bool = True) -> str:
    """
    📄 READ ANY URL — Fetches and reads content from any webpage.
    Optionally summarizes with AI.
    """
    if not url.startswith("http"):
        url = "https://" + url

    lines = [BANNER, f"         📄 URL READER: {url[:60]}",
             "══════════════════════════════════════════════════════════════"]

    raw = _http_get(url, timeout=15)

    if raw.startswith("ERROR") or raw.startswith("HTTP_ERROR"):
        lines.append(f"  ❌ Failed to fetch: {raw}")
        return "\n".join(lines)

    # Extract title
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
    if title_match:
        lines.append(f"  📌 Title: {html.unescape(title_match.group(1).strip())[:100]}")

    # Extract main content
    text = _html_to_text(raw, max_chars=4000)
    lines += ["", "📝 CONTENT:", "─" * 66, text[:2000]]

    if summarize and len(text) > 200:
        lines += ["", "─" * 66]
        ai = _ai_enhance(
            f"Summarize this webpage content for a security researcher. Extract key info, vulnerabilities, techniques. Max 150 words:\n\n{text[:3000]}"
        )
        if ai:
            lines += ["🤖 AI SUMMARY:", ai]

    lines.append("═" * 66)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 5. LIVE BREACH CHECK (HaveIBeenPwned - public API)
# ════════════════════════════════════════════════════════════════════

def check_breach_live(email_or_username: str) -> str:
    """
    🔑 BREACH DATABASE CHECK — Check if email/account has been in data breaches.
    Uses HaveIBeenPwned v3 API + DeHashed patterns.
    """
    lines = [BANNER, f"         🔑 BREACH CHECK: '{email_or_username}'",
             "══════════════════════════════════════════════════════════════"]

    target = email_or_username.strip()
    is_email = "@" in target

    # HIBP API (requires API key for v3, but we check publicly)
    if is_email:
        encoded = urllib.parse.quote(target)
        # Try HIBP
        hibp_url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{encoded}"
        raw = _http_get(hibp_url, headers={
            "hibp-api-key": _get_api_key().get("hibp_api_key", ""),
            "User-Agent": "IP-Prime-Mythos"
        })

        if "HTTP_ERROR:401" in raw or "HTTP_ERROR:403" in raw:
            lines += [
                "  ⚠️ HIBP requires paid API key for email lookup.",
                "  Use these free alternatives:",
                f"  🔍 https://haveibeenpwned.com/account/{encoded}",
                f"  🔍 https://breachdirectory.org/",
                f"  🔍 https://dehashed.com/search?query={encoded}",
                f"  🔍 https://leak-lookup.com/",
                f"  🔍 https://intelx.io/?s={encoded}",
            ]
        elif "HTTP_ERROR:404" in raw:
            lines.append(f"  ✅ GOOD NEWS: '{target}' not found in known breaches!")
        elif not raw.startswith("ERROR"):
            try:
                breaches = json.loads(raw)
                lines.append(f"  🔴 FOUND IN {len(breaches)} BREACH(ES)!")
                lines.append("─" * 66)
                for b in breaches[:10]:
                    lines += [
                        f"  💀 {b.get('Name', 'Unknown')} ({b.get('BreachDate', 'N/A')})",
                        f"     Compromised: {', '.join(b.get('DataClasses', [])[:5])}",
                        f"     Accounts: {b.get('PwnCount', 'N/A'):,}",
                    ]
            except Exception:
                pass
    else:
        lines += [
            f"  Username/domain check for: {target}",
            f"  🔍 https://whatsmyname.app/ (username tracking)",
            f"  🔍 https://namechk.com/ (social media check)",
            f"  🔍 https://sherlock.project/ (open source tool)",
        ]

    # Password breach check (k-anonymity, safe)
    lines += [
        "",
        "─" * 66,
        "🔑 PASSWORD BREACH CHECK (safe k-anonymity method):",
        "  python -c \"",
        "  import hashlib, requests",
        "  p = 'your_password'",
        "  h = hashlib.sha1(p.encode()).hexdigest().upper()",
        "  r = requests.get(f'https://api.pwnedpasswords.com/range/{h[:5]}')",
        "  print('PWNED!' if h[5:] in r.text else 'SAFE')\"",
    ]

    lines.append("═" * 66)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 6. LIVE SUBDOMAIN DISCOVERY (crt.sh certificate transparency)
# ════════════════════════════════════════════════════════════════════

def discover_subdomains_live(domain: str) -> str:
    """
    🌐 LIVE SUBDOMAIN DISCOVERY via crt.sh Certificate Transparency logs.
    Finds real subdomains from SSL certificate history.
    """
    lines = [BANNER, f"         🌐 LIVE SUBDOMAIN DISCOVERY: {domain}",
             "══════════════════════════════════════════════════════════════"]

    # crt.sh - certificate transparency (completely free, no key)
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    raw = _http_get(url)

    if raw.startswith("ERROR"):
        lines.append(f"  ❌ crt.sh unavailable: {raw}")
        return "\n".join(lines)

    try:
        data = json.loads(raw)

        # Extract unique subdomains
        subdomains = set()
        for entry in data:
            name = entry.get("name_value", "")
            for sub in name.split("\n"):
                sub = sub.strip().lower()
                if sub.endswith(f".{domain}") and "*" not in sub:
                    subdomains.add(sub)

        subdomains = sorted(subdomains)
        lines += [
            f"  📊 Found {len(subdomains)} unique subdomains from SSL cert history:",
            "─" * 66,
        ]

        if not subdomains:
            lines.append(f"  No subdomains found for {domain}")
        else:
            # Resolve IPs for interesting subdomains
            interesting = [s for s in subdomains if any(kw in s for kw in
                ["admin", "api", "dev", "test", "staging", "vpn", "mail", "ftp",
                 "db", "database", "jenkins", "gitlab", "jira", "beta", "internal"])]

            if interesting:
                lines.append("  🎯 HIGH-VALUE TARGETS:")
                for sub in interesting[:15]:
                    try:
                        ip = socket.gethostbyname(sub)
                        lines.append(f"  🔴 {sub:<45} → {ip}")
                    except Exception:
                        lines.append(f"  ⚪ {sub:<45} (no DNS)")

            lines += ["", "  📋 ALL SUBDOMAINS:"]
            for sub in subdomains[:50]:
                lines.append(f"  • {sub}")

            if len(subdomains) > 50:
                lines.append(f"  ... and {len(subdomains) - 50} more")

        # AI analysis
        if subdomains:
            lines.append("─" * 66)
            ai = _ai_enhance(
                f"Penetration tester: Analyze these subdomains of {domain} and identify the most interesting attack targets:\n"
                + "\n".join(list(subdomains)[:20])
                + "\nMax 100 words, be tactical."
            )
            if ai:
                lines += ["🤖 AI TARGET ANALYSIS:", ai]

    except json.JSONDecodeError:
        lines.append(f"  Parse error from crt.sh")

    lines.append("═" * 66)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# 7. SHODAN LOOKUP (requires API key)
# ════════════════════════════════════════════════════════════════════

def shodan_lookup_live(target: str) -> str:
    """
    🔭 SHODAN IP/HOST LOOKUP — Internet-connected device intelligence.
    Requires SHODAN_API_KEY in config/api_keys.json
    """
    lines = [BANNER, f"         🔭 SHODAN LOOKUP: {target}",
             "══════════════════════════════════════════════════════════════"]

    keys = _get_api_key()
    shodan_key = keys.get("shodan_api_key", "")

    if not shodan_key:
        lines += [
            "  ⚠️ No Shodan API key found.",
            "  Add to config/api_keys.json: \"shodan_api_key\": \"your_key\"",
            "  Get free key at: https://account.shodan.io/",
            "",
            "  💡 Free alternatives (no key needed):",
            f"  🔍 https://www.shodan.io/host/{target} (browser)",
            f"  🔍 https://censys.io/hosts/{target}",
            f"  🔍 https://fofa.info/result?qbase64=... ",
            f"  🔍 https://hunter.how/",
            f"  🔍 https://viz.greynoise.io/ip/{target}",
        ]
        return "\n".join(lines)

    # Resolve hostname to IP if needed
    try:
        ip = socket.gethostbyname(target)
    except Exception:
        ip = target

    url = f"https://api.shodan.io/shodan/host/{ip}?key={shodan_key}"
    raw = _http_get(url)

    try:
        data = json.loads(raw)

        if "error" in data:
            lines.append(f"  Shodan error: {data['error']}")
            return "\n".join(lines)

        lines += [
            f"  🌐 IP          : {data.get('ip_str', ip)}",
            f"  🏢 Organization: {data.get('org', 'N/A')}",
            f"  🌍 Country     : {data.get('country_name', 'N/A')} ({data.get('country_code', '')})",
            f"  🏙️  City        : {data.get('city', 'N/A')}",
            f"  🔄 Last Update : {data.get('last_update', 'N/A')}",
            "",
            "📡 OPEN PORTS & SERVICES:",
            "─" * 66,
        ]

        for port_data in data.get("data", [])[:10]:
            port = port_data.get("port", "?")
            transport = port_data.get("transport", "tcp")
            product = port_data.get("product", "Unknown")
            version = port_data.get("version", "")
            banner = port_data.get("data", "")[:80].replace("\n", " ")
            vulns = port_data.get("vulns", {})

            lines.append(f"  🟢 {port}/{transport}  {product} {version}")
            if banner:
                lines.append(f"     Banner: {banner}")
            if vulns:
                for vuln_id in list(vulns.keys())[:3]:
                    lines.append(f"     🔴 {vuln_id}: {vulns[vuln_id].get('summary', '')[:80]}")

        # Hostnames
        hostnames = data.get("hostnames", [])
        if hostnames:
            lines += ["", f"  🏷️ Hostnames: {', '.join(hostnames[:5])}"]

        # Tags
        tags = data.get("tags", [])
        if tags:
            lines += [f"  🏷️ Tags: {', '.join(tags)}"]

    except json.JSONDecodeError:
        lines.append(f"  Response: {raw[:300]}")

    lines.append("═" * 66)
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════════
# MAIN DISPATCHER
# ════════════════════════════════════════════════════════════════════

def mythos_internet(parameters: dict, player=None) -> str:
    """
    🌐 Mythos Internet Core — Live knowledge engine for IP Prime.
    Gives Mythos Claude-like internet access for security research.
    """
    action = parameters.get("action", "").lower().strip()

    def log(msg):
        if player:
            player.write_log(f"[MythosInternet] {msg}")

    if not action:
        return (
            f"{BANNER}\n\n"
            "🌐 MYTHOS INTERNET — Live Knowledge Actions:\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  cve_search     — Live CVE/vulnerability search (NVD NIST)\n"
            "  exploit_search — Live ExploitDB search\n"
            "  web_search     — DuckDuckGo live search\n"
            "  read_url       — Read any URL / webpage content\n"
            "  breach_check   — Email breach database lookup\n"
            "  subdomains     — Live subdomain discovery (crt.sh)\n"
            "  shodan         — Shodan IP intelligence lookup\n"
        )

    if action == "cve_search":
        query = parameters.get("query", parameters.get("target", "")).strip()
        if not query:
            return "Error: 'query' required. E.g., query='apache log4j' or query='CVE-2021-44228'"
        limit = int(parameters.get("limit", 10))
        log(f"Live CVE search: {query}")
        return search_cve_live(query, limit)

    elif action == "exploit_search":
        query = parameters.get("query", parameters.get("target", "")).strip()
        if not query:
            return "Error: 'query' required."
        log(f"Live ExploitDB search: {query}")
        return search_exploitdb_live(query)

    elif action == "web_search":
        query = parameters.get("query", parameters.get("target", "")).strip()
        if not query:
            return "Error: 'query' required."
        log(f"Live web search: {query}")
        return web_search_live(query)

    elif action == "read_url":
        url = parameters.get("url", parameters.get("target", "")).strip()
        if not url:
            return "Error: 'url' required."
        summarize = parameters.get("summarize", True)
        log(f"Reading URL: {url}")
        return read_url_live(url, summarize=summarize)

    elif action == "breach_check":
        target = parameters.get("target", parameters.get("email", "")).strip()
        if not target:
            return "Error: 'target' (email or username) required."
        log(f"Breach check: {target}")
        return check_breach_live(target)

    elif action == "subdomains":
        domain = parameters.get("domain", parameters.get("target", "")).strip()
        if not domain:
            return "Error: 'domain' required."
        log(f"Live subdomain discovery: {domain}")
        return discover_subdomains_live(domain)

    elif action == "shodan":
        target = parameters.get("target", "").strip()
        if not target:
            return "Error: 'target' (IP or hostname) required."
        log(f"Shodan lookup: {target}")
        return shodan_lookup_live(target)

    else:
        return f"Unknown action: '{action}'. Use: cve_search | exploit_search | web_search | read_url | breach_check | subdomains | shodan"
