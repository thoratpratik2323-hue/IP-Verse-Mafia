"""
brain.py — The Unlimited Memory Brain for IP Prime.

This is the unified orchestrator that connects ALL memory layers into a single
queryable, scalable brain with NO hard caps. Memory grows forever — old data
is compressed, summarised and tiered, never deleted.

Architecture:
    Layer 0: Working Memory     — current session turns (RAM, fast)
    Layer 1: Long-Term JSON     — identity, preferences, projects, relationships
    Layer 2: Episodic Memory    — task logs, what happened and when
    Layer 3: Procedural Memory  — proven workflows and how-to patterns
    Layer 4: Knowledge Base     — stored facts tagged by topic/date
    Layer 5: Archive JSONL      — raw daily conversation transcripts
    Layer 6: Vector Store       — semantic embeddings (LanceDB)
    Layer 7: Graph Store        — SQLite entity-relationship graph (brain.db)
    Layer 8: Compressed Digests — weekly/monthly summaries of old archives
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Any

import sys


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = _base_dir()
BRAIN_DB = BASE_DIR / "memory" / "brain.db"
DIGEST_DIR = BASE_DIR / "memory" / "digests"
_lock = Lock()


# ═══════════════════════════════════════════════════════════════════════════
#  GRAPH STORE — SQLite entity-relationship memory (Layer 7)
# ═══════════════════════════════════════════════════════════════════════════

def _get_db() -> sqlite3.Connection:
    """Get or create the brain.db SQLite connection."""
    BRAIN_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(BRAIN_DB), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            entity_type TEXT NOT NULL DEFAULT 'concept',
            metadata    TEXT DEFAULT '{}',
            created_at  TEXT NOT NULL,
            updated_at  TEXT NOT NULL,
            UNIQUE(name, entity_type)
        );

        CREATE TABLE IF NOT EXISTS relations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id   INTEGER NOT NULL REFERENCES entities(id),
            target_id   INTEGER NOT NULL REFERENCES entities(id),
            relation    TEXT NOT NULL,
            weight      REAL DEFAULT 1.0,
            context     TEXT DEFAULT '',
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS facts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            subject     TEXT NOT NULL,
            predicate   TEXT NOT NULL,
            object      TEXT NOT NULL,
            confidence  REAL DEFAULT 1.0,
            source      TEXT DEFAULT 'conversation',
            created_at  TEXT NOT NULL,
            expires_at  TEXT DEFAULT NULL
        );

        CREATE TABLE IF NOT EXISTS timeline (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date  TEXT NOT NULL,
            event_type  TEXT NOT NULL DEFAULT 'general',
            summary     TEXT NOT NULL,
            details     TEXT DEFAULT '',
            importance  INTEGER DEFAULT 5,
            created_at  TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS digests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            period_type TEXT NOT NULL,
            period_key  TEXT NOT NULL,
            summary     TEXT NOT NULL,
            turn_count  INTEGER DEFAULT 0,
            topics      TEXT DEFAULT '[]',
            created_at  TEXT NOT NULL,
            UNIQUE(period_type, period_key)
        );

        CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
        CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
        CREATE INDEX IF NOT EXISTS idx_facts_subject ON facts(subject);
        CREATE INDEX IF NOT EXISTS idx_facts_predicate ON facts(predicate);
        CREATE INDEX IF NOT EXISTS idx_timeline_date ON timeline(event_date);
        CREATE INDEX IF NOT EXISTS idx_digests_period ON digests(period_type, period_key);
    """)
    conn.commit()


# ─────────────────────────────────────────────────────────────────────────
#  Entity operations
# ─────────────────────────────────────────────────────────────────────────

