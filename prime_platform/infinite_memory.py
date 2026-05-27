"""Infinite memory — long-term archive + personal knowledge base."""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from threading import Lock

from prime_platform.config import BASE_DIR, load_prime_config

ARCHIVE_DIR = BASE_DIR / "memory" / "archive"
KB_PATH = BASE_DIR / "memory" / "knowledge_base.json"
_lock = Lock()

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def _ensure_dirs() -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def _load_kb() -> dict:
    default = {"entries": [], "updated": ""}
    if not KB_PATH.exists():
        return default
    with _lock:
        try:
            data = json.loads(KB_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {**default, **data}
        except Exception:
            pass
    return default


def _save_kb(data: dict) -> None:
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    with _lock:
        KB_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def archive_turn(user: str = "", assistant: str = "") -> None:
    cfg = load_prime_config()
    if not cfg.get("infinite_memory", {}).get("enabled", True):
        return
    user = (user or "").strip()
    assistant = (assistant or "").strip()
    if not user and not assistant:
        return

    _ensure_dirs()
    day = datetime.now().strftime("%Y-%m-%d")
    path = ARCHIVE_DIR / f"{day}.jsonl"
    record = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "user": user[:2000],
        "assistant": assistant[:4000],
    }
    with _lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


def store_knowledge(topic: str, content: str, tags: list | None = None) -> str:
    topic = (topic or "").strip()
    content = (content or "").strip()
    if not topic or not content:
        return "Need both topic and content to store knowledge."
    kb = _load_kb()
    entries = kb.get("entries", [])
    entries.append({
        "id": f"kb_{len(entries) + 1}",
        "topic": topic[:200],
        "content": content[:8000],
        "tags": tags or [],
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    kb["entries"] = entries[-5000:]
    _save_kb(kb)
    return f"Stored knowledge: {topic} ({len(content)} chars)"


def parse_query_date(text: str, reference: datetime | None = None) -> str | None:
    """Extract YYYY-MM-DD from natural language (English + Hinglish)."""
    ref = reference or datetime.now()
    t = (text or "").lower()

    m = re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b", t)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", t)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).strftime("%Y-%m-%d")
        except ValueError:
            pass

    m = re.search(
        r"\b(\d{1,2})\s+(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
        r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
        r"nov(?:ember)?|dec(?:ember)?)(?:\s+(20\d{2}))?\b",
        t,
        re.I,
    )
    if m:
        day = int(m.group(1))
        mon_key = m.group(2).lower()[:3]
        year = int(m.group(3)) if m.group(3) else ref.year
        month = _MONTHS.get(mon_key) or _MONTHS.get(m.group(2).lower(), 0)
        if month:
            try:
                return datetime(year, month, day).strftime("%Y-%m-%d")
            except ValueError:
                pass

    past_hint = any(
        w in t
        for w in (
            "yaad", "remember", "recall", "kya kiya", "kya bola", "us din",
            "that day", "last time", "pichle", "bolatha", "bataya", "kaha tha",
        )
    )
    if past_hint or "yesterday" in t:
        if "yesterday" in t or re.search(r"\bkal\b", t):
            return (ref - timedelta(days=1)).strftime("%Y-%m-%d")
        if re.search(r"\bparso\b", t) or "day before yesterday" in t:
            return (ref - timedelta(days=2)).strftime("%Y-%m-%d")
        if re.search(r"\baaj\b", t) and "today" in t:
            return ref.strftime("%Y-%m-%d")

    return None


def list_archive_dates(limit: int = 60) -> list[str]:
    _ensure_dirs()
    dates = sorted(
        (p.stem for p in ARCHIVE_DIR.glob("*.jsonl") if re.match(r"20\d{2}-\d{2}-\d{2}", p.stem)),
        reverse=True,
    )
    return dates[:limit]


