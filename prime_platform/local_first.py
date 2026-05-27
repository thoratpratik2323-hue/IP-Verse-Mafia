"""Local-first framework: on-device LLM detection and routing preferences."""
from __future__ import annotations

import json
import subprocess
import urllib.request
from typing import Any

from prime_platform.config import load_prime_config, save_prime_config


def _friendly_conn_error(err: str) -> str:
    e = (err or "").strip().lower()
    if "timed out" in e or "timeout" in e:
        return (
            "Ollama not reachable (timed out). "
            "Start the Ollama app, or use IP Prime with cloud Gemini only — local mode is optional."
        )
    if "connection refused" in e or "10061" in e or "actively refused" in e:
        return (
            "Ollama is not running on this PC. "
            "Install from ollama.com and run it, or ignore local-first if you only use Gemini."
        )
    if "getaddrinfo" in e or "name or service not known" in e:
        return "Invalid Ollama URL — check config/prime_features.json → local_first.ollama_url"
    return (err or "Unknown connection error").strip()


def probe_ollama(url: str | None = None, timeout: float = 5.0) -> dict[str, Any]:
    cfg = load_prime_config()
    base = (url or cfg["local_first"]["ollama_url"]).rstrip("/")
    try:
        req = urllib.request.Request(f"{base}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        models = [m.get("name", "") for m in data.get("models", [])]
        return {"online": True, "url": base, "models": models, "count": len(models)}
    except Exception as e:
        return {
            "online": False,
            "url": base,
            "models": [],
            "error": _friendly_conn_error(str(e)),
        }


def get_local_status(ollama: dict[str, Any] | None = None) -> str:
    cfg = load_prime_config()
    lf = cfg["local_first"]
    ollama = ollama if ollama is not None else probe_ollama()
    lines = [
        "═══ IP PRIME LOCAL-FIRST STATUS ═══",
        f"Local-first mode: {'ON' if lf.get('enabled') else 'OFF'}",
        f"Ollama endpoint: {lf.get('ollama_url')}",
        f"Preferred local model: {lf.get('preferred_local_model')}",
        f"Cloud fallback: {'yes' if lf.get('fallback_to_cloud', True) else 'no'}",
        "",
        f"Ollama: {'online' if ollama.get('online') else 'offline'}",
    ]
    if ollama.get("online"):
        models = ollama.get("models") or []
        lines.append(f"Local models available ({len(models)}):")
        for m in models[:12]:
            lines.append(f"  • {m}")
        if len(models) > 12:
            lines.append(f"  … and {len(models) - 12} more")
    elif ollama.get("error"):
        lines.append(f"  ({ollama['error']})")

    lines.extend([
        "",
        "Architecture:",
        "  • Voice core: Gemini Live (cloud) unless you switch to a local stack later",
        "  • Tools & memory: on-device (JSON, LanceDB, file index)",
        "  • Optional: route text tasks to Ollama via prime_writing when local-first is ON",
    ])
    return "\n".join(lines)


def set_local_first(enabled: bool | None = None, ollama_url: str | None = None, model: str | None = None) -> str:
    cfg = load_prime_config()
    lf = cfg["local_first"]
    if enabled is not None:
        lf["enabled"] = bool(enabled)
    if ollama_url:
        lf["ollama_url"] = ollama_url.strip().rstrip("/")
    if model:
        lf["preferred_local_model"] = model.strip()
    save_prime_config(cfg)
    return get_local_status()


def run_local_prompt(prompt: str, model: str | None = None) -> str:
    """Run a prompt on Ollama (on-device). Returns text or error message."""
    cfg = load_prime_config()
    lf = cfg["local_first"]
    probe = probe_ollama()
    if not probe.get("online"):
        return "Ollama is not running. Start Ollama locally or disable local-first mode."

    use_model = model or lf.get("preferred_local_model", "llama3.2")
    base = lf.get("ollama_url", "http://127.0.0.1:11434").rstrip("/")
    payload = json.dumps({
        "model": use_model,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")
    try:
        req = urllib.request.Request(
            f"{base}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data.get("response") or "").strip() or "(empty response)"
    except Exception as e:
        return f"Local inference failed: {e}"


def docker_available() -> bool:
    try:
        r = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True, text=True, timeout=5,
        )
        return r.returncode == 0
    except Exception:
        return False
