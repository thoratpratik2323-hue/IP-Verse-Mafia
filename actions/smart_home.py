import json
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"

def _get_ha_config() -> tuple[str | None, str | None]:
    try:
        if API_KEYS_PATH.exists():
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg.get("home_assistant_url"), cfg.get("home_assistant_token")
    except Exception:
        pass
    return None, None

def execute_smart_home_command(action: str, device_name: str, domain: str = "light") -> str:
    """Executes a service action (turn_on, turn_off, toggle) for a Home Assistant device, or runs a simulation if offline."""
    url, token = _get_ha_config()
    
    # Process action name cleanly
    act = action.lower().strip()
    if act not in ["turn_on", "turn_off", "toggle", "set_value"]:
        act = "turn_on" if "on" in act else "turn_off"
        
    device = device_name.lower().strip().replace(" ", "_")
    entity_id = f"{domain}.{device}"
    
    # SIMULATION LAYER: If credentials are not set, run high-fidelity simulation mode
    if not url or not token:
        # Build friendly name
        friendly_device = device_name.title()
        sim_state = "ON 🟢" if act == "turn_on" or (act == "toggle" and "off" in friendly_device) else "OFF 🔴"
        
        return (
            f"### 🏠 Smart Home (Simulation Mode)\n"
            f"Device: **{friendly_device}** (`{entity_id}`)\n"
            f"Requested Action: `{act.upper()}`\n"
            f"Simulated New State: **{sim_state}**\n\n"
            f"> [!TIP]\n"
            f"> To connect your real physical devices, configure your `home_assistant_url` and `home_assistant_token` in Settings."
        )
        
    # PHYSICAL ACCESS LAYER: Execute real REST calls to Home Assistant
    try:
        url_clean = url.rstrip("/")
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Build HA service endpoint
        endpoint = f"{url_clean}/api/services/{domain}/{act}"
        payload = {"entity_id": entity_id}
        
        res = requests.post(endpoint, headers=headers, json=payload, timeout=5)
        if res.status_code == 200:
            return (
                f"### 🏠 Smart Home Control\n"
                f"Successfully called Home Assistant service `{act}` on **{entity_id}**.\n"
                f"Response Status: `{res.status_code} OK`"
            )
        else:
            return (
                f"### 🏠 Smart Home Error\n"
                f"Failed to control device **{device_name}** via Home Assistant.\n"
                f"- **Endpoint**: `{endpoint}`\n"
                f"- **HTTP Status**: `{res.status_code}`\n"
                f"- **Detail**: `{res.text}`"
            )
            
    except Exception as e:
        return f"Error connecting to your Home Assistant endpoint: {e}"