def recall_by_date(date: str, query: str = "", limit: int = 30) -> str:
    """Return full conversation log for a calendar day (+ optional keyword filter)."""
    date = (date or "").strip()
    if not re.match(r"20\d{2}-\d{2}-\d{2}", date):
        return f"Invalid date format: {date} (use YYYY-MM-DD)"

    path = ARCHIVE_DIR / f"{date}.jsonl"
    records: list[dict] = []
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").strip().splitlines():
                if line.strip():
                    records.append(json.loads(line))
        except Exception as e:
            return f"Error reading archive for {date}: {e}"

    q = (query or "").strip().lower()
    if q:
        filtered = []
        for rec in records:
            blob = f"{rec.get('user', '')} {rec.get('assistant', '')}".lower()
            if _score(q, blob) > 0 or q in blob:
                filtered.append(rec)
        records = filtered

    kb = _load_kb()
    kb_hits = []
    for e in kb.get("entries", []):
        tags = e.get("tags") or []
        created = (e.get("created") or "")[:10]
        if f"date:{date}" in tags or created == date:
            kb_hits.append(e)

    if not records and not kb_hits:
        known = list_archive_dates(14)
        hint = f" Known recent days: {', '.join(known[:7])}" if known else ""
        return f"No memories archived for {date}.{hint}"

    lines = [f"═══ FULL DAY MEMORY — {date} ({len(records)} conversation turns) ═══"]
    for rec in records[:limit]:
        ts = rec.get("ts", "")
        u = (rec.get("user") or "").strip()
        a = (rec.get("assistant") or "").strip()
        if u:
            lines.append(f"  [{ts}] Pratik Sir: {u[:500]}")
        if a:
            lines.append(f"  [{ts}] IP Prime: {a[:600]}")

    if len(records) > limit:
        lines.append(f"  … and {len(records) - limit} more turns (ask with a narrower query)")

    if kb_hits:
        lines.append("")
        lines.append("Saved facts tagged for this date:")
        for e in kb_hits[:10]:
            lines.append(f"  • {e.get('topic')}: {e.get('content', '')[:400]}")

    return "\n".join(lines)


def store_dated_note(date: str, content: str, topic: str = "") -> str:
    date = (date or "").strip()
    content = (content or "").strip()
    if not date or not content:
        return "Need date (YYYY-MM-DD) and content."
    topic = (topic or f"Pratik Sir on {date}")[:200]
    return store_knowledge(topic, content, tags=[f"date:{date}", "dated_memory", "auto_capture"])


def recall_memory(query: str, limit: int = 8, date: str = "") -> str:
    query_raw = (query or "").strip()
    query_l = query_raw.lower()

    explicit_date = (date or "").strip()
    if not explicit_date:
        explicit_date = parse_query_date(query_raw) or ""

    if explicit_date:
        date_block = recall_by_date(explicit_date, query=query_raw, limit=max(limit, 20))
        if "FULL DAY MEMORY" in date_block or "Saved facts tagged" in date_block:
            return date_block
        if not query_l:
            return date_block
        if "no memories archived" not in date_block.lower():
            return date_block

    if not query_l and not explicit_date:
        return "Provide a query or date (YYYY-MM-DD) to search infinite memory."

    hits: list[tuple[int, str]] = []

    kb = _load_kb()
    for e in kb.get("entries", []):
        blob = f"{e.get('topic', '')} {e.get('content', '')} {' '.join(e.get('tags', []))}".lower()
        score = _score(query_l, blob)
        if score > 0:
            hits.append((score, f"[KB] {e.get('topic')}: {e.get('content', '')[:400]}"))

    _ensure_dirs()
    for path in sorted(ARCHIVE_DIR.glob("*.jsonl"), reverse=True)[:45]:
        day_tag = path.stem
        try:
            lines = path.read_text(encoding="utf-8").strip().splitlines()
        except Exception:
            continue
        for line in reversed(lines[-250:]):
            try:
                rec = json.loads(line)
            except Exception:
                continue
            blob = f"{rec.get('user', '')} {rec.get('assistant', '')}".lower()
            score = _score(query_l, blob)
            if explicit_date and day_tag == explicit_date:
                score += 40
            if score > 0:
                ts = rec.get("ts", day_tag)
                u = (rec.get("user") or "").strip()
                a = (rec.get("assistant") or "").strip()
                snippet = u or a
                if u and a:
                    snippet = f"U: {u[:180]} | P: {a[:180]}"
                hits.append((score, f"[{ts}] {snippet[:400]}"))

    try:
        from actions.semantic_store import semantic_search
        vec = semantic_search(query=query_raw)
        if vec and "No relevant" not in vec and "Error" not in vec[:20]:
            hits.append((50, f"[Vector] {vec[:600]}"))
    except Exception:
        pass

    hits.sort(key=lambda x: -x[0])
    if not hits:
        return f"No memories found for: {query}"

    lines = [f"═══ INFINITE MEMORY — {len(hits[:limit])} hits for '{query}' ═══"]
    seen = set()
    for _, text in hits[:limit]:
        if text in seen:
            continue
        seen.add(text)
        lines.append(f"  • {text}")
    return "\n".join(lines)


