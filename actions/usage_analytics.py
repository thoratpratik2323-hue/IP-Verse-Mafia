"""
actions/usage_analytics.py — Tool usage tracking and weekly report.
Tracks which tools are called, response times, and failure rates.
Shows a weekly "IP Prime Report" like a GitHub contribution graph for AI.
"""
from __future__ import annotations
import json
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, Counter
from typing import Any

logger = logging.getLogger("usage_analytics")
ANALYTICS_PATH = Path("memory/usage_analytics.json")


class UsageAnalytics:
    """Track IP Prime tool usage and generate weekly reports."""

    def __init__(self):
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict:
        ANALYTICS_PATH.parent.mkdir(parents=True, exist_ok=True)
        if ANALYTICS_PATH.exists():
            try:
                return json.loads(ANALYTICS_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"calls": [], "daily_counts": {}}

    def _save(self):
        try:
            ANALYTICS_PATH.write_text(
                json.dumps(self._data, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.debug(f"[Analytics] Save failed: {e}")

    def record(self, tool_name: str, duration_ms: float = 0.0,
               success: bool = True, error: str = ""):
        """Record a single tool call."""
        today = datetime.now().strftime("%Y-%m-%d")
        call = {
            "tool": tool_name,
            "ts":   datetime.now().isoformat(),
            "ms":   round(duration_ms, 1),
            "ok":   success,
            "err":  error[:100] if error else "",
        }
        self._data.setdefault("calls", []).append(call)
        # Keep only last 2000 calls to avoid bloat
        if len(self._data["calls"]) > 2000:
            self._data["calls"] = self._data["calls"][-2000:]

        # Daily counter
        daily = self._data.setdefault("daily_counts", {})
        daily[today] = daily.get(today, 0) + 1
        self._save()

    def weekly_report(self) -> str:
        """Generate a text report of the past 7 days."""
        calls = self._data.get("calls", [])
        cutoff = datetime.now() - timedelta(days=7)
        recent = [
            c for c in calls
            if datetime.fromisoformat(c["ts"]) >= cutoff
        ]

        if not recent:
            return "📊 IP Prime Report: Koi data nahi pichle 7 din mein."

        total = len(recent)
        failed = sum(1 for c in recent if not c.get("ok", True))
        success_rate = round((total - failed) / total * 100, 1) if total else 0

        tool_counts = Counter(c["tool"] for c in recent)
        top_tools = tool_counts.most_common(5)

        avg_ms = sum(c.get("ms", 0) for c in recent) / max(len(recent), 1)

        # Build daily activity line
        daily = self._data.get("daily_counts", {})
        activity = []
        for i in range(7):
            day = (datetime.now() - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            count = daily.get(day, 0)
            bar = "█" * min(count // 5, 8) or "▁"
            activity.append(bar)

        report_lines = [
            "📊 IP Prime — Weekly Usage Report",
            f"{'─' * 38}",
            f"📅 Period: Last 7 days",
            f"⚡ Total calls:   {total:,}",
            f"✅ Success rate:  {success_rate}%",
            f"❌ Failures:      {failed}",
            f"⏱️  Avg response:  {round(avg_ms)}ms",
            "",
            "📈 Daily Activity:",
            "  " + " ".join(activity),
            "  Mon Tue Wed Thu Fri Sat Sun",
            "",
            "🔥 Top Tools Used:",
        ]
        for tool, count in top_tools:
            bar = "█" * min(count // 3, 12)
            report_lines.append(f"  {tool[:25]:<25} {bar} {count}")

        return "\n".join(report_lines)

    def top_tools(self, n: int = 10) -> list[tuple[str, int]]:
        calls = self._data.get("calls", [])
        return Counter(c["tool"] for c in calls).most_common(n)

    def failure_rate_by_tool(self) -> dict[str, float]:
        calls = self._data.get("calls", [])
        tool_total: dict[str, int] = defaultdict(int)
        tool_fail:  dict[str, int] = defaultdict(int)
        for c in calls:
            t = c["tool"]
            tool_total[t] += 1
            if not c.get("ok", True):
                tool_fail[t] += 1
        return {
            t: round(tool_fail[t] / tool_total[t] * 100, 1)
            for t in tool_total if tool_total[t] >= 3
        }


def run(args: dict) -> str:
    """Tool entry point for IP Prime."""
    action = args.get("action", "report")
    analytics = UsageAnalytics()

    if action == "report":
        return analytics.weekly_report()
    if action == "top_tools":
        tools = analytics.top_tools(10)
        lines = ["🔥 Most Used Tools:"]
        for t, c in tools:
            lines.append(f"  {t:<30} {c} calls")
        return "\n".join(lines)
    if action == "failures":
        rates = analytics.failure_rate_by_tool()
        if not rates:
            return "✅ Sab tools theek chal rahe hain!"
        lines = ["⚠️ Tools With Failures:"]
        for t, rate in sorted(rates.items(), key=lambda x: -x[1]):
            lines.append(f"  {t:<30} {rate}% failure rate")
        return "\n".join(lines)
    return f"❌ Unknown action: {action}. Use: report | top_tools | failures"
