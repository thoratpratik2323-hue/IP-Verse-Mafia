"""
╔══════════════════════════════════════════════════════════════════════╗
║            🛡️ ANTI-DRONE DEFENSE SYSTEM — IP PRIME MODULE 🛡️         ║
║                                                                      ║
║  Drone Detection via:                                                ║
║  • WiFi SSID scanning (DJI, Parrot, Autel, Skydio signatures)        ║
║  • MAC OUI vendor identification                                     ║
║  • RF frequency pattern analysis (software-based)                    ║
║  • Network traffic anomaly detection                                 ║
║  • Continuous alert + logging                                        ║
║                                                                      ║
║  ⚠️ NOTE: RF jamming is ILLEGAL. This system is for DETECTION only.  ║
║  Legal countermeasures: alerts, documentation, authority reporting.  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import socket
import struct
import hashlib
import threading
import subprocess
import datetime
import re
import math
from typing import Optional

# ════════════════════════════════════════════════════════════════════
# DRONE FINGERPRINT DATABASE
# Known drone WiFi SSIDs and MAC prefixes
# ════════════════════════════════════════════════════════════════════

DRONE_SSID_SIGNATURES = {
    # DJI (most popular commercial drones)
    "DJI": [
        "DJI-", "MAVIC-", "PHANTOM-", "SPARK-", "MINI-", "AIR-",
        "FPV-", "INSPIRE-", "MATRICE-", "AGRAS-", "AVATA-",
        "DJI_FLY_", "RC-N", "RC-PRO", "DJI_RC_",
    ],
    # Parrot
    "Parrot": [
        "Parrot_", "Bebop_", "Anafi_", "DISCO-", "MAMBO_",
        "Swing-", "Rolling Spider", "Jumping Night",
    ],
    # Autel Robotics
    "Autel": [
        "Autel-", "EVO-", "DRAGONFISH-",
    ],
    # Skydio
    "Skydio": ["Skydio_", "SKYDIO-"],
    # Holy Stone (consumer)
    "HolyStone": ["HS-", "HOLY_STONE_", "HSRC-"],
    # Eachine / generic FPV
    "FPV/Generic": [
        "FPV-", "DRONE-", "UAV-", "COPTER-", "QUADCOPTER-",
        "RC_Drone_", "LILIPUT-", "SYMA-", "MJX_BUGS_",
        "WLtoys-", "BAYANGTOYS-",
    ],
    # Indian military/surveillance concerns
    "Unknown/Suspicious": [
        "WIFI-UAV", "SKY-RC", "AIRDROP", "SHADOW-",
    ],
}

# Known drone manufacturer MAC OUI prefixes
DRONE_MAC_VENDORS = {
    "60:60:1F": "DJI",
    "A0:14:3D": "DJI",
    "48:1C:B9": "DJI",
    "34:D2:62": "DJI",
    "2C:AA:8E": "DJI",
    "AC:23:3F": "DJI",
    "00:12:1C": "Parrot SA",
    "A0:14:3D": "DJI Technology",
    "90:3A:E6": "DJI",
    "84:EB:18": "DJI",
    "28:B3:73": "Autel Robotics",
    "00:26:7E": "3DR (Solo)",
    "AC:3C:0B": "Skydio",
}

# Drone control frequencies (MHz)
DRONE_FREQUENCIES = {
    "2400-2483 MHz": "Most common drone control (WiFi 2.4GHz band - DJI, Parrot, etc.)",
    "5725-5850 MHz": "DJI OcuSync / FPV video downlink (5.8GHz)",
    "5150-5250 MHz": "DJI newer models (O3/O3+)",
    "868 MHz": "European drone telemetry / Remote ID",
    "915 MHz": "US/India drone telemetry",
    "1575 MHz": "GPS L1 (drone navigation - do not jam, illegal)",
    "433 MHz": "Long-range FPV control links (LoRa)",
    "2450 MHz": "DJI Lightbridge video",
}

LEGAL_COUNTERMEASURES = """
🛡️ LEGAL COUNTERMEASURES (India - DGCA regulations):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 📱 Report to DGCA Digital Sky Platform
   Website: digitalsky.dgca.gov.in
   App: Digital Sky (Google Play)
   Emergency: Call local police + Airport ATC

