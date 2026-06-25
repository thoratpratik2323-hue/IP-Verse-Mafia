# actions/google_drive_tool.py
# Google Drive integration — list, upload, download files using Google API.
# Uses google-api-python-client or falls back to Drive REST API with an access token.

import json
import os
import sys
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


def _get_credentials():
    cfg = _load_config()
    creds = cfg.get("google_drive_credentials", {})
    return creds


def _no_creds_msg() -> str:
    return (
        "Google Drive credentials are not configured, sir. "
        "Please add a 'google_drive_credentials' block to config/api_keys.json with "
        "'service_account_file' pointing to your Google service account JSON file, "
        "or supply an 'access_token' for personal Drive access. "
        "Visit https://console.cloud.google.com/ to create credentials."
    )


# ─── Auth Helpers ─────────────────────────────────────────────────────────────

def _get_service_headers(creds: dict) -> dict | None:
    """Return request headers using service account or personal access token."""
    # 1) Try service account via google-auth
    sa_file = creds.get("service_account_file", "")
    if sa_file:
        sa_path = Path(sa_file).expanduser()
        if not sa_path.is_absolute():
            sa_path = BASE_DIR / sa_file
        if sa_path.exists():
            try:
                from google.oauth2 import service_account
                import google.auth.transport.requests as grequests
                scopes = ["https://www.googleapis.com/auth/drive"]
                credentials = service_account.Credentials.from_service_account_file(
                    str(sa_path), scopes=scopes
                )
                credentials.refresh(grequests.Request())
                return {"Authorization": f"Bearer {credentials.token}"}
            except ImportError:
                pass  # google-auth not installed, fall through
            except Exception as e:
                return None

    # 2) Try plain access token (personal OAuth token)
    access_token = creds.get("access_token", "")
    if access_token:
        return {"Authorization": f"Bearer {access_token}"}

    return None


# ─── Actions ──────────────────────────────────────────────────────────────────

def _list_files(headers: dict, folder_id: str = None, limit: int = 15) -> str:
    """List recent files in Google Drive (optionally filtered by folder)."""
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "pageSize": limit,
        "fields": "files(id, name, mimeType, modifiedTime, size)",
        "orderBy": "modifiedTime desc"
    }
    if folder_id:
        params["q"] = f"'{folder_id}' in parents and trashed=false"
    else:
        params["q"] = "trashed=false"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        files = resp.json().get("files", [])
        if not files:
            return "No files found in your Google Drive, sir."
        lines = ["Here are your recent Google Drive files, sir:"]
        for f in files:
            name = f.get("name", "Unknown")
            mime = f.get("mimeType", "").split(".")[-1].replace("application/", "")
            modified = f.get("modifiedTime", "")[:10]
            size_bytes = f.get("size", "")
            size_str = f" ({int(size_bytes) // 1024} KB)" if size_bytes else ""
            lines.append(f"  • {name}{size_str} [{mime}] — modified {modified}")
        return "\n".join(lines)
    except requests.HTTPError as e:
        return f"Google Drive list error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Failed to list Google Drive files: {e}"


def _upload_file(headers: dict, file_path: str, folder_id: str = None) -> str:
    """Upload a file to Google Drive using multipart upload."""
    path = Path(file_path).expanduser()
    if not path.exists():
        # Try relative to Desktop
        desktop_path = Path.home() / "Desktop" / file_path
        if desktop_path.exists():
            path = desktop_path
        else:
            return f"File not found: {file_path}, sir."

    file_name = path.name
    mime_type = _guess_mime(path.suffix.lower())

    metadata = {"name": file_name}
    if folder_id:
        metadata["parents"] = [folder_id]

    try:
        with open(path, "rb") as fh:
            file_data = fh.read()

        # Multipart upload
        boundary = "saturday_upload_boundary"
        body = (
            f"--{boundary}\r\n"
            f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
            f"{json.dumps(metadata)}\r\n"
            f"--{boundary}\r\n"
            f"Content-Type: {mime_type}\r\n\r\n"
        ).encode() + file_data + f"\r\n--{boundary}--".encode()

        upload_headers = dict(headers)
        upload_headers["Content-Type"] = f"multipart/related; boundary={boundary}"

        resp = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers=upload_headers,
            data=body,
            timeout=60
        )
        resp.raise_for_status()
        file_id = resp.json().get("id", "")
        return f"File '{file_name}' uploaded successfully to Google Drive, sir! (ID: {file_id})"
    except requests.HTTPError as e:
        return f"Google Drive upload error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Failed to upload to Google Drive: {e}"


