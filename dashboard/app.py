"""
dashboard/app.py — IP Prime Web Dashboard (FastAPI).
Access IP Prime from any browser at http://localhost:8765

Routes:
  GET  /          → Web UI
  GET  /api/stats → System stats (CPU, RAM, tasks)
  GET  /api/tasks → Background job queue
  GET  /api/memory/recent → Recent memory entries
  POST /api/chat  → Send a message to IP Prime AI
"""
from __future__ import annotations
import sys
import json
import time
import asyncio
import psutil
from pathlib import Path
from datetime import datetime

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel
    import uvicorn
    _FASTAPI_OK = True
except ImportError:
    _FASTAPI_OK = False

DASHBOARD_DIR = Path(__file__).resolve().parent
STATIC_DIR    = DASHBOARD_DIR / "static"
MEMORY_DIR    = Path("memory")


def _read_goals() -> list[dict]:
    p = MEMORY_DIR / "goals.json"
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            pass
    return []


def _read_task_queue() -> list[dict]:
    """Try to import the live queue, fallback to empty list."""
    try:
        sys.path.insert(0, str(DASHBOARD_DIR.parent))
        from core.task_queue_manager import TaskQueue
        return [j.to_dict() for j in TaskQueue.all_jobs()]
    except Exception:
        return []


def create_app() -> "FastAPI":
    if not _FASTAPI_OK:
        raise ImportError("FastAPI not installed. Run: pip install fastapi uvicorn")

    app = FastAPI(title="IP Prime Dashboard", version="1.0.0")

    # --- API Routes ---

    @app.get("/api/stats")
    def get_stats():
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "cpu_percent":  cpu,
            "ram_used_gb":  round(ram.used / 1e9, 2),
            "ram_total_gb": round(ram.total / 1e9, 2),
            "ram_percent":  ram.percent,
            "disk_used_gb": round(disk.used / 1e9, 2),
            "disk_total_gb":round(disk.total / 1e9, 2),
            "timestamp":    datetime.now().isoformat(),
        }

    @app.get("/api/tasks")
    def get_tasks():
        return {"jobs": _read_task_queue()}

    @app.get("/api/goals")
    def get_goals():
        return {"goals": _read_goals()}

    @app.get("/api/memory/recent")
    def get_memory():
        """Return last 20 memory files from memory/ dir."""
        entries = []
        if MEMORY_DIR.exists():
            for f in sorted(MEMORY_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
                try:
                    data = json.loads(f.read_text())
                    entries.append({"file": f.name, "data": data})
                except Exception:
                    entries.append({"file": f.name, "data": {}})
        return {"entries": entries}

    # --- Main UI ---
    @app.get("/", response_class=HTMLResponse)
    def root():
        html_path = STATIC_DIR / "index.html"
        if html_path.exists():
            return html_path.read_text(encoding="utf-8")
        return "<h1>IP Prime Dashboard — index.html not found</h1>"

    # WebSocket route for mobile companion app integration
    from fastapi import WebSocket, WebSocketDisconnect
    
    class ConnectionManager:
        def __init__(self):
            self.active_connections: list[WebSocket] = []

        async def connect(self, websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)

        def disconnect(self, websocket: WebSocket):
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

        async def broadcast(self, message: dict):
            for connection in self.active_connections:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    manager = ConnectionManager()

    @app.websocket("/api/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        
        # Start a background task to periodically send system stats to this client
        async def send_stats_loop():
            while True:
                try:
                    cpu = psutil.cpu_percent(interval=0.5)
                    ram = psutil.virtual_memory()
                    stats = {
                        "type": "stats",
                        "cpu_percent": cpu,
                        "ram_percent": ram.percent,
                        "timestamp": datetime.now().isoformat()
                    }
                    await websocket.send_json(stats)
                    await asyncio.sleep(2.0)
                except Exception:
                    break
                    
        stats_task = asyncio.create_task(send_stats_loop())
        
        try:
            while True:
                data = await websocket.receive_json()
                cmd_text = data.get("command", "").strip()
                if cmd_text:
                    # Route to standard IP Prime IPC json file so main process executes it
                    ipc_file = Path(r"C:\Users\thora\Downloads\output\ip_prime_ipc.json")
                    req_id = f"mobile_{int(time.time())}"
                    
                    ipc_payload = {
                        "status": "pending",
                        "command": cmd_text,
                        "request_id": req_id
                    }
                    try:
                        ipc_file.write_text(json.dumps(ipc_payload, indent=4), encoding="utf-8")
                        
                        # Wait for execution response in background, then send back
                        async def wait_for_response():
                            for _ in range(30): # 30 seconds timeout
                                await asyncio.sleep(1.0)
                                if ipc_file.exists():
                                    try:
                                        res_data = json.loads(ipc_file.read_text(encoding="utf-8"))
                                        if res_data.get("request_id") == req_id and res_data.get("status") in ("completed", "failed"):
                                            response_msg = {
                                                "type": "response",
                                                "status": res_data.get("status"),
                                                "response": res_data.get("response", ""),
                                                "error": res_data.get("error", "")
                                            }
                                            await websocket.send_json(response_msg)
                                            break
                                    except Exception:
                                        pass
                        asyncio.create_task(wait_for_response())
                    except Exception as e:
                        await websocket.send_json({"type": "response", "status": "failed", "error": str(e)})
        except WebSocketDisconnect:
            manager.disconnect(websocket)
        finally:
            stats_task.cancel()

    return app


def start_dashboard(host: str = "127.0.0.1", port: int = 8765):
    """Start the dashboard server. Call from main.py or a background thread."""
    if not _FASTAPI_OK:
        print("[Dashboard] FastAPI not installed. pip install fastapi uvicorn")
        return
    import threading
    app = create_app()
    def _run():
        uvicorn.run(app, host=host, port=port, log_level="warning")
    t = threading.Thread(target=_run, daemon=True, name="ip-dashboard")
    t.start()
    print(f"[Dashboard] 🌐 Running at http://{host}:{port}")
