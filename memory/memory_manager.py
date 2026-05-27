import json
from datetime import datetime
from threading import Lock
from pathlib import Path
import sys


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR         = get_base_dir()
OLD_MEMORY_PATH  = BASE_DIR / "memory" / "long_term.json"
LONG_TERM_DIR    = BASE_DIR / "memory" / "long_term"
_lock            = Lock()
MAX_VALUE_LENGTH = 1000
MEMORY_MAX_CHARS = 100000

def _empty_memory() -> dict:
    return {
        "identity":      {},
        "preferences":   {},
        "projects":      {},
        "relationships": {},
        "wishes":        {},
        "notes":         {},
    }

def load_memory() -> dict:
    LONG_TERM_DIR.mkdir(parents=True, exist_ok=True)
    memory = _empty_memory()
    
    # Check if we need to migrate from the old long_term.json
    if OLD_MEMORY_PATH.exists() and not any(LONG_TERM_DIR.glob("*.json")):
        with _lock:
            try:
                print("[Memory] [Migrating] Migrating old long_term.json to hierarchical structure...")
                data = json.loads(OLD_MEMORY_PATH.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    for key in memory:
                        if key in data and isinstance(data[key], dict):
                            memory[key] = data[key]
                    # Write to new hierarchical files immediately
                    for key, val in memory.items():
                        file_path = LONG_TERM_DIR / f"{key}.json"
                        file_path.write_text(json.dumps(val, indent=2, ensure_ascii=False), encoding="utf-8")
                    # Backup old memory path by renaming it
                    backup_path = OLD_MEMORY_PATH.with_suffix(".json.bak")
                    OLD_MEMORY_PATH.rename(backup_path)
                    print(f"[Memory] [OK] Migration complete. Old file backed up to {backup_path.name}")
                    return memory
            except Exception as e:
                print(f"[Memory] [Error] Migration failed: {e}")
                
    # Normal load: read each file in memory/long_term/
    with _lock:
        for key in memory:
            file_path = LONG_TERM_DIR / f"{key}.json"
            if file_path.exists():
                try:
                    data = json.loads(file_path.read_text(encoding="utf-8"))
                    if isinstance(data, dict):
                        memory[key] = data
                except Exception as e:
                    print(f"[Memory] [Error] Error loading {key}.json: {e}")
    return memory

def _all_entries(memory: dict) -> list[tuple]:
    entries = []
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            if isinstance(entry, dict) and "value" in entry:
                entries.append((cat, key, entry))
    return entries

def _trim_to_limit(memory: dict) -> dict:
    if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
        return memory
    entries = _all_entries(memory)
    entries.sort(key=lambda t: t[2].get("updated", "0000-00-00"))
    for cat, key, _ in entries:
        if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
            break
        del memory[cat][key]
        print(f"[Memory] [Trimmed] Trimmed {cat}/{key}")
    return memory

def save_memory(memory: dict) -> None:
    if not isinstance(memory, dict):
        return
    memory = _trim_to_limit(memory)
    LONG_TERM_DIR.mkdir(parents=True, exist_ok=True)
    with _lock:
        try:
            for key, val in memory.items():
                if key in _empty_memory():
                    file_path = LONG_TERM_DIR / f"{key}.json"
                    file_path.write_text(
                        json.dumps(val, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
        except Exception as e:
            print(f"[Memory] [Error] Error saving memory: {e}")

def _truncate_value(val: str) -> str:
    if isinstance(val, str) and len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH].rstrip() + "…"
    return val

def _recursive_update(target: dict, updates: dict) -> bool:
    changed = False
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value):
                changed = True
        else:
            new_val  = _truncate_value(str(value["value"] if isinstance(value, dict) else value))
            entry    = {"value": new_val, "updated": datetime.now().strftime("%Y-%m-%d")}
            existing = target.get(key, {})
            if not isinstance(existing, dict) or existing.get("value") != new_val:
                target[key] = entry
                changed = True
    return changed

def update_memory(memory_update: dict) -> dict:
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory()
    memory = load_memory()
    if _recursive_update(memory, memory_update):
        save_memory(memory)
        print(f"[Memory] [Saved] Saved: {list(memory_update.keys())}")
    return memory

def format_memory_for_prompt(memory: dict | None) -> str:
    if not memory:
        return ""

    lines = []

    identity  = memory.get("identity", {})
    id_fields = ["name", "age", "birthday", "city", "job", "language", "school", "nationality"]
    for field in id_fields:
        entry = identity.get(field)
        if entry:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"{field.title()}: {val}")
    for key, entry in identity.items():
        if key in id_fields:
            continue
        val = entry.get("value") if isinstance(entry, dict) else entry
        if val:
            lines.append(f"{key.replace('_', ' ').title()}: {val}")

    prefs = memory.get("preferences", {})
    if prefs:
        lines.append("")
        lines.append("Preferences:")
        for key, entry in list(prefs.items())[:50]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    projects = memory.get("projects", {})
    if projects:
        lines.append("")
        lines.append("Active Projects / Goals:")
        for key, entry in list(projects.items())[:30]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    rels = memory.get("relationships", {})
    if rels:
        lines.append("")
        lines.append("People in their life:")
        for key, entry in list(rels.items())[:30]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    wishes = memory.get("wishes", {})
    if wishes:
        lines.append("")
        lines.append("Wishes / Plans / Wants:")
        for key, entry in list(wishes.items())[:30]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key.replace('_', ' ').title()}: {val}")

    notes = memory.get("notes", {})
    if notes:
        lines.append("")
        lines.append("Other notes:")
        for key, entry in list(notes.items())[:30]:
            val = entry.get("value") if isinstance(entry, dict) else entry
            if val:
                lines.append(f"  - {key}: {val}")

    if not lines:
        return ""

    header = "[WHAT YOU KNOW ABOUT THIS PERSON — use naturally, never recite like a list]\n"
    result = header + "\n".join(lines)
    if len(result) > 90000:
        result = result[:89997] + "…"

    return result + "\n"

