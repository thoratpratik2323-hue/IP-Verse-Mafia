"""
n8n_dispatcher.py — Orchestrates background n8n automation flows.

This is a standard action module for the IP Prime personal assistant suite.
"""

import json
import requests
from pathlib import Path

# Setup database path
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "n8n_webhooks.json"

def _load_mappings() -> dict:
    """Loads n8n webhook friendly mappings from config."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        default_map = {
            "invoice": "https://n8n.yourdomain.com/webhook/invoice-trigger",
            "backup": "https://n8n.yourdomain.com/webhook/backup-trigger"
        }
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_map, f, indent=4)
        return default_map
        
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def trigger_n8n_webhook(webhook_name: str, payload: dict = None) -> str:
    """Triggers an external self-hosted n8n workflow webhook."""
    name_clean = webhook_name.lower().strip()
    mappings = _load_mappings()
    
    if name_clean not in mappings:
        return (
            f"Error: Mapped webhook name '{webhook_name}' was not found in `config/n8n_webhooks.json`.\n"
            f"Available mappings: {list(mappings.keys())}"
        )
        
    webhook_url = mappings[name_clean]
    if not payload:
        payload = {}
        
    try:
        # Standard HTTP POST request to the n8n webhook trigger endpoint
        res = requests.post(webhook_url, json=payload, timeout=10.0)
        
        if res.status_code in [200, 201]:
            try:
                res_text = res.json()
            except Exception:
                res_text = res.text
                
            return (
                f"### 🔌 n8n Workflow Triggered successfully!\n"
                f"- **Webhook Name**: `{webhook_name}`\n"
                f"- **Target URL**: `{webhook_url}`\n"
                f"- **Status Code**: `{res.status_code}`\n\n"
                f"#### Trigger response payload:\n"
                f"```json\n{json.dumps(res_text, indent=2) if isinstance(res_text, dict) else str(res_text)}\n```"
            )
        else:
            return (
                f"Error: n8n server returned non-success response code `{res.status_code}`.\n"
                f"**URL**: `{webhook_url}`\n"
                f"**Details**: \n```\n{res.text}\n```"
            )
            
    except Exception as e:
        return f"Error: Failed to reach n8n webhook server at '{webhook_url}': {e}"
