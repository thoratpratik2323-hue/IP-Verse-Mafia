import psutil

def panic_wipe():
    """Instantly terminate browser and communication processes for privacy lockdown."""
    targets = ['chrome', 'firefox', 'msedge', 'brave', 'whatsapp', 'discord', 'telegram', 'code']
    killed = 0
    for p in psutil.process_iter(['name']):
        try:
            name = p.info['name']
            if name and any(t in name.lower() for t in targets):
                p.kill()
                killed += 1
        except Exception:
            pass
    return {
        "status": "ok",
        "killed": killed,
        "reply": f"Panic Wipe activated, Sir. Forcefully terminated {killed} processes."
    }