def store_entity(name: str, entity_type: str = "concept",
                 metadata: dict | None = None) -> int:
    """Store or update an entity. Returns the entity ID."""
    now = datetime.now().isoformat(timespec="seconds")
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)
    with _lock:
        conn = _get_db()
        try:
            cur = conn.execute(
                "INSERT INTO entities (name, entity_type, metadata, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(name, entity_type) DO UPDATE SET "
                "metadata=excluded.metadata, updated_at=excluded.updated_at",
                (name.strip().lower(), entity_type.strip().lower(),
                 meta_json, now, now),
            )
            conn.commit()
            # Get the ID
            row = conn.execute(
                "SELECT id FROM entities WHERE name=? AND entity_type=?",
                (name.strip().lower(), entity_type.strip().lower()),
            ).fetchone()
            return row[0] if row else cur.lastrowid
        finally:
            conn.close()


def store_relation(source: str, relation: str, target: str,
                   weight: float = 1.0, context: str = "") -> None:
    """Store a relation between two entities (auto-creates entities)."""
    src_id = store_entity(source)
    tgt_id = store_entity(target)
    now = datetime.now().isoformat(timespec="seconds")
    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                "INSERT INTO relations (source_id, target_id, relation, weight, context, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (src_id, tgt_id, relation.strip().lower(), weight,
                 context[:2000], now),
            )
            conn.commit()
        finally:
            conn.close()


def store_fact(subject: str, predicate: str, obj: str,
               confidence: float = 1.0, source: str = "conversation") -> None:
    """Store a subject-predicate-object triple."""
    now = datetime.now().isoformat(timespec="seconds")
    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                "INSERT INTO facts (subject, predicate, object, confidence, source, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (subject.strip()[:500], predicate.strip()[:200],
                 obj.strip()[:2000], confidence, source[:100], now),
            )
            conn.commit()
        finally:
            conn.close()


def store_timeline_event(event_date: str, summary: str,
                         event_type: str = "general", details: str = "",
                         importance: int = 5) -> None:
    """Record a timestamped event in the timeline."""
    now = datetime.now().isoformat(timespec="seconds")
    with _lock:
        conn = _get_db()
        try:
            conn.execute(
                "INSERT INTO timeline (event_date, event_type, summary, details, importance, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (event_date, event_type, summary[:2000],
                 details[:8000], importance, now),
            )
            conn.commit()
        finally:
            conn.close()


# ─────────────────────────────────────────────────────────────────────────
#  Query operations
# ─────────────────────────────────────────────────────────────────────────

def query_entity(name: str) -> dict | None:
    """Look up an entity by name."""
    with _lock:
        conn = _get_db()
        try:
            row = conn.execute(
                "SELECT id, name, entity_type, metadata, created_at, updated_at "
                "FROM entities WHERE name = ?",
                (name.strip().lower(),),
            ).fetchone()
            if not row:
                return None
            return {
                "id": row[0], "name": row[1], "type": row[2],
                "metadata": json.loads(row[3] or "{}"),
                "created": row[4], "updated": row[5],
            }
        finally:
            conn.close()


def query_relations(entity_name: str, direction: str = "both") -> list[dict]:
    """Find all relations involving an entity."""
    name = entity_name.strip().lower()
    results = []
    with _lock:
        conn = _get_db()
        try:
            if direction in ("out", "both"):
                rows = conn.execute("""
                    SELECT e2.name, r.relation, r.weight, r.context, r.created_at
                    FROM relations r
                    JOIN entities e1 ON r.source_id = e1.id
                    JOIN entities e2 ON r.target_id = e2.id
                    WHERE e1.name = ?
                    ORDER BY r.weight DESC
                """, (name,)).fetchall()
                for r in rows:
                    results.append({
                        "direction": "->", "target": r[0],
                        "relation": r[1], "weight": r[2],
                        "context": r[3], "created": r[4],
                    })
            if direction in ("in", "both"):
                rows = conn.execute("""
                    SELECT e1.name, r.relation, r.weight, r.context, r.created_at
                    FROM relations r
                    JOIN entities e1 ON r.source_id = e1.id
                    JOIN entities e2 ON r.target_id = e2.id
                    WHERE e2.name = ?
                    ORDER BY r.weight DESC
                """, (name,)).fetchall()
                for r in rows:
                    results.append({
                        "direction": "<-", "source": r[0],
                        "relation": r[1], "weight": r[2],
                        "context": r[3], "created": r[4],
                    })
        finally:
            conn.close()
    return results