def remember(key: str, value: str, category: str = "notes") -> str:
    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"
    update_memory({category: {key: {"value": value}}})
    return f"Remembered: {category}/{key} = {value}"


def forget(key: str, category: str = "notes") -> str:
    memory = load_memory()
    cat    = memory.get(category, {})
    if key in cat:
        del cat[key]
        memory[category] = cat
        save_memory(memory)
        return f"Forgotten: {category}/{key}"
    return f"Not found: {category}/{key}"


forget_memory = forget

SESSION_LOG_PATH = BASE_DIR / "memory" / "session_log.json"
LAST_SESSION_SUMMARY_PATH = BASE_DIR / "memory" / "last_session_summary.json"
MAX_SESSION_TURNS = 40
SHUTDOWN_HIGHLIGHT_TURNS = 8


def load_session_log() -> dict:
    default = {"last_updated": "", "turns": [], "summary": ""}
    if not SESSION_LOG_PATH.exists():
        return default
    with _lock:
        try:
            data = json.loads(SESSION_LOG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {**default, **data}
        except Exception as e:
            print(f"[Memory] [Error] Error loading session log: {e}")
    return default


def append_session_turn(user: str = "", assistant: str = "") -> None:
    user = (user or "").strip()
    assistant = (assistant or "").strip()
    if not user and not assistant:
        return

    log = load_session_log()
    turns = log.get("turns", [])
    turns.append({
        "user": user[:500],
        "assistant": assistant[:800],
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    log["turns"] = turns[-MAX_SESSION_TURNS:]
    log["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Keep a short rolling summary for quick recall
    recent = log["turns"][-5:]
    summary_bits = []
    for t in recent:
        if t.get("user"):
            summary_bits.append(f"User: {t['user'][:120]}")
        if t.get("assistant"):
            summary_bits.append(f"IP Prime: {t['assistant'][:160]}")
    log["summary"] = " | ".join(summary_bits)[-2000:]

    SESSION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        try:
            SESSION_LOG_PATH.write_text(
                json.dumps(log, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            print(f"[Memory] [Error] Error saving session log: {e}")

    # Mirror last activity into long-term notes for cross-session recall
    if user or assistant:
        activity = user or assistant
        update_memory({
            "notes": {
                "last_interaction": {
                    "value": activity[:500],
                    "updated": datetime.now().strftime("%Y-%m-%d"),
                }
            }
        })

    try:
        from prime_platform.infinite_memory import archive_turn
        archive_turn(user=user, assistant=assistant)
    except Exception:
        pass

    try:
        from actions.semantic_store import index_conversation_turn
        if user:
            index_conversation_turn(role="user", content=user)
        if assistant:
            index_conversation_turn(role="assistant", content=assistant)
    except Exception as sem_e:
        print(f"[Memory] Vector indexing skipped: {sem_e}")

    try:
        auto_capture_from_turn(user=user, assistant=assistant)
    except Exception:
        pass


def auto_capture_from_turn(user: str = "", assistant: str = "") -> None:
    """Save dated notes and explicit 'remember' phrases without waiting for the model."""
    user = (user or "").strip()
    if not user or len(user) < 8:
        return

    u_l = user.lower()
    remember_triggers = (
        "yaad rakh", "yaad rakho", "remember this", "remember that",
        "don't forget", "mat bhoolna", "note kar", "save this",
        "merko yaad", "mujhe yaad", "yaad hai na",
    )
    if any(t in u_l for t in remember_triggers):
        update_memory({
            "notes": {
                f"user_said_{datetime.now().strftime('%Y%m%d_%H%M')}": {
                    "value": user[:900],
                    "updated": datetime.now().strftime("%Y-%m-%d"),
                }
            }
        })

    try:
        from prime_platform.infinite_memory import parse_query_date, store_dated_note

        when = parse_query_date(user) or datetime.now().strftime("%Y-%m-%d")
        if any(w in u_l for w in ("yaad rakh", "remember", "us din", "on that day", "date pe")):
            store_dated_note(when, user[:1500], topic=f"Pratik Sir said ({when})")
        elif len(user) > 40 and any(
            w in u_l for w in ("project", "plan", "favorite", "birthday", "kaam", "goal", "prefer")
        ):
            store_dated_note(
                datetime.now().strftime("%Y-%m-%d"),
                user[:1200],
                topic=f"Context ({datetime.now().strftime('%Y-%m-%d %H:%M')})",
            )
    except Exception:
        pass


def format_session_for_prompt(max_turns: int = 12) -> str:
    log = load_session_log()
    turns = log.get("turns", [])
    if not turns:
        return ""

    lines = [
        "[RECENT SESSION HISTORY — remember this naturally, refer back when Pratik Sir asks what you did last time]",
        f"Last active: {log.get('last_updated', 'unknown')}",
        "",
    ]
    for t in turns[-max_turns:]:
        ts = t.get("ts", "")
        if t.get("user"):
            lines.append(f"  [{ts}] Pratik Sir: {t['user']}")
        if t.get("assistant"):
            lines.append(f"  [{ts}] You: {t['assistant']}")

    summary = log.get("summary", "")
    if summary:
        lines.extend(["", f"Quick recap: {summary}"])

    return "\n".join(lines) + "\n"


def save_shutdown_summary() -> bool:
    """Write a compact recap when IP Prime stops (window close, exit, crash hook)."""
    log = load_session_log()
    turns = log.get("turns", [])
    if not turns:
        return False

    recent = turns[-SHUTDOWN_HIGHLIGHT_TURNS:]
    highlights: list[str] = []
    for t in recent:
        ts = t.get("ts", "")
        if t.get("user"):
            highlights.append(f"[{ts}] Pratik Sir: {t['user'][:280]}")
        if t.get("assistant"):
            highlights.append(f"[{ts}] IP Prime: {t['assistant'][:360]}")

    last = recent[-1]
    payload = {
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "last_active": log.get("last_updated", ""),
        "turn_count": len(turns),
        "summary": (log.get("summary") or "")[:2000],
        "highlights": highlights,
        "last_user": (last.get("user") or "")[:500],
        "last_assistant": (last.get("assistant") or "")[:800],
    }

    LAST_SESSION_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        try:
            LAST_SESSION_SUMMARY_PATH.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            print("[Memory] [OK] Last session summary saved for next startup.")
            return True
        except Exception as e:
            print(f"[Memory] [Error] Shutdown summary save failed: {e}")
            return False


def load_last_session_summary() -> dict:
    default = {
        "saved_at": "",
        "last_active": "",
        "turn_count": 0,
        "summary": "",
        "highlights": [],
        "last_user": "",
        "last_assistant": "",
    }
    if not LAST_SESSION_SUMMARY_PATH.exists():
        return default
    with _lock:
        try:
            data = json.loads(LAST_SESSION_SUMMARY_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {**default, **data}
        except Exception as e:
            print(f"[Memory] [Error] Error loading last session summary: {e}")
    return default


def format_last_session_for_prompt() -> str:
    data = load_last_session_summary()
    if not data.get("saved_at") and not data.get("summary") and not data.get("highlights"):
        return ""

    lines = [
        "[LAST SESSION BEFORE SHUTDOWN — use when Pratik Sir asks what you did last time or to continue work]",
        f"Saved when IP Prime closed: {data.get('saved_at', 'unknown')}",
        f"Last active: {data.get('last_active', 'unknown')} · {data.get('turn_count', 0)} turns in log",
        "",
    ]
    summary = (data.get("summary") or "").strip()
    if summary:
        lines.append(f"Session recap: {summary}")
        lines.append("")

    highlights = data.get("highlights") or []
    if highlights:
        lines.append("Recent highlights from that run:")
        for h in highlights[-6:]:
            lines.append(f"  • {h}")
        lines.append("")

    last_u = (data.get("last_user") or "").strip()
    last_a = (data.get("last_assistant") or "").strip()
    if last_u or last_a:
        lines.append("Last exchange before close:")
        if last_u:
            lines.append(f"  Pratik Sir: {last_u[:400]}")
        if last_a:
            lines.append(f"  You: {last_a[:500]}")

    return "\n".join(lines) + "\n"