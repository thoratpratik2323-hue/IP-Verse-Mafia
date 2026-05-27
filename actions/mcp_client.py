"""
mcp_client.py — Model Context Protocol client managing external tool connections.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import sys
import json
import subprocess
import threading
import queue
from pathlib import Path

class MCPServerConnection:
    def __init__(self, name: str, command: str, args: list = None, env: dict = None, player=None):
        self.name = name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.player = player
        self.process = None
        self.read_thread = None
        self.response_queues = {}
        self.running = False
        self.msg_id = 0
        self.tools = []

    def _log(self, text: str):
        msg = f"[MCP Connection - {self.name}] {text}"
        print(msg)

    def start(self) -> bool:
        try:
            cmd = [self.command] + self.args
            startup_env = os.environ.copy()
            startup_env.update(self.env)
            
            # Use shell=True on Windows to support batch files/npx/npm/etc.
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=startup_env,
                text=True,
                shell=True,
                bufsize=1
            )
            self.running = True
            
            # Start stdout reader thread
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True, name=f"MCP-{self.name}-Reader")
            self.read_thread.start()
            
            # Start stderr logger thread
            threading.Thread(target=self._error_log_loop, daemon=True, name=f"MCP-{self.name}-ErrReader").start()
            
            # Initialize handshake
            self._log("Initiating protocol handshake...")
            if self._handshake():
                self._log("Handshake successful! Retrieving tools...")
                self._load_tools()
                return True
            else:
                self._log("Handshake failed.")
                self.stop()
                return False
        except Exception as e:
            self._log(f"Failed to start subprocess: {e}")
            return False

    def _read_loop(self):
        while self.running and self.process and self.process.poll() is None:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    msg_id = data.get("id")
                    if msg_id is not None:
                        if msg_id in self.response_queues:
                            self.response_queues[msg_id].put(data)
                except Exception:
                    # Non-JSON line, ignore
                    pass
            except Exception:
                break
        self.running = False

    def _error_log_loop(self):
        while self.running and self.process and self.process.poll() is None:
            try:
                line = self.process.stderr.readline()
                if not line:
                    break
                line_str = line.strip()
                if line_str:
                    print(f"[MCP Server Error - {self.name}] {line_str}")
            except Exception:
                break

    def _send_request(self, method: str, params: dict) -> dict | None:
        if not self.running or not self.process or self.process.poll() is not None:
            self._log("Cannot send request; server process is not running.")
            return None

        self.msg_id += 1
        req_id = self.msg_id
        req = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        
        q = queue.Queue()
        self.response_queues[req_id] = q
        
        try:
            self.process.stdin.write(json.dumps(req) + "\n")
            self.process.stdin.flush()
        except Exception as e:
            self._log(f"Failed to write to stdin: {e}")
            return None

        try:
            # 15 seconds timeout
            res = q.get(timeout=15.0)
            return res
        except queue.Empty:
            self._log(f"Request timeout for method '{method}'")
            return None
        finally:
            self.response_queues.pop(req_id, None)

    def _send_notification(self, method: str, params: dict = None):
        if not self.running or not self.process:
            return
        req = {
            "jsonrpc": "2.0",
            "method": method
        }
        if params is not None:
            req["params"] = params
        try:
            self.process.stdin.write(json.dumps(req) + "\n")
            self.process.stdin.flush()
        except Exception as e:
            self._log(f"Failed to send notification: {e}")

    def _handshake(self) -> bool:
        init_params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "IP-Prime-MCP-Client",
                "version": "1.0.0"
            }
        }
        res = self._send_request("initialize", init_params)
        if res and "result" in res:
            self._send_notification("notifications/initialized")
            return True
        return False

    def _load_tools(self):
        res = self._send_request("tools/list", {})
        if res and "result" in res:
            self.tools = res["result"].get("tools", [])
            self._log(f"Successfully loaded {len(self.tools)} tools from server.")
        else:
            self.tools = []

    def call_tool(self, tool_name: str, arguments: dict) -> dict | None:
        self._log(f"Calling tool '{tool_name}' with parameters: {arguments}")
        res = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        if res and "result" in res:
            return res["result"]
        elif res and "error" in res:
            return {"content": [{"type": "text", "text": f"Error: {res['error']}"}], "isError": True}
        return None

    def stop(self):
        self.running = False
        self._log("Stopping server connection...")
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        self._log("Server connection stopped.")


class MCPClientManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(MCPClientManager, cls).__new__(cls)
                cls._instance.connections = {}
                cls._instance.player = None
                cls._instance.loaded = False
                import atexit
                atexit.register(cls._instance.shutdown)
            return cls._instance

    def initialize(self, player=None):
        self.player = player
        if self.loaded:
            return
        
        # Load config
        try:
            if getattr(sys, "frozen", False):
                base_dir = Path(sys.executable).parent
            else:
                base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / "config" / "mcp_servers.json"
            
            if not config_path.exists():
                print(f"[MCP Manager] Config file not found at: {config_path}")
                return
            
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            
            servers = cfg.get("mcpServers", {})
            for s_name, s_cfg in servers.items():
                cmd = s_cfg.get("command")
                args = s_cfg.get("args", [])
                env = s_cfg.get("env", {})
                
                if cmd:
                    conn = MCPServerConnection(s_name, cmd, args, env, player=self.player)
                    self.connections[s_name] = conn
                    # Start in background thread
                    threading.Thread(target=conn.start, daemon=True, name=f"MCP-Start-{s_name}").start()
            
            self.loaded = True
        except Exception as e:
            print(f"[MCP Manager] Error loading config: {e}")

    def get_all_tools(self) -> list:
        all_tools = []
        for s_name, conn in self.connections.items():
            if conn.running:
                for t in conn.tools:
                    # Enrich tool representation with server name to prevent name collisions
                    tool_copy = t.copy()
                    tool_copy["server_name"] = s_name
                    all_tools.append(tool_copy)
        return all_tools

    def execute_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        conn = self.connections.get(server_name)
        if not conn:
            return f"Error: MCP Server '{server_name}' is not configured or not running."
        if not conn.running:
            # Try restarting it
            conn.start()
            if not conn.running:
                return f"Error: MCP Server '{server_name}' is offline."
        
        result = conn.call_tool(tool_name, arguments)
        if not result:
            return f"Error: Tool call to '{tool_name}' failed or timed out."
        
        contents = result.get("content", [])
        text_parts = []
        for c in contents:
            if c.get("type") == "text":
                text_parts.append(c.get("text", ""))
        
        return "\n".join(text_parts) if text_parts else "Success (No text response)."

    def shutdown(self):
        for conn in self.connections.values():
            conn.stop()
        self.connections.clear()
        self.loaded = False