def query_facts(subject: str = "", predicate: str = "",
                limit: int = 50) -> list[dict]:
    """Search facts by subject and/or predicate."""
    conditions = []
    params = []
    if subject:
        conditions.append("subject LIKE ?")
        params.append(f"%{subject.strip()}%")
    if predicate:
        conditions.append("predicate LIKE ?")
        params.append(f"%{predicate.strip()}%")
    where = " AND ".join(conditions) if conditions else "1=1"
    with _lock:
        conn = _get_db()
        try:
            rows = conn.execute(
                f"SELECT subject, predicate, object, confidence, source, created_at "
                f"FROM facts WHERE {where} ORDER BY created_at DESC LIMIT ?",
                params + [limit],
            ).fetchall()
            return [
                {"subject": r[0], "predicate": r[1], "object": r[2],
                 "confidence": r[3], "source": r[4], "created": r[5]}
                for r in rows
            ]
        finally:
            conn.close()


def query_timeline(start_date: str = "", end_date: str = "",
                   event_type: str = "", limit: int = 50) -> list[dict]:
    """Query the timeline by date range and/or event type."""
    conditions = []
    params = []
    if start_date:
        conditions.append("event_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("event_date <= ?")
        params.append(end_date)
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
    where = " AND ".join(conditions) if conditions else "1=1"
    with _lock:
        conn = _get_db()
        try:
            rows = conn.execute(
                f"SELECT event_date, event_type, summary, details, importance, created_at "
                f"FROM timeline WHERE {where} ORDER BY event_date DESC LIMIT ?",
                params + [limit],
            ).fetchall()
            return [
                {"date": r[0], "type": r[1], "summary": r[2],
                 "details": r[3], "importance": r[4], "created": r[5]}
                for r in rows
            ]
        finally:
            conn.close()


# ═══════════════════════════════════════════════════════════════════════════
#  UNIFIED BRAIN SEARCH — searches ALL layers at once
# ═══════════════════════════════════════════════════════════════════════════

def brain_search(query: str, limit: int = 10) -> str:
    """
    The ultimate memory search. Queries ALL layers simultaneously:
    - Long-term JSON memories
    - Episodic memories
    - Knowledge base entries
    - Archive transcripts
    - SQLite graph (entities, facts, timeline)
    - Compressed digests
    - Vector store (if available)

    Returns a unified, formatted result string.
    """
    q = (query or "").strip()
    if not q:
        return "Please provide a search query for the brain."

    q_lower = q.lower()
    hits: list[tuple[int, str, str]] = []  # (score, layer, text)

    # ── Layer 1: Long-term JSON ──────────────────────────────────────
    try:
        from memory.memory_manager import load_memory
        mem = load_memory()
        for category, items in mem.items():
            if not isinstance(items, dict):
                continue
            for key, entry in items.items():
                val = entry.get("value", "") if isinstance(entry, dict) else str(entry)
                blob = f"{key} {val}".lower()
                score = _keyword_score(q_lower, blob)
                if score > 0:
                    hits.append((score + 10, "Long-Term",
                                 f"[{category}] {key}: {val[:300]}"))
    except Exception:
        pass

    # ── Layer 2: Episodic Memory ─────────────────────────────────────
    try:
        ep_path = BASE_DIR / "memory" / "episodic.json"
        if ep_path.exists():
            episodes = json.loads(ep_path.read_text(encoding="utf-8"))
            if isinstance(episodes, list):
                for ep in reversed(episodes[-200:]):
                    blob = f"{ep.get('goal', '')} {ep.get('result', '')}".lower()
                    score = _keyword_score(q_lower, blob)
                    if score > 0:
                        ts = ep.get("timestamp", "")[:16]
                        status = "✅" if ep.get("success") else "❌"
                        hits.append((score + 5, "Episodic",
                                     f"[{ts}] {status} {ep.get('goal', '')[:200]}"))
    except Exception:
        pass

    # ── Layer 4: Knowledge Base ──────────────────────────────────────
    try:
        kb_path = BASE_DIR / "memory" / "knowledge_base.json"
        if kb_path.exists():
            kb = json.loads(kb_path.read_text(encoding="utf-8"))
            for e in kb.get("entries", []):
                blob = f"{e.get('topic', '')} {e.get('content', '')} {' '.join(e.get('tags', []))}".lower()
                score = _keyword_score(q_lower, blob)
                if score > 0:
                    hits.append((score + 8, "Knowledge",
                                 f"{e.get('topic', '')}: {e.get('content', '')[:300]}"))
    except Exception:
        pass

    # ── Layer 5: Archive JSONL ───────────────────────────────────────
    try:
        archive_dir = BASE_DIR / "memory" / "archive"
        if archive_dir.exists():
            for path in sorted(archive_dir.glob("*.jsonl"), reverse=True)[:60]:
                try:
                    lines = path.read_text(encoding="utf-8").strip().splitlines()
                except Exception:
                    continue
                for line in reversed(lines[-300:]):
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    blob = f"{rec.get('user', '')} {rec.get('assistant', '')}".lower()
                    score = _keyword_score(q_lower, blob)
                    if score > 0:
                        ts = rec.get("ts", path.stem)
                        u = (rec.get("user") or "")[:150]
                        a = (rec.get("assistant") or "")[:150]
                        snippet = f"U: {u}" if u else ""
                        if a:
                            snippet += f" | P: {a}" if snippet else f"P: {a}"
                        hits.append((score, "Archive",
                                     f"[{ts}] {snippet[:350]}"))
    except Exception:
        pass

    # ── Layer 7: SQLite Graph (entities, facts, timeline) ────────────
    try:
        # Search entities
        with _lock:
            conn = _get_db()
            try:
                rows = conn.execute(
                    "SELECT name, entity_type, metadata FROM entities "
                    "WHERE name LIKE ? LIMIT 20",
                    (f"%{q_lower}%",),
                ).fetchall()
                for r in rows:
                    hits.append((15, "Entity",
                                 f"{r[0]} ({r[1]}): {r[2][:200]}"))

                # Search facts
                rows = conn.execute(
                    "SELECT subject, predicate, object FROM facts "
                    "WHERE subject LIKE ? OR object LIKE ? "
                    "ORDER BY created_at DESC LIMIT 20",
                    (f"%{q_lower}%", f"%{q_lower}%"),
                ).fetchall()
                for r in rows:
                    hits.append((12, "Fact",
                                 f"{r[0]} → {r[1]} → {r[2][:200]}"))

                # Search timeline
                rows = conn.execute(
                    "SELECT event_date, summary FROM timeline "
                    "WHERE summary LIKE ? ORDER BY event_date DESC LIMIT 15",
                    (f"%{q_lower}%",),
                ).fetchall()
                for r in rows:
                    hits.append((10, "Timeline",
                                 f"[{r[0]}] {r[1][:300]}"))
            finally:
                conn.close()
    except Exception:
        pass

    # ── Layer 8: Compressed Digests ──────────────────────────────────
    try:
        with _lock:
            conn = _get_db()
            try:
                rows = conn.execute(
                    "SELECT period_type, period_key, summary FROM digests "
                    "WHERE summary LIKE ? ORDER BY created_at DESC LIMIT 10",
                    (f"%{q_lower}%",),
                ).fetchall()
                for r in rows:
                    hits.append((8, "Digest",
                                 f"[{r[0]}:{r[1]}] {r[2][:400]}"))
            finally:
                conn.close()
    except Exception:
        pass

    # ── Layer 6: Vector Store (async-safe, skip if unavailable) ──────
    try:
        from actions.semantic_store import search_history_semantic
        vec_result = search_history_semantic(query=q, limit=3)
        if vec_result and "No semantic matches" not in vec_result:
            hits.append((20, "Vector", vec_result[:600]))
    except Exception:
        pass

    # ── Sort and format ──────────────────────────────────────────────
    hits.sort(key=lambda x: -x[0])
    if not hits:
        return f"🧠 No memories found for: '{q}'"

    lines = [
        f"═══ 🧠 UNLIMITED BRAIN — {len(hits)} hits for '{q}' ═══",
        "",
    ]
    seen = set()
    count = 0
    for score, layer, text in hits:
        if count >= limit:
            break
        key = text[:100]
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"  [{layer}] {text}")
        count += 1

    if len(hits) > limit:
        lines.append(f"\n  … and {len(hits) - limit} more results (refine your query)")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  BRAIN STATS
