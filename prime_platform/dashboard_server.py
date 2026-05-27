"""Advanced monitoring dashboard — energy, cost, memory, homelab (HTTP)."""
from __future__ import annotations

import concurrent.futures
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

_server: ThreadingHTTPServer | None = None
_thread: threading.Thread | None = None
_port = 18765
_API_TIMEOUT_SEC = 10.0


def _run_bounded(fn, label: str, timeout: float = _API_TIMEOUT_SEC):
    """Run blocking work (docker/ollama) without freezing the HTTP handler."""
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(fn)
            return fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        return {
            "ok": False,
            "error": (
                f"{label} timed out after {int(timeout)}s. "
                "If you do not use this feature, you can ignore it. "
                "Otherwise start Docker Desktop or Ollama and refresh."
            ),
        }
    except Exception as e:
        return {"ok": False, "error": f"{label} error: {e}"}


def _json_api(path: str) -> dict:
    if path == "/api/metrics":
        def _metrics():
            from prime_platform.energy_metrics import (
                _load_usage,
                _system_power_hint,
                get_energy_dashboard,
            )
            return {
                "usage": _load_usage(),
                "power": _system_power_hint(),
                "dashboard_text": get_energy_dashboard(),
            }
        out = _run_bounded(_metrics, "Energy metrics", timeout=6.0)
        return out if isinstance(out, dict) and "ok" in out else {"ok": True, **out}

    if path == "/api/memory":
        def _memory():
            from prime_platform.infinite_memory import get_memory_stats
            from memory.memory_manager import load_memory
            return {"stats": get_memory_stats(), "categories": list(load_memory().keys())}
        out = _run_bounded(_memory, "Memory stats", timeout=6.0)
        return out if isinstance(out, dict) and "ok" in out else {"ok": True, **out}

    if path == "/api/local":
        def _local():
            from prime_platform.local_first import probe_ollama, get_local_status
            ollama = probe_ollama(timeout=5.0)
            return {"ollama": ollama, "status_text": get_local_status(ollama)}
        out = _run_bounded(_local, "Local / Ollama", timeout=8.0)
        if isinstance(out, dict) and out.get("ok") is False:
            return {
                "ok": False,
                "error": out["error"],
                "status_text": out["error"],
                "ollama": {"online": False, "error": out["error"]},
            }
        return {"ok": True, **out}

    if path == "/api/homelab":
        def _homelab():
            from prime_platform.homelab import docker_status, list_containers
            docker = docker_status()
            if docker.startswith("Docker is not"):
                return {
                    "docker": docker,
                    "containers": "Docker not available — install/start Docker Desktop to use homelab.",
                }
            return {"docker": docker, "containers": list_containers()}
        out = _run_bounded(_homelab, "Homelab / Docker", timeout=12.0)
        if isinstance(out, dict) and out.get("ok") is False:
            return {
                "ok": False,
                "error": out["error"],
                "docker": out["error"],
                "containers": "",
            }
        return {"ok": True, **out}

    if path == "/api/gesture":
        def _gesture():
            from prime_platform.gesture_control import GestureService
            return {"status": GestureService.instance().status()}
        out = _run_bounded(_gesture, "Gesture", timeout=4.0)
        return out if isinstance(out, dict) and "ok" in out else {"ok": True, **out}

    return {"ok": False, "error": "not found"}


_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>IP Prime — Advanced Monitor</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#020810;color:#e2e8f0;min-height:100vh;padding:24px}
  h1{color:#22d3ee;font-size:1.4rem;margin-bottom:4px}
  .sub{color:#64748b;font-size:.85rem;margin-bottom:24px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
  .card{background:rgba(5,15,30,.9);border:1px solid rgba(6,182,212,.25);border-radius:12px;padding:16px}
  .card h2{font-size:.75rem;color:#06b6d4;letter-spacing:1px;margin-bottom:12px}
  pre{font-size:.72rem;line-height:1.45;white-space:pre-wrap;color:#94a3b8;max-height:320px;overflow:auto}
  .pill{display:inline-block;padding:4px 10px;border-radius:6px;font-size:.7rem;background:rgba(6,182,212,.12);border:1px solid rgba(6,182,212,.35);color:#22d3ee;margin-right:6px}
  .warn{color:#fbbf24}
</style>
</head>
<body>
<h1>IP PRIME — Advanced Monitoring</h1>
<p class="sub">Energy · API cost · Memory · Local Ollama (optional) · Docker homelab (optional)</p>
<div class="pill" id="refresh">Auto-refresh 5s</div>
<p class="sub warn" style="margin-top:8px">Local &amp; Homelab errors are normal if Ollama/Docker are not installed — cloud voice still works.</p>
<div class="grid" style="margin-top:16px">
  <div class="card"><h2>ENERGY & COST</h2><pre id="metrics">Loading…</pre></div>
  <div class="card"><h2>INFINITE MEMORY</h2><pre id="memory">Loading…</pre></div>
  <div class="card"><h2>LOCAL-FIRST (OLLAMA)</h2><pre id="local">Loading…</pre></div>
  <div class="card"><h2>HOMELAB / DOCKER</h2><pre id="homelab">Loading…</pre></div>
</div>
<script>
const FETCH_MS = 14000;
async function load(path, elId, formatter) {
  const el = document.getElementById(elId);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), FETCH_MS);
  try {
    const r = await fetch(path, { signal: ctrl.signal });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    const j = await r.json();
    if (j.ok === false && j.error) {
      el.textContent = j.error;
      return;
    }
    el.textContent = formatter(j);
  } catch (e) {
    const msg = (e.name === 'AbortError')
      ? 'Timed out — open dashboard from IP Prime (Settings → Monitor) so the server on port 18765 is running.'
      : ('Error: ' + e);
    el.textContent = msg;
  } finally {
    clearTimeout(timer);
  }
}
function refreshAll() {
  load('/api/metrics','metrics', j => j.dashboard_text || JSON.stringify(j,null,2));
  load('/api/memory','memory', j => JSON.stringify(j.stats || j, null, 2));
  load('/api/local','local', j => j.status_text || JSON.stringify(j,null,2));
  load('/api/homelab','homelab', j => (j.docker || '') + '\\n\\n' + (j.containers || ''));
}
refreshAll();
setInterval(refreshAll, 5000);
</script>
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            body = _DASHBOARD_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path.startswith("/api/"):
            data = _json_api(path)
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def start_dashboard(port: int | None = None, open_browser: bool = True) -> str:
    global _server, _thread, _port
    from prime_platform.config import load_prime_config
    cfg = load_prime_config()
    _port = port or int(cfg.get("tauri_desktop", {}).get("api_port", 18765))

    if _server:
        url = f"http://127.0.0.1:{_port}/"
        if open_browser:
            webbrowser.open(url)
        return f"Dashboard already running at {url}"

    _server = ThreadingHTTPServer(("127.0.0.1", _port), _Handler)
    _thread = threading.Thread(target=_server.serve_forever, daemon=True, name="IPPrime-Dashboard")
    _thread.start()
    url = f"http://127.0.0.1:{_port}/"
    if open_browser:
        webbrowser.open(url)
    return f"Advanced monitoring dashboard live at {url}"


def stop_dashboard() -> str:
    global _server, _thread
    if _server:
        _server.shutdown()
        _server = None
        _thread = None
        return "Dashboard server stopped."
    return "Dashboard was not running."