def _download_file(headers: dict, file_id: str, save_name: str = "") -> str:
    """Download a file from Google Drive by its file ID."""
    # First get metadata to find the file name
    meta_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    params = {"fields": "name, mimeType"}
    try:
        meta_resp = requests.get(meta_url, headers=headers, params=params, timeout=10)
        meta_resp.raise_for_status()
        meta = meta_resp.json()
        name = save_name or meta.get("name", f"drive_file_{file_id}")

        # Check if it's a Google Doc/Sheet (needs export)
        mime = meta.get("mimeType", "")
        if "google-apps" in mime:
            export_mime = "application/pdf"
            dl_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
            dl_params = {"mimeType": export_mime}
            if not name.endswith(".pdf"):
                name += ".pdf"
        else:
            dl_url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
            dl_params = {"alt": "media"}

        dl_resp = requests.get(dl_url, headers=headers, params=dl_params, timeout=60)
        dl_resp.raise_for_status()

        save_path = Path.home() / "Downloads" / "sat output" / name
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(dl_resp.content)
        return f"File '{name}' downloaded successfully to {save_path}, sir!"
    except requests.HTTPError as e:
        return f"Google Drive download error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Failed to download from Google Drive: {e}"


def _search_drive(headers: dict, query: str, limit: int = 10) -> str:
    """Search Google Drive files by name."""
    url = "https://www.googleapis.com/drive/v3/files"
    params = {
        "pageSize": limit,
        "q": f"name contains '{query}' and trashed=false",
        "fields": "files(id, name, mimeType, modifiedTime)",
        "orderBy": "modifiedTime desc"
    }
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        files = resp.json().get("files", [])
        if not files:
            return f"No files matching '{query}' found in Google Drive, sir."
        lines = [f"Drive search results for '{query}', sir:"]
        for f in files:
            name = f.get("name", "Unknown")
            file_id = f.get("id", "")
            modified = f.get("modifiedTime", "")[:10]
            lines.append(f"  • {name} (ID: {file_id}) — {modified}")
        return "\n".join(lines)
    except requests.HTTPError as e:
        return f"Google Drive search error: {e.response.status_code} — {e.response.text[:200]}"
    except Exception as e:
        return f"Failed to search Google Drive: {e}"


def _guess_mime(ext: str) -> str:
    mapping = {
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/plain",
        ".py": "text/x-python",
        ".json": "application/json",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".mp4": "video/mp4",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".zip": "application/zip",
    }
    return mapping.get(ext, "application/octet-stream")


# ─── Main Dispatcher ──────────────────────────────────────────────────────────

def google_drive_tool(parameters: dict, player=None, speak=None) -> str:
    """
    Google Drive file management integration tool.
    Supported actions: list_files | upload_file | download_file | search
    """
    creds = _get_credentials()
    if not creds:
        msg = _no_creds_msg()
        if speak:
            speak(msg[:200])
        return msg

    headers = _get_service_headers(creds)
    if not headers:
        msg = _no_creds_msg()
        if speak:
            speak(msg[:200])
        return msg

    action = parameters.get("action", "list_files").lower().strip()
    file_path = parameters.get("file_path", "").strip()
    file_id = parameters.get("file_id", "").strip()
    folder_id = parameters.get("folder_id", "").strip() or None
    save_name = parameters.get("save_name", "").strip()
    query = parameters.get("query", "").strip()
    limit = int(parameters.get("limit", 15))

    if action == "upload_file":
        if not file_path:
            result = "Please specify a 'file_path' parameter to upload, sir."
        else:
            result = _upload_file(headers, file_path, folder_id)

    elif action == "download_file":
        if not file_id:
            result = "Please specify a 'file_id' parameter to download, sir."
        else:
            result = _download_file(headers, file_id, save_name)

    elif action == "search":
        if not query:
            result = "Please specify a 'query' parameter to search Drive, sir."
        else:
            result = _search_drive(headers, query, limit)

    else:  # default: list_files
        result = _list_files(headers, folder_id, limit)

    if player:
        player.write_log(f"SATURDAY (Drive): {result[:200]}")
    return result
