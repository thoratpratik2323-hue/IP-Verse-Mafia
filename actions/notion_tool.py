# actions/notion_tool.py
# Notion API integration — list, create, search pages and database records.

import json
import requests
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "api_keys.json"

# ─── Config Loader ────────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get_credentials() -> tuple[str, str]:
    cfg = _load_config()
    token = cfg.get("notion_token", "")
    db_id = cfg.get("notion_database_id", "")
    return token, db_id

def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

def _no_creds_msg() -> str:
    return (
        "Notion credentials are not configured, sir. "
        "Please add 'notion_token' and 'notion_database_id' to config/api_keys.json. "
        "You can get a Notion integration token at https://www.notion.so/my-integrations."
    )

# ─── Actions ──────────────────────────────────────────────────────────────────

def _list_pages(token: str, db_id: str, limit: int = 10) -> str:
    """Query a Notion database and return recent page titles."""
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    payload = {"page_size": limit}
    try:
        resp = requests.post(url, headers=_headers(token), json=payload, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        if not results:
            return "Your Notion database appears to be empty, sir."
        lines = ["Here are your recent Notion entries, sir:"]
        for page in results:
            props = page.get("properties", {})
            # Try to find a Name / Title property
            title_text = "(Untitled)"
            for prop_val in props.values():
                if prop_val.get("type") == "title":
                    title_parts = prop_val.get("title", [])
                    if title_parts:
                        title_text = title_parts[0].get("plain_text", "(Untitled)")
                    break
            created = page.get("created_time", "")[:10]
            lines.append(f"  • {title_text} (created: {created})")
        return "\n".join(lines)
    except requests.HTTPError as e:
        return f"Notion API error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Failed to fetch Notion pages: {e}"


def _create_page(token: str, db_id: str, title: str, content: str = "") -> str:
    """Create a new Notion page inside the configured database."""
    url = "https://api.notion.com/v1/pages"
    payload = {
        "parent": {"database_id": db_id},
        "properties": {
            "Name": {
                "title": [{"text": {"content": title}}]
            }
        },
        "children": []
    }
    # Add content block if provided
    if content:
        payload["children"].append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": content[:2000]}}]
            }
        })
    try:
        resp = requests.post(url, headers=_headers(token), json=payload, timeout=10)
        resp.raise_for_status()
        page_url = resp.json().get("url", "")
        return f"Notion page '{title}' created successfully, sir. URL: {page_url}"
    except requests.HTTPError as e:
        return f"Notion create error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Failed to create Notion page: {e}"


def _search_pages(token: str, query: str, limit: int = 5) -> str:
    """Search across all Notion pages accessible to this integration."""
    url = "https://api.notion.com/v1/search"
    payload = {"query": query, "page_size": limit}
    try:
        resp = requests.post(url, headers=_headers(token), json=payload, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return f"No Notion pages found matching '{query}', sir."
        lines = [f"Search results for '{query}' in Notion, sir:"]
        for item in results:
            title_text = "(Untitled)"
            if item.get("object") == "page":
                props = item.get("properties", {})
                for pv in props.values():
                    if pv.get("type") == "title":
                        parts = pv.get("title", [])
                        if parts:
                            title_text = parts[0].get("plain_text", "(Untitled)")
                        break
            page_url = item.get("url", "")
            lines.append(f"  • {title_text} — {page_url}")
        return "\n".join(lines)
    except requests.HTTPError as e:
        return f"Notion search error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Failed to search Notion: {e}"


# ─── Main Dispatcher ──────────────────────────────────────────────────────────

def notion_tool(parameters: dict, player=None, speak=None) -> str:
    """
    Notion workspace integration tool.
    Supported actions: list_pages | create_page | search
    """
    token, db_id = _get_credentials()
    if not token:
        msg = _no_creds_msg()
        if speak:
            speak(msg)
        return msg

    action = parameters.get("action", "list_pages").lower().strip()
    title = parameters.get("title", "").strip()
    content = parameters.get("content", "").strip()
    query = parameters.get("query", "").strip()
    limit = int(parameters.get("limit", 10))

    if action == "create_page":
        if not title:
            title = f"Saturday Note — {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        result = _create_page(token, db_id, title, content)
    elif action == "search":
        if not query:
            result = "Please specify a 'query' parameter to search Notion, sir."
        else:
            result = _search_pages(token, query, limit)
    else:  # default: list_pages
        if not db_id:
            result = _no_creds_msg()
        else:
            result = _list_pages(token, db_id, limit)

    if player:
        player.write_log(f"SATURDAY (Notion): {result[:200]}")
    return result
