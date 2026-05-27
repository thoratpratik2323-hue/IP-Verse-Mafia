"""
core/path_config.py — IP Prime centralised path configuration.

All hard-coded filesystem paths used across the project are defined here.
Values are resolved in this priority order:
  1. Environment variable (if set)
  2. config/paths.json entry (if file exists)
  3. Sensible default relative to this file or user home

Import this module instead of hard-coding paths in action modules.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def _get_base_dir() -> Path:
    """Return the project root directory, works both frozen (PyInstaller) and dev mode."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    # core/path_config.py → project root is one level up
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Project root & core dirs
# ---------------------------------------------------------------------------
BASE_DIR: Path = _get_base_dir()
CONFIG_DIR: Path = BASE_DIR / "config"
CORE_DIR: Path = BASE_DIR / "core"
MEMORY_DIR: Path = BASE_DIR / "memory"
ACTIONS_DIR: Path = BASE_DIR / "actions"
LOGS_DIR: Path = BASE_DIR / "logs"
ASSETS_DIR: Path = BASE_DIR / "assets"
DOCS_DIR: Path = BASE_DIR / "docs"


# ---------------------------------------------------------------------------
# Config files
# ---------------------------------------------------------------------------
API_CONFIG_PATH: Path = CONFIG_DIR / "api_keys.json"
PROMPT_PATH: Path = CORE_DIR / "prompt.txt"
PERSONALITY_PATH: Path = CONFIG_DIR / "personality.json"
PATHS_CONFIG_PATH: Path = CONFIG_DIR / "paths.json"


# ---------------------------------------------------------------------------
# Helper: load optional paths.json overrides
# ---------------------------------------------------------------------------
def _load_paths_config() -> dict:
    """Load optional paths.json for user-defined path overrides."""
    if PATHS_CONFIG_PATH.exists():
        try:
            return json.loads(PATHS_CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


_paths_cfg: dict = _load_paths_config()


def _resolve(env_var: str, cfg_key: str, default: Path) -> Path:
    """
    Resolve a path with priority: env var > paths.json > default.

    Args:
        env_var: Name of the environment variable to check first.
        cfg_key: Key in config/paths.json to check second.
        default: Fallback Path if neither env var nor config key is set.

    Returns:
        Resolved Path object.
    """
    from_env = os.environ.get(env_var)
    if from_env:
        return Path(from_env)
    from_cfg = _paths_cfg.get(cfg_key)
    if from_cfg:
        return Path(from_cfg)
    return default


# ---------------------------------------------------------------------------
# User workspace paths (replaces hard-coded C:\Users\thora\Downloads\...)
# ---------------------------------------------------------------------------

# IP Given workspace — where generated code, projects, screenshots, etc. land
IP_GIVEN_DIR: Path = _resolve(
    "IP_GIVEN_DIR",
    "ip_given_dir",
    Path.home() / "Downloads" / "IP Given",
)
IP_GIVEN_CODE_DIR: Path = _resolve(
    "IP_GIVEN_CODE_DIR",
    "ip_given_code_dir",
    IP_GIVEN_DIR / "code",
)
IP_GIVEN_PROJECTS_DIR: Path = _resolve(
    "IP_GIVEN_PROJECTS_DIR",
    "ip_given_projects_dir",
    IP_GIVEN_DIR / "projects",
)
IP_GIVEN_SCREENSHOTS_DIR: Path = _resolve(
    "IP_GIVEN_SCREENSHOTS_DIR",
    "ip_given_screenshots_dir",
    IP_GIVEN_DIR / "screenshots",
)
IP_GIVEN_DOCS_DIR: Path = _resolve(
    "IP_GIVEN_DOCS_DIR",
    "ip_given_docs_dir",
    IP_GIVEN_DIR / "docs",
)

# IP Prime user data — tasks, mood history, briefing logs, etc.
IPPRIME_DATA_DIR: Path = _resolve(
    "IPPRIME_DATA_DIR",
    "ipprime_data_dir",
    Path.home() / ".ipprime",
)
TASKS_FILE: Path = IPPRIME_DATA_DIR / "tasks.json"
MOOD_HISTORY_FILE: Path = IPPRIME_DATA_DIR / "mood_history.json"
BRIEFING_LOG_FILE: Path = IPPRIME_DATA_DIR / "briefing_log.txt"
CODE_REVIEWS_LOG: Path = IPPRIME_DATA_DIR / "code_reviews.log"


# ---------------------------------------------------------------------------
# Memory paths (mirrors memory_manager.py constants for unified access)
# ---------------------------------------------------------------------------
LONG_TERM_MEMORY_DIR: Path = MEMORY_DIR / "long_term"
SESSION_LOG_PATH: Path = MEMORY_DIR / "session_log.json"
LAST_SESSION_SUMMARY_PATH: Path = MEMORY_DIR / "last_session_summary.json"
KNOWLEDGE_BASE_PATH: Path = MEMORY_DIR / "knowledge_base.json"


# ---------------------------------------------------------------------------
# Helper: ensure a directory exists (call when writing)
# ---------------------------------------------------------------------------
def ensure_dir(path: Path) -> Path:
    """
    Create directory (and parents) if it does not exist.

    Args:
        path: Directory path to create.

    Returns:
        The same path, so it can be used inline.
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