def format_archive_calendar_for_prompt(max_days: int = 14, *, include_samples: bool = False) -> str:
    """Short index of which days have logs — prompts date-based recall."""
    cfg = load_prime_config()
    if not cfg.get("infinite_memory", {}).get("enabled", True):
        return ""
    rt = cfg.get("realtime", {})
    if rt.get("lean_prompt", True):
        max_days = min(max_days, int(rt.get("calendar_days_in_prompt", 5)))
        include_samples = False
    _ensure_dirs()
    dates = list_archive_dates(max_days)
    if not dates:
        return ""

    lines = [
        "[CONVERSATION CALENDAR — chats saved by date; for past days use prime_infinite_memory "
        "action=recall_by_date with date=YYYY-MM-DD]",
        "",
    ]
    for day in dates[:max_days]:
        path = ARCHIVE_DIR / f"{day}.jsonl"
        try:
            n = sum(1 for _ in path.open(encoding="utf-8"))
        except Exception:
            n = 0
        extra = ""
        if include_samples and n:
            try:
                tail = path.read_text(encoding="utf-8").strip().splitlines()[-1:]
                if tail:
                    rec = json.loads(tail[0])
                    u = (rec.get("user") or "").strip()
                    if u:
                        extra = f' — e.g. "{u[:60]}…"'
            except Exception:
                pass
        lines.append(f"  • {day}: {n} turns{extra}")
    return "\n".join(lines) + "\n"


def format_infinite_context_for_prompt(max_entries: int = 6) -> str:
    cfg = load_prime_config()
    if not cfg.get("infinite_memory", {}).get("enabled", True):
        return ""
    cal_days = 10
    if cfg.get("realtime", {}).get("lean_prompt", True):
        max_entries = min(max_entries, 3)
        cal_days = int(cfg.get("realtime", {}).get("calendar_days_in_prompt", 5))
    parts = [format_archive_calendar_for_prompt(max_days=cal_days)]
    kb = _load_kb()
    entries = kb.get("entries", [])
    if entries:
        lines = ["[PERSONAL KNOWLEDGE BASE — use naturally when relevant]"]
        for e in entries[-max_entries:]:
            tags = ", ".join(e.get("tags") or [])
            tag_s = f" ({tags})" if tags else ""
            lines.append(f"  • {e.get('topic')}{tag_s}: {e.get('content', '')[:300]}")
        parts.append("\n".join(lines) + "\n")
    return "".join(p for p in parts if p)


def get_memory_stats() -> dict:
    kb = _load_kb()
    archive_files = list(ARCHIVE_DIR.glob("*.jsonl")) if ARCHIVE_DIR.exists() else []
    archive_lines = 0
    for p in archive_files:
        try:
            archive_lines += sum(1 for _ in p.open(encoding="utf-8"))
        except Exception:
            pass
    return {
        "kb_entries": len(kb.get("entries", [])),
        "archive_days": len(archive_files),
        "archive_turns": archive_lines,
    }


def _score(query: str, text: str) -> int:
    if not text:
        return 0
    words = [w for w in re.split(r"\W+", query) if len(w) > 2]
    if not words:
        return 0
    return sum(2 if w in text else 0 for w in words)
