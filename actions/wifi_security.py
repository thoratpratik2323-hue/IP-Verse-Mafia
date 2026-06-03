"""
╔══════════════════════════════════════════════════════════════════════════╗
║         📡 WiFi SECURITY & DEFENSE AUDIT — IP PRIME MODULE              ║
║                                                                          ║
║  ⚠️  FOR EDUCATIONAL PURPOSES & AUTHORIZED AUDITING ONLY                 ║
║  ⚠️  Unauthorized access to third-party networks = ILLEGAL (IT Act 66)   ║
║                                                                          ║
║  Covers:                                                                 ║
║  • Theoretical mechanics of WPA2/WPA3 4-way handshake                    ║
║  • WEP/WPS historical vulnerability concepts                             ║
║  • Local system wireless connection posture auditing                     ║
║  • Defensive router hardening standards                                  ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import subprocess
from datetime import datetime

# Configure stdout to handle UTF-8 symbols on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BANNER = """╔══════════════════════════════════════════════════════════════╗
║        📡 WiFi SECURITY & DEFENSE AUDIT — IP PRIME           ║
║       FOR AUTHORIZED AUDITING & EDUCATION ONLY               ║
╚══════════════════════════════════════════════════════════════╝"""

LEGAL_WARNING = """
⚠️  LEGAL NOTICE:
   Bypassing security controls of networks you do not own or have
   written authorization to test is a punishable criminal offense.
   India: IT Act Section 66 & 43 → Heavy fines + jail sentence.
   Use this module only to audit your own system or local lab setup.
"""

THEORY_DATA = {
    "handshake": {
        "title": "🤝 WPA/WPA2 4-Way Handshake Mechanics",
        "description": (
            "The 4-way handshake confirms both client (Supplicant) and AP (Authenticator) "
            "possess the Pre-Shared Key (PSK) without revealing the key itself.\n\n"
            "Steps:\n"
            "1. Message 1 (AP → Client): AP sends an 'ANonce' (Authenticator Nonce, a random number).\n"
            "2. Message 2 (Client → AP): Client generates 'SNonce' (Supplicant Nonce) and derives the "
            "Pairwise Transient Key (PTK). It replies with SNonce and a MIC (Message Integrity Code) "
            "created using the key.\n"
            "3. Message 3 (AP → Client): AP derives the PTK, verifies the MIC. If valid, AP sends the GTK "
            "(Group Temporal Key) and another MIC.\n"
            "4. Message 4 (Client → AP): Client acknowledges key installation and sends a final MIC."
        ),
        "weakness": (
            "Attacker captures the 4-way handshake packets from the air. Since the handshake "
            "contains SNonce, ANonce, MAC addresses, and the MIC, they can perform an offline dictionary "
            "attack to crack the pre-shared key (PMK) by brute-forcing potential passwords."
        ),
        "defense": (
            "Use complex passwords (16+ characters) to make dictionary attacks impossible, or upgrade to "
            "WPA3 which uses SAE (Simultaneous Authentication of Equals) to prevent offline dictionary attacks."
        )
    },
    "wpa3": {
        "title": "🛡️ WPA3 & SAE (Simultaneous Authentication of Equals)",
        "description": (
            "WPA3 replaces the vulnerable pre-shared key exchange with SAE (often called Dragonfly key exchange).\n\n"
            "Key Enhancements:\n"
            "• Resistance to Offline Dictionary Attacks: An attacker who captures the handshake cannot brute-force "
            "the password offline. They must interact with the AP for every single guess, allowing the AP to block them.\n"
            "• Forward Secrecy: Even if the network password is leaked in the future, past captured traffic remains "
            "encrypted and secure.\n"
            "• PMF Mandatory: Protected Management Frames (PMF) are required, preventing easy deauthentication attacks."
        )
    },
    "wps_wep": {
        "title": "❌ Legacy Vulnerabilities: WEP and WPS PIN",
        "description": (
            "WEP (Wired Equivalent Privacy):\n"
            "Uses a weak RC4 cipher with small Initialization Vectors (IVs). Since IVs reuse quickly on busy networks, "
            "attackers can capture enough IVs to mathematically decrypt the key in minutes.\n\n"
            "WPS (Wi-Fi Protected Setup) PIN:\n"
            "Allows connection via an 8-digit PIN. The AP authenticates the first 4 digits separately from the last 4, "
            "reducing the keyspace from 100,000,000 to just 11,000 combinations. This allows cracking the PIN via brute-force "
            "in a few hours using tools like Reaver."
        ),
        "defense": "Disable WEP completely (use WPA2/WPA3). Disable WPS settings entirely in router control panel."
    }
}

HARDENING_CHECKLIST = """
📋 WIRELESS NETWORK HARDENING CONFIGURATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Disable WPS (Wi-Fi Protected Setup) in your router settings.
2. Upgrade security mode to WPA3-Personal (SAE) or WPA2/WPA3 Mixed mode.
3. Set a strong passphrase (minimum 16 random characters, symbols, numbers).
4. Enable PMF (Protected Management Frames) or 'Management Frame Protection' to block deauthentication attacks.
5. Create a isolated Guest WLAN network with separate client isolation for guests/IoT devices.
6. Disable Remote Administration on the router WAN interface.
7. Change the default router administration panel username and password.
8. Keep router firmware updated to protect against unpatched remote exploits.
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


