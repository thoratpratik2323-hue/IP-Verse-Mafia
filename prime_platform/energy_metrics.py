"""Real-time energy / API cost tracking and comparison dashboards."""
from __future__ import annotations

import json
from datetime import datetime
from threading import Lock

import psutil

from prime_platform.config import BASE_DIR, load_prime_config

USAGE_PATH = BASE_DIR / "memory" / "usage_metrics.json"
_lock = Lock()

# Rough USD per 1M tokens (input+output blended estimate)
_CLOUD_COMPARE = {
    "gemini_flash": 0.15,
    "gemini_pro": 1.25,
    "gpt_4o": 5.0,
    "claude_sonnet": 3.0,
    "local_ollama": 0.0,
}


def _load_usage() -> dict:
    default = {
        "sessions": [],
        "totals": {"tool_calls": 0, "est_tokens": 0, "est_usd": 0.0},
        "by_day": {},
    }
    if not USAGE_PATH.exists():
        return default
    with _lock:
        try:
            return json.loads(USAGE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return default


def _save_usage(data: dict) -> None:
    USAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        USAGE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def record_tool_call(tool_name: str, est_tokens: int | None = None) -> None:
    cfg = load_prime_config()
    if not cfg.get("energy_metrics", {}).get("enabled", True):
        return
    em = cfg["energy_metrics"]
    tokens = est_tokens or int(em.get("estimate_tokens_per_tool_call", 800))
    rate = float(em.get("gemini_flash_per_1m_tokens_usd", 0.15))
    usd = tokens / 1_000_000 * rate

    day = datetime.now().strftime("%Y-%m-%d")
    data = _load_usage()
    data["totals"]["tool_calls"] = data["totals"].get("tool_calls", 0) + 1
    data["totals"]["est_tokens"] = data["totals"].get("est_tokens", 0) + tokens
    data["totals"]["est_usd"] = round(data["totals"].get("est_usd", 0) + usd, 6)

    by_day = data.setdefault("by_day", {})
    day_rec = by_day.setdefault(day, {"tool_calls": 0, "est_tokens": 0, "est_usd": 0.0})
    day_rec["tool_calls"] += 1
    day_rec["est_tokens"] += tokens
    day_rec["est_usd"] = round(day_rec.get("est_usd", 0) + usd, 6)

    data["sessions"] = (data.get("sessions", []) + [{
        "ts": datetime.now().isoformat(timespec="seconds"),
        "tool": tool_name,
        "tokens": tokens,
        "usd": round(usd, 6),
    }])[-500:]

    _save_usage(data)


def _system_power_hint() -> dict:
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory().percent
    try:
        battery = psutil.sensors_battery()
        batt_pct = battery.percent if battery else None
        on_power = not battery.power_plugged if battery else None
    except Exception:
        batt_pct, on_power = None, None
    est_watts = 15 + (cpu / 100) * 45 + (mem / 100) * 20
    return {
        "cpu_percent": round(cpu, 1),
        "ram_percent": round(mem, 1),
        "est_system_watts": round(est_watts, 1),
        "battery_percent": batt_pct,
        "on_ac_power": on_power,
    }


def get_energy_dashboard() -> str:
    data = _load_usage()
    totals = data.get("totals", {})
    day = datetime.now().strftime("%Y-%m-%d")
    today = data.get("by_day", {}).get(day, {})
    power = _system_power_hint()

    lines = [
        "═══ IP PRIME ENERGY & COST DASHBOARD ═══",
        "",
        "── Today ──",
        f"  Tool calls: {today.get('tool_calls', 0)}",
        f"  Est. tokens: {today.get('est_tokens', 0):,}",
        f"  Est. API cost: ${today.get('est_usd', 0):.4f}",
        "",
        "── All time (this install) ──",
        f"  Tool calls: {totals.get('tool_calls', 0)}",
        f"  Est. tokens: {totals.get('est_tokens', 0):,}",
        f"  Est. API cost: ${totals.get('est_usd', 0):.4f}",
        "",
        "── System power (estimate) ──",
        f"  CPU: {power['cpu_percent']}%  RAM: {power['ram_percent']}%",
        f"  Est. draw: ~{power['est_system_watts']} W",
    ]
    if power.get("battery_percent") is not None:
        src = "AC" if power.get("on_ac_power") else "Battery"
        lines.append(f"  Battery: {power['battery_percent']}% ({src})")

    lines.extend(["", "── Cloud cost comparison (per 1M tokens, indicative) ──"])
    est_m = max(totals.get("est_tokens", 0) / 1_000_000, 0.001)
    for name, rate in _CLOUD_COMPARE.items():
        cost = est_m * rate
        lines.append(f"  {name.replace('_', ' ').title():16} ${rate:.2f}/1M → ~${cost:.4f} at your volume")

    lines.append("")
    lines.append("Local Ollama inference: $0 API cost (electricity only).")
    return "\n".join(lines)


def get_footer_summary() -> str:
    data = _load_usage()
    day = datetime.now().strftime("%Y-%m-%d")
    today = data.get("by_day", {}).get(day, {})
    power = _system_power_hint()
    return (
        f"API ${today.get('est_usd', 0):.3f} today · "
        f"~{power['est_system_watts']}W · "
        f"CPU {power['cpu_percent']:.0f}%"
    )