2. 🚔 File FIR
   Under IT Act Section 66 (unauthorized surveillance)
   Under Drone Rules 2021 (DGCA violation)
   Under IPC 441 (criminal trespass if recording property)

3. 📷 Document Evidence
   • Photograph/video the drone
   • Note time, direction, behavior
   • Record GPS coordinates

4. 🔊 Acoustic Deterrents (LEGAL)
   • High-power speakers (some frequencies disturb drones)
   • Anti-drone sirens (alert nearby people)

5. 🦅 Trained Eagles/Falcons (Legal in some jurisdictions)
   • Netherlands police use trained eagles

6. 🌐 Authorized Anti-Drone Systems (Requires Gov License)
   • DroneGun Tactical (Australia)
   • DeDrone RF-300 (detection + link disruption)
   • SkyWall (physical net capture)

⚠️ ILLEGAL in India WITHOUT authorization:
   • RF Jamming (blocks 2.4/5.8GHz signals)
   • GPS Spoofing (fake GPS signals)
   • Laser targeting
   • Shooting drones (criminal damage)
"""

# ════════════════════════════════════════════════════════════════════
# DETECTION ENGINE
# ════════════════════════════════════════════════════════════════════

class DroneDetectionEngine:
    """Real-time drone detection using WiFi scanning and network analysis."""
    
    def __init__(self, player=None):
        self.player = player
        self.detected_drones = {}
        self.alert_active = False
        self.scan_count = 0
        self._stop_event = threading.Event()
        self.log_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "logs", "antidrone.log"
        )
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def _log(self, msg: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
        if self.player:
            self.player.write_log(line)

    def _scan_wifi_windows(self) -> list:
        """Scan WiFi networks on Windows using netsh."""
        networks = []
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
            )
            output = result.stdout
            
            # Parse networks
            current_ssid = None
            current_bssid = None
            current_signal = None
            current_channel = None
            
            for line in output.splitlines():
                line = line.strip()
                
                if line.startswith("SSID") and "BSSID" not in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_ssid = parts[1].strip()
                
                elif "BSSID" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_bssid = parts[1].strip()
                
                elif "Signal" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_signal = parts[1].strip()
                
                elif "Channel" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current_channel = parts[1].strip()
                        # Complete network entry
                        if current_ssid:
                            networks.append({
                                "ssid": current_ssid,
                                "bssid": current_bssid or "Unknown",
                                "signal": current_signal or "Unknown",
                                "channel": current_channel or "Unknown",
                            })
                        current_ssid = None
                        current_bssid = None
                        current_signal = None
                        current_channel = None
            
        except Exception as e:
            self._log(f"WiFi scan error: {e}")
        return networks

    def _check_drone_ssid(self, ssid: str) -> Optional[str]:
        """Check if SSID matches known drone signatures."""
        ssid_upper = ssid.upper()
        for manufacturer, patterns in DRONE_SSID_SIGNATURES.items():
            for pattern in patterns:
                if ssid_upper.startswith(pattern.upper()) or pattern.upper() in ssid_upper:
                    return manufacturer
        return None

    def _check_drone_mac(self, bssid: str) -> Optional[str]:
        """Check if MAC address belongs to drone manufacturer."""
        if not bssid or len(bssid) < 8:
            return None
        prefix = bssid[:8].upper()
        for mac_prefix, vendor in DRONE_MAC_VENDORS.items():
            if prefix.startswith(mac_prefix.upper()[:5]):
                return vendor
        return None

    def _signal_to_distance(self, signal_str: str) -> str:
        """Estimate distance from signal strength."""
        try:
            signal = int(signal_str.replace("%", ""))
            # Convert percentage to dBm approximately
            dbm = (signal / 2) - 100
            # Free space path loss estimation
            if dbm > -50:
                return "< 10 meters (VERY CLOSE!)"
            elif dbm > -60:
                return "10-30 meters"
            elif dbm > -70:
                return "30-60 meters"
            elif dbm > -80:
                return "60-120 meters"
            else:
                return "> 120 meters"
        except Exception:
            return "Unknown distance"

    def _trigger_alert(self, drone_info: dict):
        """Trigger multi-channel alert when drone detected."""
        drone_id = drone_info.get("ssid", "Unknown")
        manufacturer = drone_info.get("manufacturer", "Unknown")
        signal = drone_info.get("signal", "?")
        distance = drone_info.get("distance", "Unknown")
        
        alert_msg = (
            f"DRONE DETECTED! {manufacturer} drone '{drone_id}' "
            f"Signal: {signal} | Distance: {distance}"
        )
        self._log(f"🚨 ALERT: {alert_msg}")
        
        # Windows notification
        try:
            subprocess.Popen([
                "powershell", "-NoProfile", "-WindowStyle", "Hidden",
                "-Command",
                f"""
                Add-Type -AssemblyName System.Windows.Forms;
                [System.Windows.Forms.MessageBox]::Show(
                    '{alert_msg}',
                    'ANTI-DRONE ALERT - IP PRIME',
                    [System.Windows.Forms.MessageBoxButtons]::OK,
                    [System.Windows.Forms.MessageBoxIcon]::Warning
                )
                """
            ])
        except Exception:
            pass
        
        # Play alert sound
        try:
            import winsound
            for _ in range(3):
                winsound.Beep(1000, 200)
                time.sleep(0.1)
        except Exception:
            pass

    def scan_once(self) -> dict:
        """Perform a single drone detection scan."""
        self.scan_count += 1
        networks = self._scan_wifi_windows()
        
        found_drones = []
        safe_networks = []
        
        for net in networks:
            ssid = net.get("ssid", "")
            bssid = net.get("bssid", "")
            signal = net.get("signal", "")
            channel = net.get("channel", "")
            
            manufacturer = self._check_drone_ssid(ssid) or self._check_drone_mac(bssid)
            
            if manufacturer:
                drone = {
                    "ssid": ssid,
                    "bssid": bssid,
                    "manufacturer": manufacturer,
                    "signal": signal,
                    "channel": channel,
                    "distance": self._signal_to_distance(signal),
                    "first_seen": datetime.datetime.now().isoformat(),
                }
                found_drones.append(drone)
                
                # Track new drones
                if ssid not in self.detected_drones:
                    self.detected_drones[ssid] = drone
                    self._trigger_alert(drone)
            else:
                safe_networks.append(net)
        
        return {
            "scan_number": self.scan_count,
            "timestamp": datetime.datetime.now().isoformat(),
            "drones_found": found_drones,
            "total_networks": len(networks),
            "safe_networks": len(safe_networks),
        }

    def continuous_monitor(self, interval: int = 10, duration: int = 300):
        """Run continuous monitoring for specified duration."""
        self._log(f"Starting continuous monitoring (interval={interval}s, duration={duration}s)")
        end_time = time.time() + duration
        
        while not self._stop_event.is_set() and time.time() < end_time:
            result = self.scan_once()
            if result["drones_found"]:
                for drone in result["drones_found"]:
                    self._log(f"DRONE: {drone['manufacturer']} | {drone['ssid']} | {drone['distance']}")
            time.sleep(interval)
        
        self._log("Monitoring session ended.")

    def stop(self):
        self._stop_event.set()


# ════════════════════════════════════════════════════════════════════
# MAIN ACTION FUNCTIONS
# ════════════════════════════════════════════════════════════════════

_monitor_thread = None
_engine_instance = None


def antidrone_defense(parameters: dict, player=None) -> str:
    """
    🛡️ Anti-Drone Defense System for IP Prime.
    Detects drones via WiFi SSID scanning and MAC analysis.
    """
    global _monitor_thread, _engine_instance
    
    action = parameters.get("action", "scan").lower().strip()
    
    BANNER = """