def run_local_audit() -> str:
    """
    Runs benign OS commands to show current wireless profile configuration, security cipher, and authentication.
    """
    output_lines = [
        "📡 LOCAL WIRELESS INTERFACE AUDIT RESULTS",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    ]

    if sys.platform != "win32":
        output_lines.append("⚠️ Audit is currently optimized for Windows environments using netsh.")
        return "\n".join(output_lines)

    try:
        # Run netsh to get wireless interface settings
        res = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            errors="replace"
        )
        if res.returncode != 0:
            output_lines.append("❌ Could not query wireless interfaces. Ensure WiFi is turned on.")
            return "\n".join(output_lines)

        interface_data = res.stdout.strip()
        parsed_fields = {}
        for line in interface_data.split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                parsed_fields[key.strip().lower()] = val.strip()

        # Display important metrics
        ssid = parsed_fields.get("ssid", "Unknown / Not Connected")
        bssid = parsed_fields.get("bssid", "N/A")
        auth = parsed_fields.get("authentication", "Unknown")
        cipher = parsed_fields.get("cipher", "Unknown")
        signal = parsed_fields.get("signal", "N/A")
        state = parsed_fields.get("state", "Disconnected")

        output_lines.append(f"🟢 State          : {state}")
        output_lines.append(f"🟢 SSID           : {ssid}")
        output_lines.append(f"🟢 BSSID          : {bssid}")
        output_lines.append(f"🟢 Authentication : {auth}")
        output_lines.append(f"🟢 Encryption     : {cipher}")
        output_lines.append(f"🟢 Signal Strength: {signal}")
        output_lines.append("")

        # Evaluate risk level based on encryption
        if "wep" in auth.lower():
            output_lines.append("🚨 SECURITY RISK: Network uses WEP encryption which is highly insecure and trivial to crack.")
        elif "wpa-personal" in auth.lower() or "wpa-enterprise" in auth.lower():
            output_lines.append("⚠️ SECURITY RISK: Network uses WPA1 which is outdated. Upgrade to WPA2/WPA3.")
        elif "wpa2-personal" in auth.lower():
            output_lines.append("✅ standard: Network uses WPA2-Personal. Ensure password length is 16+ characters.")
        elif "wpa3" in auth.lower():
            output_lines.append("🛡️ EXCELLENT: Network utilizes modern WPA3 encryption. Immune to offline dictionary attacks.")
        elif "open" in auth.lower():
            output_lines.append("🚨 SECURITY RISK: Unencrypted Open network! Data is sent in plain text.")

    except Exception as e:
        output_lines.append(f"❌ Error performing audit: {e}")

    return "\n".join(output_lines)


def wifi_security(parameters: dict, player=None) -> str:
    """
    Main entry point for WiFi Security & Defense Audit module.
    """
    action = parameters.get("action", "").lower().strip()

    if not action:
        return (
            f"{BANNER}\n{LEGAL_WARNING}\n"
            "📡 SUPPORTED ACTIONS:\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "  learn            — Theoretical guides on handshakes, WEP/WPS, and WPA3 SAE\n"
            "  handshake_theory — Deep dive explanation of WPA/WPA2 4-Way handshake mechanics\n"
            "  audit_local      — Query current local connected WiFi profile & security strength\n"
            "  hardening_guide  — Best practices checklist to secure home or enterprise routers\n"
        )

    if action == "learn":
        lines = [
            BANNER, LEGAL_WARNING,
            "📚 WiFi SECURITY UNDERSTANDING GUIDE",
            "══════════════════════════════════════════════════════════════"
        ]
        for key, details in THEORY_DATA.items():
            lines.append(f"\n◈ {details['title']}")
            lines.append(details['description'])
            if "weakness" in details:
                lines.append(f"\n  🔍 Vulnerability Concept: {details['weakness']}")
        
        ai = _ai_explain(
            "You are a wireless security researcher. Briefly describe the security benefits of SAE in WPA3 "
            "over standard WPA2 PSK, and how it stops passive interception attacks. Keep it technical but under 120 words."
        )
        if ai:
            lines.append("\n" + "═" * 60 + "\n🤖 SAGE INSIGHT:\n" + ai)
        return "\n".join(lines)

    elif action == "handshake_theory":
        details = THEORY_DATA["handshake"]
        lines = [
            BANNER,
            f"\n{details['title']}",
            "══════════════════════════════════════════════════════════════",
            details['description'],
            f"\n🔍 Vulnerability: {details['weakness']}",
            f"\n🛡️ Defensive Control: {details['defense']}"
        ]
        return "\n".join(lines)

    elif action == "audit_local":
        lines = [
            BANNER,
            run_local_audit(),
            "═" * 60
        ]
        return "\n".join(lines)

    elif action == "hardening_guide":
        lines = [
            BANNER,
            HARDENING_CHECKLIST,
            "═" * 60
        ]
        return "\n".join(lines)

    else:
        return f"Unknown action: '{action}'. Use: learn | handshake_theory | audit_local | hardening_guide"
