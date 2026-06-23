import os
import time
import threading
import platform
import psutil

# Global state
usb_lockdown_active = False
known_drives = set()
_monitor_thread = None

def get_drives():
    """Retrieve set of removable/FAT32 drive letters."""
    drives = set()
    try:
        for p in psutil.disk_partitions():
            # Removable drives are typically external USBs
            if 'removable' in p.opts.lower() or p.fstype == 'FAT32':
                drives.add(p.device)
    except Exception:
        pass
    return drives

def usb_monitor_loop():
    """Background loop that monitors for unauthorized USB plug-ins during lockdown."""
    global known_drives, usb_lockdown_active
    while True:
        time.sleep(2)
        if usb_lockdown_active:
            current_drives = get_drives()
            new_drives = current_drives - known_drives
            if new_drives:
                print(f"[SECURITY] Unauthorized USB detected: {new_drives}")
                # Play alert sound or try to synthesize speech
                try:
                    from actions.edge_tts_helper import generate_speech
                    # Place warning speech file in static directory
                    static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
                    os.makedirs(static_dir, exist_ok=True)
                    filepath = os.path.join(static_dir, "unauthorized_usb_warning.mp3")
                    generate_speech("Unauthorized USB Device detected. Access Denied.", "en-GB-RyanNeural", filepath)
                except Exception as e:
                    print(f"[USB MONITOR SPEECH ERR] {e}")
            known_drives = current_drives

def start_usb_monitor():
    """Ensure the background USB monitoring thread is running."""
    global _monitor_thread
    if _monitor_thread is None or not _monitor_thread.is_alive():
        _monitor_thread = threading.Thread(target=usb_monitor_loop, daemon=True)
        _monitor_thread.start()
        print("[SECURITY] USB Monitor thread started.")

def toggle_usb(enabled: bool):
    """Toggle the active status of USB lockdown security."""
    global usb_lockdown_active, known_drives
    usb_lockdown_active = enabled
    if usb_lockdown_active:
        known_drives = get_drives()
        start_usb_monitor()
    return {"status": "ok", "active": usb_lockdown_active}
