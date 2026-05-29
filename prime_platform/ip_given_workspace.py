"""Default workspace: all saves, code, and projects go under CODING PROJECTS."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from prime_platform.config import load_prime_config, save_prime_config

DEFAULT_ROOT = Path(r"C:\Users\thora\.gemini\antigravity\scratch\IP Prime\CODING PROJECTS")

SUBDIRS = {
    "code": "code",
    "projects": "projects",
    "downloads": "downloads",
    "exports": "exports",
    "screenshots": "screenshots",
    "browser_profiles": "browser_profiles",
    "archives": "archives",
}


def get_ip_given_root() -> Path:
    cfg = load_prime_config()
    raw = (cfg.get("workspace") or {}).get("root", "")
    root = Path(raw).expanduser() if raw else DEFAULT_ROOT
    return root


def ensure_workspace() -> Path:
    root = get_ip_given_root()
    root.mkdir(parents=True, exist_ok=True)
    for sub in SUBDIRS.values():
        (root / sub).mkdir(parents=True, exist_ok=True)
    return root


def subdir(name: str) -> Path:
    ensure_workspace()
    key = name.lower().strip()
    folder = SUBDIRS.get(key, key)
    path = get_ip_given_root() / folder
    path.mkdir(parents=True, exist_ok=True)
    return path


def code_dir() -> Path:
    return subdir("code")


def projects_dir() -> Path:
    return subdir("projects")


def downloads_dir() -> Path:
    return subdir("downloads")


def exports_dir() -> Path:
    return subdir("exports")


def browser_profiles_dir() -> Path:
    return subdir("browser_profiles")


def resolve_save_path(
    output_path: str = "",
    *,
    category: str = "code",
    default_name: str = "",
    extension: str = "",
) -> Path:
    """
    Resolve any save path into CODING PROJECTS workspace.
    Absolute paths outside CODING PROJECTS are still allowed if under user home.
    """
    ensure_workspace()
    base = subdir(category)

    if output_path:
        p = Path(output_path).expanduser()
        if p.is_absolute():
            if not p.parent.exists():
                p.parent.mkdir(parents=True, exist_ok=True)
            return p
        return base / p

    if default_name:
        name = default_name
    elif extension:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = extension if extension.startswith(".") else f".{extension}"
        name = f"ipprime_{stamp}{ext}"
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"ipprime_{stamp}.txt"

    return base / name


def sanitize_project_name(name: str) -> str:
    name = (name or "project").strip()
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = re.sub(r"\s+", "_", name)
    return name[:80] or "project"


def new_project_dir(project_name: str) -> Path:
    safe = sanitize_project_name(project_name)
    stamp = datetime.now().strftime("%Y%m%d")
    path = projects_dir() / f"{safe}_{stamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def workspace_summary() -> str:
    root = ensure_workspace()
    lines = [f"CODING PROJECTS workspace: {root}"]
    for key, folder in SUBDIRS.items():
        p = root / folder
        n = sum(1 for _ in p.rglob("*") if _.is_file()) if p.exists() else 0
        lines.append(f"  • {folder}/ — {n} files")
    return "\n".join(lines)


def persist_root_to_config() -> None:
    """Write default workspace into prime_features.json if missing."""
    cfg = load_prime_config()
    ws = cfg.setdefault("workspace", {})
    if not ws.get("root"):
        ws["root"] = str(DEFAULT_ROOT)
        ws["auto_save_all"] = True
        save_prime_config(cfg)
