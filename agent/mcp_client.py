import subprocess
import json

class MCPClient:
    """
    Model Context Protocol (MCP) Client.
    Allows IP Prime to connect to external official tool servers (e.g. Slack, GitHub).
    """
    def __init__(self):
        self.servers = {}
        print("[MCPClient] \U0001f50c MCP Client initialized. Ready to bind external servers.")

    def connect_server(self, name: str, command: str, args: list):
        """Spawns an MCP server process and connects via Stdio."""
        try:
            process = subprocess.Popen(
                [command] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.servers[name] = process
            print(f"[MCPClient] Successfully connected to MCP Server: {name}")
            return True
        except Exception as e:
            print(f"[MCPClient] Failed to connect to {name}: {e}")
            return False

    def list_tools(self, server_name: str):
        """Requests the list of available tools from the MCP server."""
        if server_name not in self.servers:
            return []
            
        process = self.servers[server_name]
        
        # Craft a standard MCP JSON-RPC payload for tools/list
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        try:
            process.stdin.write(json.dumps(req) + "\n")
            process.stdin.flush()
            
            # Read response (blocking wait for simplicity in this demo wrapper)
            response_str = process.stdout.readline()
            response = json.loads(response_str)
            
            return response.get("result", {}).get("tools", [])
        except Exception as e:
            print(f"[MCPClient] Error listing tools from {server_name}: {e}")
            return []

    def call_tool(self, server_name: str, tool_name: str, args: dict):
        """Executes a tool on the MCP server."""
        if server_name not in self.servers:
            return f"Error: MCP Server {server_name} not found."
            
        process = self.servers[server_name]
        
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args
            }
        }
        
        try:
            process.stdin.write(json.dumps(req) + "\n")
            process.stdin.flush()
            
            response_str = process.stdout.readline()
            response = json.loads(response_str)
            
            return response.get("result", "No result returned.")
        except Exception as e:
            return f"Error executing {tool_name} on {server_name}: {e}"

# Global instance
mcp_client = MCPClient()