# ═══════════════════════════════════════════════════════════════════════════

def brain_stats() -> dict:
    """Return counts across all memory layers."""
    stats = {
        "long_term_categories": 0,
        "long_term_entries": 0,
        "episodic_episodes": 0,
        "procedural_workflows": 0,
        "knowledge_base_entries": 0,
        "archive_days": 0,
        "archive_turns": 0,
        "graph_entities": 0,
        "graph_relations": 0,
        "graph_facts": 0,
        "timeline_events": 0,
        "digests": 0,
        "vector_conversations": 0,
        "vector_documents": 0,
    }

    # Long-term
    try:
        from memory.memory_manager import load_memory
        mem = load_memory()
        stats["long_term_categories"] = len(mem)
        for cat, items in mem.items():
            if isinstance(items, dict):
                stats["long_term_entries"] += len(items)
    except Exception:
        pass

    # Episodic
    try:
        ep_path = BASE_DIR / "memory" / "episodic.json"
        if ep_path.exists():
            data = json.loads(ep_path.read_text(encoding="utf-8"))
            stats["episodic_episodes"] = len(data) if isinstance(data, list) else 0
    except Exception:
        pass

    # Procedural
    try:
        proc_path = BASE_DIR / "memory" / "procedural.json"
        if proc_path.exists():
            data = json.loads(proc_path.read_text(encoding="utf-8"))
            stats["procedural_workflows"] = len(data) if isinstance(data, dict) else 0
    except Exception:
        pass

    # Knowledge Base
    try:
        kb_path = BASE_DIR / "memory" / "knowledge_base.json"
        if kb_path.exists():
            kb = json.loads(kb_path.read_text(encoding="utf-8"))
            stats["knowledge_base_entries"] = len(kb.get("entries", []))
    except Exception:
        pass

    # Archive
    try:
        archive_dir = BASE_DIR / "memory" / "archive"
        if archive_dir.exists():
            files = list(archive_dir.glob("*.jsonl"))
            stats["archive_days"] = len(files)
            for f in files:
                try:
                    stats["archive_turns"] += sum(1 for _ in f.open(encoding="utf-8"))
                except Exception:
                    pass
    except Exception:
        pass

    # SQLite Graph
    try:
        with _lock:
            conn = _get_db()
            try:
                stats["graph_entities"] = conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
                stats["graph_relations"] = conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
                stats["graph_facts"] = conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0]
                stats["timeline_events"] = conn.execute("SELECT COUNT(*) FROM timeline").fetchone()[0]
                stats["digests"] = conn.execute("SELECT COUNT(*) FROM digests").fetchone()[0]
            finally:
                conn.close()
    except Exception:
        pass

    # Vector Store
    try:
        import lancedb
        db_path = BASE_DIR / "memory" / "lancedb_store"
        if db_path.exists():
            db = lancedb.connect(str(db_path))
            if "conversations" in db.list_table_names():
                stats["vector_conversations"] = db.open_table("conversations").count_rows()
            if "documents" in db.list_table_names():
                stats["vector_documents"] = db.open_table("documents").count_rows()
    except Exception:
        pass

    return stats