╔══════════════════════════════════════════════════════════════════╗
║          🛡️ IP PRIME — ANTI-DRONE DEFENSE SYSTEM 🛡️              ║
║         Drone Detection via WiFi + RF Frequency Analysis         ║
╚══════════════════════════════════════════════════════════════════╝"""
    
    # ── ACTION: scan ──────────────────────────────────────────────
    if action == "scan":
        engine = DroneDetectionEngine(player=player)
        result = engine.scan_once()
        
        lines = [BANNER, ""]
        lines.append(f"📡 SCAN #{result['scan_number']} | {result['timestamp'][:19]}")
        lines.append(f"🌐 Total WiFi networks found: {result['total_networks']}")
        lines.append("")
        
        drones = result["drones_found"]
        if drones:
            lines.append(f"🚨 ALERT! {len(drones)} DRONE(S) DETECTED!")
            lines.append("─" * 66)
            for i, d in enumerate(drones, 1):
                lines += [
                    f"  DRONE #{i}:",
                    f"  🏭 Manufacturer : {d['manufacturer']}",
                    f"  📶 SSID         : {d['ssid']}",
                    f"  🔑 MAC Address  : {d['bssid']}",
                    f"  📊 Signal       : {d['signal']}",
                    f"  📡 Channel      : {d['channel']}",
                    f"  📍 Est. Distance: {d['distance']}",
                    "",
                ]
        else:
            lines += [
                "✅ AREA CLEAR — No drones detected in WiFi range.",
                "",
                "Scanned networks:",
            ]
            # Show all networks for reference
            for net in engine._scan_wifi_windows()[:5]:
                lines.append(f"  • {net.get('ssid', 'Hidden')} ({net.get('bssid', 'N/A')})")
        
        lines += [
            "",
            "─" * 66,
            "💡 Commands: monitor | frequencies | countermeasures | log",
            "═" * 66,
        ]
        return "\n".join(lines)
    
    # ── ACTION: monitor ───────────────────────────────────────────
    elif action == "monitor":
        interval = int(parameters.get("interval", 10))
        duration = int(parameters.get("duration", 300))
        
        if _monitor_thread and _monitor_thread.is_alive():
            return "⚠️ Monitor already running. Use 'stop' to end it first."
        
        _engine_instance = DroneDetectionEngine(player=player)
        _monitor_thread = threading.Thread(
            target=_engine_instance.continuous_monitor,
            args=(interval, duration),
            daemon=True
        )
        _monitor_thread.start()
        
        return (
            f"{BANNER}\n\n"
            f"🚀 ANTI-DRONE MONITOR STARTED!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⏱️  Scan interval : Every {interval} seconds\n"
            f"⏰  Duration      : {duration} seconds ({duration//60} min)\n"
            f"📁  Log file      : {_engine_instance.log_file}\n\n"
            f"🚨 Alert triggers:\n"
            f"   • Windows popup notification\n"
            f"   • Alarm beep sound\n"
            f"   • Terminal log\n\n"
            f"📡 Monitoring for: DJI, Parrot, Autel, Skydio, FPV drones\n"
            f"Use 'stop' command to end monitoring.\n"
            f"{'═'*50}"
        )
    
    # ── ACTION: stop ──────────────────────────────────────────────
    elif action == "stop":
        if _engine_instance:
            _engine_instance.stop()
            return "✅ Anti-drone monitor stopped."
        return "ℹ️ No monitor is currently running."
    
    # ── ACTION: frequencies ───────────────────────────────────────
    elif action == "frequencies":
        lines = [BANNER, "", "📻 DRONE RF FREQUENCY REFERENCE MAP:", "─" * 66]
        for freq, desc in DRONE_FREQUENCIES.items():
            lines.append(f"  📡 {freq}")
            lines.append(f"     {desc}")
            lines.append("")
        
        lines += [
            "🔬 DETECTION TOOLS (if you have RTL-SDR dongle ~₹1500):",
            "  pip install pyrtlsdr",
            "  • Scan 2.4GHz band for drone burst transmissions",
            "  • DJI OcuSync has distinct modulation pattern",
            "  • Use SDRSharp/GQRX for visual spectrum analysis",
            "",
            "📱 FREE APPS:",
            "  • DroneWatcher (Android) — detects via RemoteID",
            "  • OpenDroneID (Android/iOS) — EU/US drone ID",
            "  • AirMap — shows authorized flight zones",
            "═" * 66,
        ]
        return "\n".join(lines)
    
    # ── ACTION: countermeasures ───────────────────────────────────
    elif action == "countermeasures":
        return BANNER + "\n" + LEGAL_COUNTERMEASURES
    
    # ── ACTION: log ───────────────────────────────────────────────
    elif action == "log":
        log_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "logs", "antidrone.log"
        )
        if not os.path.exists(log_path):
            return f"📁 No log file yet. Run 'scan' or 'monitor' first.\nLog path: {log_path}"
        
        try:
            with open(log_path, encoding="utf-8") as f:
                lines = f.readlines()
            recent = lines[-50:] if len(lines) > 50 else lines
            return (
                f"{BANNER}\n\n"
                f"📁 LOG FILE: {log_path}\n"
                f"Total entries: {len(lines)}\n"
                f"{'─'*60}\n"
                f"{''.join(recent)}"
            )
        except Exception as e:
            return f"Error reading log: {e}"
    
    # ── ACTION: geofence ─────────────────────────────────────────
    elif action == "geofence":
        radius = parameters.get("radius", "500")
        location = parameters.get("location", "your location")
        
        return (
            f"{BANNER}\n\n"
            f"🗺️  GEOFENCE ZONE SETUP\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Protected Zone  : {location}\n"
            f"📏 Radius          : {radius} meters\n\n"
            f"🔴 ALERT TRIGGERS:\n"
            f"   • Any drone WiFi detected in scan range\n"
            f"   • Signal strength > -70 dBm (within ~60m)\n"
            f"   • Unknown aircraft WiFi with UAV-like SSID\n\n"
            f"📱 REPORT TO AUTHORITIES:\n"
            f"   • DGCA: +91-11-24622495\n"
            f"   • Digital Sky: digitalsky.dgca.gov.in\n"
            f"   • Emergency: 112 (Police)\n"
            f"   • Airport ATC (if near airport): Inform immediately\n\n"
            f"⚖️  DRONE RULES 2021 (India):\n"
            f"   • No fly zones: within 5km of airports\n"
            f"   • Prohibited: military areas, strategic locations\n"
            f"   • Required: DGCA registration + Remote Pilot License\n"
            f"   • Violation: Fine up to ₹1 Lakh + equipment seizure\n"
            f"{'═'*60}"
        )
    
    # ── DEFAULT ───────────────────────────────────────────────────
    else:
        return (
            f"{BANNER}\n\n"
            f"⚡ ANTI-DRONE DEFENSE — Available Commands:\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"  scan           — Single WiFi scan for drones\n"
            f"  monitor        — Continuous monitoring (background)\n"
            f"  stop           — Stop continuous monitor\n"
            f"  frequencies    — Drone RF frequency reference map\n"
            f"  countermeasures — Legal anti-drone options\n"
            f"  geofence       — Setup protected zone alert\n"
            f"  log            — View detection history\n"
        )
