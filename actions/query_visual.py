import sqlite3
from pathlib import Path
from typing import Any

def query_visual_timeline(parameters: dict[str, Any]) -> str:
    """Queries Saturday's visual timeline memory to find what the user was doing at a specific time or with a specific app."""
    query = parameters.get("query", "").strip().lower()
    if not query:
        return "Please provide a query search term, sir."

    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "memory" / "visual_timeline.db"

    if not db_path.exists():
        return "No visual memory timeline database exists yet, sir."

    try:
        conn = sqlite3.connect(str(db_path))
        try:
            c = conn.cursor()
            c.execute(
                "SELECT timestamp, summary, screenshot_path FROM timeline WHERE LOWER(summary) LIKE ? ORDER BY timestamp DESC LIMIT 5",
                (f"%{query}%",)
            )
            rows = c.fetchall()
        finally:
            conn.close()

        if not rows:
            return f"I couldn't find any screen snapshots in my visual timeline matching '{query}', sir."

        res = "Here is what I found in my visual timeline memory, sir:\n"
        for row in rows:
            timestamp, summary, path = row
            res += f"- [{timestamp}] {summary}\n"
        return res
    except Exception as e:
        return f"Failed to query visual timeline: {e}"