def format_brain_stats() -> str:
    """Human-readable brain stats for the prompt or UI."""
    s = brain_stats()
    total = sum(s.values())
    lines = [
        "🧠 ═══ UNLIMITED BRAIN STATUS ═══",
        f"  Total Memory Units: {total:,}",
        f"  Long-Term: {s['long_term_entries']} entries across {s['long_term_categories']} categories",
        f"  Episodic: {s['episodic_episodes']} task episodes",
        f"  Procedural: {s['procedural_workflows']} workflows",
        f"  Knowledge Base: {s['knowledge_base_entries']} facts",
        f"  Archive: {s['archive_days']} days, {s['archive_turns']} conversation turns",
        f"  Graph: {s['graph_entities']} entities, {s['graph_relations']} relations, {s['graph_facts']} facts",
        f"  Timeline: {s['timeline_events']} events",
        f"  Compressed Digests: {s['digests']}",
        f"  Vector Store: {s['vector_conversations']} conversations, {s['vector_documents']} document chunks",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
#  AUTO-EXTRACT — pull entities/facts from conversation turns
# ═══════════════════════════════════════════════════════════════════════════

def auto_extract_from_turn(user: str = "", assistant: str = "") -> None:
    """
    Automatically extract entities, facts, and timeline events from
    conversation turns. Runs heuristic NLP (no API calls needed).
    """
    text = f"{user} {assistant}".strip()
    if len(text) < 15:
        return

    try:
        _extract_entities(text)
        _extract_facts(user, assistant)
    except Exception as e:
        print(f"[Brain] Auto-extract error: {e}")


def _extract_entities(text: str) -> None:
    """Simple entity extraction via regex patterns."""
    # Extract capitalized proper nouns (2+ chars)
    words = re.findall(r'\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*)\b', text)
    # Filter out common English words
    stopwords = {
        "The", "This", "That", "What", "When", "Where", "How", "Why",
        "Yes", "Not", "But", "And", "For", "Are", "Was", "Can", "Has",
        "Did", "Does", "Will", "Would", "Could", "Should", "May",
        "Please", "Thanks", "Sure", "Good", "Great", "Nice", "Hello",
        "Hey", "Sir", "Bhai", "Yaar", "Okay", "Also", "Just", "Like",
    }
    for word in words:
        if word not in stopwords and len(word) > 2:
            store_entity(word, entity_type="mentioned")


def _extract_facts(user: str, assistant: str) -> None:
    """Extract explicit fact patterns from text."""
    user_lower = (user or "").lower()

    # "my X is Y" patterns
    patterns = [
        (r"my\s+(\w+)\s+is\s+(.+?)(?:\.|,|$)", "identity"),
        (r"i\s+(?:like|love|prefer)\s+(.+?)(?:\.|,|$)", "preference"),
        (r"mera\s+(\w+)\s+(?:hai|he)\s+(.+?)(?:\.|,|$)", "identity"),
        (r"mujhe\s+(.+?)\s+(?:pasand|acha)\s+(?:hai|lagta)", "preference"),
    ]
    for pattern, fact_type in patterns:
        matches = re.findall(pattern, user_lower, re.IGNORECASE)
        for match in matches:
            if isinstance(match, tuple) and len(match) >= 2:
                store_fact("pratik", match[0].strip(), match[1].strip()[:200],
                           source=fact_type)
            elif isinstance(match, str):
                store_fact("pratik", "likes", match.strip()[:200],
                           source=fact_type)


# ═══════════════════════════════════════════════════════════════════════════
#  UTILITY
# ═══════════════════════════════════════════════════════════════════════════

def _keyword_score(query: str, text: str) -> int:
    """Keyword match scoring."""
    if not text:
        return 0
    words = [w for w in re.split(r"\W+", query) if len(w) > 2]
    if not words:
        return 0
    return sum(3 if w in text else 0 for w in words)
