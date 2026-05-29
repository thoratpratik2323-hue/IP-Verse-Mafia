"""
summarizer.py — Archive Compression Engine for Unlimited Memory Brain.

Compresses old daily JSONL archives into weekly and monthly digests,
stored in SQLite. Raw archives are kept forever but digests let the
brain recall months of context efficiently.

Schedule: run compress_old_archives() daily (or on startup).
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

import sys


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
ARCHIVE_DIR = BASE_DIR / "memory" / "archive"
DIGEST_DIR = BASE_DIR / "memory" / "digests"
_lock = Lock()


def compress_old_archives(days_threshold: int = 7) -> str:
    """
    Scan archive JSONL files older than `days_threshold` days.
    For each week that hasn't been digested yet, create a compressed
    summary and store it in the brain's SQLite digests table.

    Returns a status string.
    """
    if not ARCHIVE_DIR.exists():
        return "No archive directory found."

    cutoff = datetime.now() - timedelta(days=days_threshold)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    # Group archive files by ISO week
    week_buckets: dict[str, list[Path]] = defaultdict(list)
    month_buckets: dict[str, list[Path]] = defaultdict(list)

    for path in sorted(ARCHIVE_DIR.glob("*.jsonl")):
        if not re.match(r"20\d{2}-\d{2}-\d{2}", path.stem):
            continue
        if path.stem >= cutoff_str:
            continue  # Too recent, skip

        try:
            dt = datetime.strptime(path.stem, "%Y-%m-%d")
        except ValueError:
            continue

        # ISO week key: "2026-W22"
        iso_year, iso_week, _ = dt.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        week_buckets[week_key].append(path)

        # Month key: "2026-05"
        month_key = dt.strftime("%Y-%m")
        month_buckets[month_key].append(path)

    results = []

    # Process weekly digests
    for week_key, paths in week_buckets.items():
        try:
            if _digest_exists("weekly", week_key):
                continue
            summary = _summarize_archive_files(paths, max_turns=200)
            if summary:
                _store_digest("weekly", week_key, summary, paths)
                results.append(f"✅ Weekly digest: {week_key} ({len(paths)} days)")
        except Exception as e:
            results.append(f"❌ Weekly {week_key}: {e}")

    # Process monthly digests (only if the month is fully past)
    current_month = datetime.now().strftime("%Y-%m")
    for month_key, paths in month_buckets.items():
        if month_key >= current_month:
            continue  # Current month not complete yet
        try:
            if _digest_exists("monthly", month_key):
                continue
            summary = _summarize_archive_files(paths, max_turns=500)
            if summary:
                _store_digest("monthly", month_key, summary, paths)
                results.append(f"✅ Monthly digest: {month_key} ({len(paths)} days)")
        except Exception as e:
            results.append(f"❌ Monthly {month_key}: {e}")

    if not results:
        return "All archives already digested — nothing new to compress."

    return "\n".join(results)


def _summarize_archive_files(paths: list[Path], max_turns: int = 200) -> str:
    """
    Create a text summary from multiple JSONL archive files.
    Uses extractive summarization (topic frequency + key phrases).
    """
    all_topics: dict[str, int] = defaultdict(int)
    all_user_msgs: list[str] = []
    all_assistant_msgs: list[str] = []
    turn_count = 0

    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").strip().splitlines()
        except Exception:
            continue

        for line in lines:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            turn_count += 1
            u = (rec.get("user") or "").strip()
            a = (rec.get("assistant") or "").strip()

            if u:
                all_user_msgs.append(u[:300])
                _extract_topics(u, all_topics)
            if a:
                all_assistant_msgs.append(a[:300])

    if turn_count == 0:
        return ""

    # Build summary
    top_topics = sorted(all_topics.items(), key=lambda x: -x[1])[:20]
    topic_str = ", ".join(f"{t[0]} ({t[1]}x)" for t in top_topics if t[1] > 1)

    # Sample representative messages
    sample_size = min(10, len(all_user_msgs))
    step = max(1, len(all_user_msgs) // sample_size) if sample_size else 1
    samples = [all_user_msgs[i] for i in range(0, len(all_user_msgs), step)][:sample_size]

    date_range = f"{paths[0].stem} to {paths[-1].stem}" if paths else "unknown"

    summary_parts = [
        f"Period: {date_range}",
        f"Total turns: {turn_count}",
        f"User messages: {len(all_user_msgs)}, Assistant messages: {len(all_assistant_msgs)}",
    ]

    if topic_str:
        summary_parts.append(f"Top topics: {topic_str}")

    if samples:
        summary_parts.append("Sample user messages:")
        for s in samples:
            summary_parts.append(f"  - {s[:150]}")

    return "\n".join(summary_parts)


def _extract_topics(text: str, topics: dict[str, int]) -> None:
    """Extract meaningful topics/keywords from text."""
    # Split into words, filter noise
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    stopwords = {
        "this", "that", "what", "when", "where", "which", "with",
        "have", "been", "will", "would", "could", "should", "about",
        "from", "they", "them", "their", "there", "than", "then",
        "just", "like", "also", "some", "more", "very", "your",
        "make", "know", "want", "need", "please", "thanks", "okay",
        "yeah", "yaar", "bhai", "karo", "kiya", "hain", "nahi",
        "abhi", "mujhe", "kuch", "sahi", "file", "code", "done",
    }
    for word in words:
        if word not in stopwords:
            topics[word] += 1


def _digest_exists(period_type: str, period_key: str) -> bool:
    """Check if a digest already exists in SQLite."""
    try:
        from memory.brain import _get_db, _lock as brain_lock
        with brain_lock:
            conn = _get_db()
            try:
                row = conn.execute(
                    "SELECT COUNT(*) FROM digests WHERE period_type=? AND period_key=?",
                    (period_type, period_key),
                ).fetchone()
                return row[0] > 0 if row else False
            finally:
                conn.close()
    except Exception:
        return False


def _store_digest(period_type: str, period_key: str, summary: str,
                  paths: list[Path]) -> None:
    """Store a digest in SQLite."""
    from memory.brain import _get_db, _lock as brain_lock

    now = datetime.now().isoformat(timespec="seconds")
    turn_count = 0
    for p in paths:
        try:
            turn_count += sum(1 for _ in p.open(encoding="utf-8"))
        except Exception:
            pass

    # Extract top topics as JSON list
    topics: dict[str, int] = defaultdict(int)
    for p in paths:
        try:
            for line in p.read_text(encoding="utf-8").strip().splitlines()[:100]:
                try:
                    rec = json.loads(line)
                    _extract_topics(rec.get("user", ""), topics)
                except Exception:
                    pass
        except Exception:
            pass

    top_topics = [t[0] for t in sorted(topics.items(), key=lambda x: -x[1])[:15]]

    with brain_lock:
        conn = _get_db()
        try:
            conn.execute(
                "INSERT OR REPLACE INTO digests "
                "(period_type, period_key, summary, turn_count, topics, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (period_type, period_key, summary[:10000],
                 turn_count, json.dumps(top_topics), now),
            )
            conn.commit()
        finally:
            conn.close()


def get_digest(period_type: str, period_key: str) -> str | None:
    """Retrieve a specific digest."""
    try:
        from memory.brain import _get_db, _lock as brain_lock
        with brain_lock:
            conn = _get_db()
            try:
                row = conn.execute(
                    "SELECT summary, turn_count, topics FROM digests "
                    "WHERE period_type=? AND period_key=?",
                    (period_type, period_key),
                ).fetchone()
                if row:
                    return f"[{period_type.upper()} DIGEST: {period_key}]\n" \
                           f"Turns: {row[1]} | Topics: {row[2]}\n\n{row[0]}"
                return None
            finally:
                conn.close()
    except Exception:
        return None


def list_digests(limit: int = 30) -> list[dict]:
    """List all available digests."""
    try:
        from memory.brain import _get_db, _lock as brain_lock
        with brain_lock:
            conn = _get_db()
            try:
                rows = conn.execute(
                    "SELECT period_type, period_key, turn_count, topics, created_at "
                    "FROM digests ORDER BY period_key DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [
                    {"type": r[0], "key": r[1], "turns": r[2],
                     "topics": json.loads(r[3] or "[]"), "created": r[4]}
                    for r in rows
                ]
            finally:
                conn.close()
    except Exception:
        return []
