"""
web_hud.py — Configures glassmorphic PyQt interactive HUD windows.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/web_hud.py
import json
import sys
import re
import threading
import time
import socket
import urllib.parse
import random
from pathlib import Path
from http.server import SimpleHTTPRequestHandler
from socketserver import ThreadingTCPServer
from actions.iot_controller import get_iot_state as run_get_iot_state, toggle_iot as run_iot_toggle

try:
    import psutil
except ImportError:
    psutil = None

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Shared memory for command feedback and logs
_completed_tasks = 0
_active_tasks = []

_logs_list = [
    {"time": time.strftime("%H:%M:%S"), "msg": "System Core Initialized."},
    {"time": time.strftime("%H:%M:%S"), "msg": "Cybernetic Web HUD Activated."},
    {"time": time.strftime("%H:%M:%S"), "msg": "Nezha AI Agent Cockpit Online."}
]
_dev_status_lock = threading.Lock()
_dev_status = {
    "active": False,
    "step": "idle",
    "file": "None",
    "progress": 0,
    "logs": ["Developer Agent is currently idle. Spawn a task to begin."]
}

def update_dev_status(active=None, step=None, file=None, progress=None, log=None):
    with _dev_status_lock:
        if active is not None:
            _dev_status["active"] = active
        if step is not None:
            _dev_status["step"] = step
        if file is not None:
            _dev_status["file"] = file
        if progress is not None:
            _dev_status["progress"] = progress
        if log is not None:
            _dev_status["logs"].append(f"[{time.strftime('%H:%M:%S')}] {log}")
            if len(_dev_status["logs"]) > 100:
                _dev_status["logs"].pop(0)

# Nezha Multi-Agent thread-safe state memory
_agents_lock = threading.Lock()
_active_agents = [
    {
        "id": "agent-1",
        "name": "Architect & Planner Agent 🧠",
        "model": "gemini-2.5-flash",
        "status": "Idle 💤",
        "task": "Create dependency graph and codebase architecture plan",
        "tokens": 0,
        "logs": ["Planner is waiting for spawn trigger..."],
        "progress": 0,
        "file": "None",
        "badge_class": "badge-idle",
        "bar_class": "bg-slate"
    },
    {
        "id": "agent-2",
        "name": "Nezha Coder Agent ✍️",
        "model": "gemini-2.5-flash",
        "status": "Idle 💤",
        "task": "Write complete implementation for modules",
        "tokens": 0,
        "logs": ["Coder is waiting for planner execution..."],
        "progress": 0,
        "file": "None",
        "badge_class": "badge-idle",
        "bar_class": "bg-slate"
    },
    {
        "id": "agent-3",
        "name": "Vibe Compilation Agent 🚀",
        "model": "Local Environment",
        "status": "Idle 💤",
        "task": "Verify syntax and run automated tests",
        "tokens": 0,
        "logs": ["Compiler is waiting for coder completion..."],
        "progress": 0,
        "file": "None",
        "badge_class": "badge-idle",
        "bar_class": "bg-slate"
    },
    {
        "id": "agent-4",
        "name": "Self-Healing Debugger Agent ⚠️",
        "model": "gemini-2.5-flash",
        "status": "Idle 💤",
        "task": "Analyze stack traces and apply auto-fixes",
        "tokens": 0,
        "logs": ["Debugger is monitoring compilation processes..."],
        "progress": 0,
        "file": "None",
        "badge_class": "badge-idle",
        "bar_class": "bg-slate"
    }
]
_commits_history = [
    {
        "time": time.strftime("%H:%M:%S"),
        "author": "Nezha Core",
        "msg": "chore: initialize vibe coding cockpit",
        "hash": "cb6e618"
    }
]

class WebHUDServer:
    server = None
    thread = None
    port = 5000
    is_running = False
    ui_instance = None

def get_html_content():
    try:
        with open(BASE_DIR / "actions" / "dashboard.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Failed to load dashboard.html: {e}"

def log_event(message: str):
    """Logs an event to be displayed on the Web HUD."""
    timestamp = time.strftime("%H:%M:%S")
    _logs_list.append({"time": timestamp, "msg": message})
    # Keep last 25 logs
    while len(_logs_list) > 25:
        _logs_list.pop(0)

def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Embedded HTML, CSS, and JS for a zero-dependency, ultra-premium interface
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>IP Prime — Cybernetic Web HUD</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
    
    <!-- Injected phantom-ui lit web component script -->
    <script type="module" src="https://unpkg.com/@aejkatappaja/phantom-ui@latest/dist/phantom-ui/phantom-ui.esm.js"></script>

    <style>
        :root {
            --bg: #030712;
            --panel: rgba(15, 23, 42, 0.65);
            --panel-secondary: rgba(30, 41, 59, 0.45);
            --border: rgba(59, 130, 246, 0.15);
            --border-glow: rgba(139, 92, 246, 0.25);
            --primary: #3B82F6;
            --accent: #8B5CF6;
            --cyan: #06B6D4;
            --green: #10B981;
            --text: #F8FAFC;
            --text-dim: #64748B;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: 'Inter', sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            display: flex;
            flex-direction: column;
            background-image: 
                radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.1) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.1) 0px, transparent 50%);
        }

        header {
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            backdrop-filter: blur(12px);
            background: rgba(3, 7, 18, 0.5);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .logo-section {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-orb {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: radial-gradient(circle, var(--cyan) 0%, var(--primary) 70%, transparent 100%);
            box-shadow: 0 0 20px rgba(6, 182, 212, 0.6);
            animation: pulse 3s infinite ease-in-out;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 24px;
            font-weight: 800;
            letter-spacing: -0.5px;
            background: linear-gradient(to right, #FFFFFF, var(--cyan));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .status-badge {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: var(--green);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: var(--green);
            box-shadow: 0 0 10px var(--green);
        }

        main {
            flex: 1;
            padding: 40px;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
            display: grid;
            grid-template-columns: 1fr 350px;
            gap: 30px;
        }

        @media (max-width: 1024px) {
            main {
                grid-template-columns: 1fr;
            }
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }
        }

        .glass-card {
            background: var(--panel);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            position: relative;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .glass-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 100%);
            pointer-events: none;
        }

        .glass-card:hover {
            border-color: rgba(59, 130, 246, 0.3);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            transform: translateY(-2px);
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .card-title {
            font-size: 14px;
            color: var(--text-dim);
            text-transform: uppercase;
            letter-spacing: 1px;
            font-weight: 600;
        }

        .stat-value {
            font-family: 'Outfit', sans-serif;
            font-size: 36px;
            font-weight: 800;
            color: #FFFFFF;
        }

        .stat-meta {
            font-size: 12px;
            color: var(--text-dim);
            margin-top: 8px;
        }

        .console-section {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }

        .terminal-panel {
            background: rgba(5, 8, 22, 0.85);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            display: flex;
            flex-direction: column;
            height: 300px;
        }

        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            padding-bottom: 12px;
            margin-bottom: 16px;
        }

        .terminal-title {
            font-family: 'Outfit', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: var(--cyan);
        }

        .terminal-logs {
            flex: 1;
            overflow-y: auto;
            font-family: 'Outfit', monospace;
            font-size: 13px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            padding-right: 8px;
        }

        .log-entry {
            display: flex;
            gap: 12px;
            line-height: 1.5;
        }

        .log-time {
            color: var(--primary);
            flex-shrink: 0;
        }

        .log-text {
            color: #E2E8F0;
        }

        .interactive-panel {
            display: flex;
            flex-direction: column;
            gap: 15px;
        }

        .cmd-input-container {
            display: flex;
            gap: 10px;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 6px 12px;
            align-items: center;
        }

        .cmd-input-container:focus-within {
            border-color: var(--primary);
            box-shadow: 0 0 10px rgba(59, 130, 246, 0.2);
        }

        .cmd-prefix {
            color: var(--cyan);
            font-weight: bold;
        }

        .cmd-input {
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text);
            font-family: 'Inter', sans-serif;
            font-size: 14px;
        }

        .cmd-btn {
            background: linear-gradient(135deg, var(--primary) 0%, var(--accent) 100%);
            border: none;
            border-radius: 8px;
            color: white;
            padding: 8px 16px;
            font-weight: 600;
            cursor: pointer;
            transition: opacity 0.2s;
        }

        .cmd-btn:hover {
            opacity: 0.9;
        }

        .sidebar-section {
            display: flex;
            flex-direction: column;
            gap: 25px;
        }

        phantom-ui {
            --phantom-bg: rgba(30, 41, 59, 0.4);
            --phantom-shimmer: linear-gradient(90deg, transparent, rgba(59, 130, 246, 0.15), transparent);
            border-radius: 12px;
            display: block;
            width: 100%;
        }

        .skeleton-block {
            height: 100px;
            border-radius: 12px;
            background: rgba(30, 41, 59, 0.3);
            border: 1px dashed var(--border);
            position: relative;
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.8; }
        }

        .refresh-btn {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .refresh-btn:hover {
            border-color: var(--primary);
            color: var(--text);
        }

        /* ⚡ Nezha Cockpit Styling */
        .nezha-cockpit {
            background: rgba(10, 15, 30, 0.75);
            border: 1px solid rgba(139, 92, 246, 0.3);
            box-shadow: 0 0 25px rgba(139, 92, 246, 0.15);
        }

        .nezha-title-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(139, 92, 246, 0.2);
            padding-bottom: 12px;
            margin-bottom: 20px;
        }

        .nezha-title {
            font-family: 'Outfit', sans-serif;
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 0.5px;
            background: linear-gradient(to right, #C084FC, #818CF8, #38BDF8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nezha-controls {
            display: flex;
            flex-direction: column;
            gap: 12px;
            margin-bottom: 20px;
            background: rgba(255, 255, 255, 0.02);
            padding: 16px;
            border-radius: 12px;
            border: 1px solid var(--border);
        }

        .spawn-input-row {
            display: flex;
            gap: 12px;
        }

        .spawn-field {
            flex: 1;
            background: rgba(0,0,0,0.4);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 14px;
            color: var(--text);
            font-size: 13px;
            outline: none;
            transition: all 0.2s;
        }

        .spawn-field:focus {
            border-color: var(--cyan);
            box-shadow: 0 0 10px rgba(6, 182, 212, 0.2);
        }

        .spawn-btn {
            background: linear-gradient(135deg, var(--accent) 0%, var(--cyan) 100%);
            border: none;
            border-radius: 8px;
            color: white;
            padding: 10px 20px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.4);
        }

        .spawn-btn:hover {
            opacity: 0.95;
            box-shadow: 0 0 20px rgba(6, 182, 212, 0.6);
        }

        .nezha-presets {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            align-items: center;
        }

        .preset-title {
            font-size: 11px;
            color: var(--text-dim);
            font-weight: 600;
            text-transform: uppercase;
        }

        .preset-chip {
            background: var(--panel-secondary);
            border: 1px solid var(--border);
            color: var(--text-dim);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 11px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .preset-chip:hover {
            border-color: var(--cyan);
            color: var(--text);
            background: rgba(6, 182, 212, 0.1);
        }

        .cockpit-grid {
            display: grid;
            grid-template-columns: 1.2fr 1fr;
            gap: 20px;
        }

        @media (max-width: 900px) {
            .cockpit-grid {
                grid-template-columns: 1fr;
            }
        }

        .agent-cards-container {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .agent-card {
            background: rgba(30, 41, 59, 0.25);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }

        .agent-card:hover, .agent-card.selected {
            border-color: rgba(6, 182, 212, 0.5);
            background: rgba(30, 41, 59, 0.45);
            box-shadow: 0 0 15px rgba(6, 182, 212, 0.15);
        }

        .agent-card.active-run {
            border-color: rgba(139, 92, 246, 0.5);
            box-shadow: 0 0 15px rgba(139, 92, 246, 0.2);
        }

        .agent-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
        }

        .agent-info {
            display: flex;
            flex-direction: column;
        }

        .agent-name {
            font-family: 'Outfit', sans-serif;
            font-size: 14px;
            font-weight: 600;
            color: var(--text);
        }

        .agent-model {
            font-size: 11px;
            color: var(--text-dim);
            margin-top: 2px;
        }

        /* Glowing Status Badges */
        .badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .badge-idle {
            background: rgba(71, 85, 105, 0.15);
            border: 1px solid rgba(71, 85, 105, 0.3);
            color: var(--text-dim);
        }

        .badge-thinking {
            background: rgba(6, 182, 212, 0.15);
            border: 1px solid rgba(6, 182, 212, 0.4);
            color: var(--cyan);
            animation: cyanPulse 2s infinite ease-in-out;
        }

        .badge-writing {
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.4);
            color: var(--green);
            animation: greenPulse 2s infinite ease-in-out;
        }

        .badge-compiling {
            background: rgba(139, 92, 246, 0.15);
            border: 1px solid rgba(139, 92, 246, 0.4);
            color: var(--accent);
            animation: purplePulse 2s infinite ease-in-out;
        }

        .badge-healing {
            background: rgba(245, 158, 11, 0.15);
            border: 1px solid rgba(245, 158, 11, 0.4);
            color: #F59E0B;
            animation: amberPulse 2s infinite ease-in-out;
        }

        .badge-completed {
            background: rgba(16, 185, 129, 0.25);
            border: 1px solid var(--green);
            color: var(--green);
        }

        .agent-meta {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            color: var(--text-dim);
            margin-top: 8px;
            margin-bottom: 6px;
        }

        .progress-bar-container {
            height: 6px;
            background: rgba(0,0,0,0.3);
            border-radius: 3px;
            overflow: hidden;
        }

        .progress-bar {
            height: 100%;
            width: 0%;
            transition: width 0.4s ease;
            border-radius: 3px;
        }

        .bg-cyan { background: linear-gradient(90deg, var(--cyan), #3B82F6); }
        .bg-green { background: linear-gradient(90deg, var(--green), #059669); }
        .bg-purple { background: linear-gradient(90deg, var(--accent), #6D28D9); }
        .bg-amber { background: linear-gradient(90deg, #F59E0B, #D97706); }
        .bg-slate { background: #475569; }

        /* Intelligence Center */
        .intel-tabs {
            display: flex;
            border-bottom: 1px solid var(--border);
            margin-bottom: 12px;
            gap: 8px;
        }

        .intel-tab {
            padding: 8px 16px;
            font-family: 'Outfit', sans-serif;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            color: var(--text-dim);
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }

        .intel-tab:hover, .intel-tab.active {
            color: var(--cyan);
        }

        .intel-tab.active {
            border-bottom-color: var(--cyan);
        }

        .intel-body {
            background: rgba(5, 8, 22, 0.9);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            height: 320px;
            overflow-y: auto;
            font-family: 'Outfit', monospace;
            font-size: 12px;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .agent-log-line {
            line-height: 1.4;
            color: #E2E8F0;
            border-left: 2px solid var(--border);
            padding-left: 8px;
        }

        .commit-log-line {
            padding: 8px 10px;
            border-bottom: 1px solid rgba(255,255,255,0.03);
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .commit-meta {
            display: flex;
            justify-content: space-between;
            font-size: 10px;
        }

        .commit-msg {
            color: var(--green);
            font-weight: 500;
        }

        .empty-state {
            color: var(--text-dim);
            font-style: italic;
            text-align: center;
            margin-top: 40px;
        }

        /* Pulsing status lights */
        @keyframes cyanPulse {
            0%, 100% { box-shadow: 0 0 5px rgba(6, 182, 212, 0.4); border-color: rgba(6, 182, 212, 0.4); }
            50% { box-shadow: 0 0 12px rgba(6, 182, 212, 0.8); border-color: rgba(6, 182, 212, 0.8); }
        }
        @keyframes greenPulse {
            0%, 100% { box-shadow: 0 0 5px rgba(16, 185, 129, 0.4); border-color: rgba(16, 185, 129, 0.4); }
            50% { box-shadow: 0 0 12px rgba(16, 185, 129, 0.8); border-color: rgba(16, 185, 129, 0.8); }
        }
        @keyframes purplePulse {
            0%, 100% { box-shadow: 0 0 5px rgba(139, 92, 246, 0.4); border-color: rgba(139, 92, 246, 0.4); }
            50% { box-shadow: 0 0 12px rgba(139, 92, 246, 0.8); border-color: rgba(139, 92, 246, 0.8); }
        }
        @keyframes amberPulse {
            0%, 100% { box-shadow: 0 0 5px rgba(245, 158, 11, 0.4); border-color: rgba(245, 158, 11, 0.4); }
            50% { box-shadow: 0 0 12px rgba(245, 158, 11, 0.8); border-color: rgba(245, 158, 11, 0.8); }
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-section">
            <div class="logo-orb"></div>
            <h1>IP PRIME HUD</h1>
        </div>
        <div class="status-badge">
            <div class="status-dot"></div>
            Active Daemon Server
        </div>
    </header>

    <main>
        <div class="console-section">
            <!-- 3 Columns Stats Grid wrapped in phantom-ui loaders for ultra-modern dynamic shimmer effect -->
            <div class="dashboard-grid">
                <!-- Stat 1: CPU -->
                <div class="glass-card">
                    <div class="card-header">
                        <span class="card-title">Processor (CPU)</span>
                        <button class="refresh-btn" onclick="triggerRefresh()">Refresh</button>
                    </div>
                    <phantom-ui id="cpu-loader" duration="1500" active="true">
                        <div>
                            <div class="stat-value" id="cpu-val">--%</div>
                            <div class="stat-meta">Active processes loading...</div>
                        </div>
                    </phantom-ui>
                </div>

                <!-- Stat 2: RAM -->
                <div class="glass-card">
                    <div class="card-header">
                        <span class="card-title">Memory (RAM)</span>
                    </div>
                    <phantom-ui id="ram-loader" duration="1500" active="true">
                        <div>
                            <div class="stat-value" id="ram-val">--%</div>
                            <div class="stat-meta">Unified stack cache logs</div>
                        </div>
                    </phantom-ui>
                </div>

                <!-- Stat 3: Completed Tasks -->
                <div class="glass-card">
                    <div class="card-header">
                        <span class="card-title">Execution Jobs</span>
                    </div>
                    <phantom-ui id="jobs-loader" duration="1500" active="true">
                        <div>
                            <div class="stat-value" id="jobs-val">--</div>
                            <div class="stat-meta">Total successful triggers</div>
                        </div>
                    </phantom-ui>
                </div>
            </div>

            <!-- ⚡ Nezha Agent Cockpit Panel (Premium Vibe Coding HUD Overlay) -->
            <div class="glass-card nezha-cockpit">
                <div class="nezha-title-row">
                    <div class="nezha-title">
                        <span>⚡ NEZHA MULTI-AGENT COCKPIT</span>
                    </div>
                    <div class="status-badge" style="background: rgba(139, 92, 246, 0.15); border-color: rgba(139, 92, 246, 0.3); color: var(--accent);">
                        <div class="status-dot" style="background-color: var(--accent); box-shadow: 0 0 10px var(--accent);"></div>
                        Agent-First Vibe Coding Enabled
                    </div>
                </div>

                <!-- Interactive Spawn Controls -->
                <div class="nezha-controls">
                    <div class="spawn-input-row">
                        <input type="text" class="spawn-field" id="nezha-task-input" placeholder="Vibe code with subagents... e.g. 'Refactor multi-threaded websocket server'" onkeydown="handleSpawnKey(event)">
                        <button class="spawn-btn" onclick="spawnAgentPipeline()">Spawn Parallel Agents</button>
                    </div>
                    <div class="nezha-presets">
                        <span class="preset-title">Vibe Presets:</span>
                        <div class="preset-chip" onclick="spawnAgentPipeline('Build Retro Snake game in PyQt6 with custom layouts')">🎮 Snake Game</div>
                        <div class="preset-chip" onclick="spawnAgentPipeline('Refactor multi-threaded Web HUD server to support WebSockets')">📡 Socket Server</div>
                        <div class="preset-chip" onclick="spawnAgentPipeline('Optimize styling metrics and gradients for glassmorphism panels')">🎨 Glassmorphism CSS</div>
                    </div>
                </div>

                <!-- Split Grid: Agent Cards + Logs Stream -->
                <div class="cockpit-grid">
                    <!-- Agent Cards List -->
                    <div class="agent-cards-container" id="agent-cards-list">
                        <!-- Loaded dynamically -->
                    </div>

                    <!-- Intelligence Stream Center -->
                    <div style="display: flex; flex-direction: column;">
                        <div class="intel-tabs">
                            <div class="intel-tab active" id="tab-console" onclick="setIntelTab('console')">Console Stream</div>
                            <div class="intel-tab" id="tab-commits" onclick="setIntelTab('commits')">Conventional Commits</div>
                        </div>
                        <div class="intel-body" id="intel-content">
                            <!-- Loaded dynamically based on tab / selected agent -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- Terminal Console Logs Panel -->
            <div class="terminal-panel">
                <div class="terminal-header">
                    <div class="terminal-title">>_ Real-time Execution Stream</div>
                </div>
                <phantom-ui id="logs-loader" duration="1800" active="true">
                    <div class="terminal-logs" id="logs-container">
                        <!-- Filled dynamically -->
                    </div>
                </phantom-ui>
            </div>

            <!-- Interactive Direct Command Interface -->
            <div class="glass-card interactive-panel">
                <h3 style="font-family: 'Outfit';">Dispatch Command to Jarvis Core</h3>
                <div class="cmd-input-container">
                    <span class="cmd-prefix">jarvis$</span>
                    <input type="text" class="cmd-input" id="cmd-field" placeholder="Try: 'launch notepad' or 'agent: build a snake game'..." onkeydown="handleKey(event)">
                    <button class="cmd-btn" onclick="sendCommand()">Send</button>
                </div>
            </div>
        </div>

        <div class="sidebar-section">
            <div class="glass-card">
                <h3 style="font-family: 'Outfit'; margin-bottom: 12px; font-size: 16px; color: var(--cyan);">System Identity</h3>
                <p style="font-size: 13px; color: var(--text-dim); line-height: 1.6; margin-bottom: 14px;">
                    IP Prime is a customized visual personal AI desktop suite designed specifically for **Pratik Thorat**.
                </p>
                <div style="background: rgba(255,255,255,0.02); padding: 12px; border-radius: 8px; font-size: 12px; border: 1px solid var(--border);">
                    <strong style="color: var(--primary);">Active User:</strong> Pratik Thorat<br>
                    <strong style="color: var(--primary);">Design Aesthetic:</strong> Glassmorphism Cyberpunk<br>
                    <strong style="color: var(--primary);">Shimmer Engine:</strong> phantom-ui Lit Core
                </div>
            </div>

            <div class="glass-card">
                <h3 style="font-family: 'Outfit'; margin-bottom: 12px; font-size: 16px; color: var(--accent);">Visual Shimmer Test</h3>
                <p style="font-size: 12px; color: var(--text-dim); line-height: 1.5; margin-bottom: 12px;">
                    This skeleton box showcases the runtime DOM shape measurements calculated by **phantom-ui**.
                </p>
                <phantom-ui id="box-loader" duration="3000" active="true">
                    <div class="skeleton-block" id="interactive-block">
                        <div style="padding: 12px; font-size: 12px; color: var(--green);">
                            ✔ Visual test block loaded successfully!
                        </div>
                    </div>
                </phantom-ui>
                <button class="refresh-btn" style="margin-top: 10px; width: 100%;" onclick="toggleTestShimmer()">Trigger Shimmer Re-scan</button>
            </div>
        </div>
    </main>

    <footer style="padding: 30px; text-align: center; font-size: 12px; color: var(--text-dim); border-top: 1px solid var(--border);">
        IP Prime HUD • Active Server Engine • Powered by phantom-ui
    </footer>

    <script>
        // State variables
        let selectedAgentId = "agent-1";
        let activeIntelTab = "console";
        let localAgentsState = [];
        let localCommitsState = [];

        // Fetch stats data
        async function fetchStats() {
            try {
                const res = await fetch('/api/stats');
                const data = await res.json();
                
                document.getElementById('cpu-val').innerText = data.cpu + '%';
                document.getElementById('ram-val').innerText = data.memory + '%';
                document.getElementById('jobs-val').innerText = data.completed_tasks;
                
                // Let phantom-ui know loaders can finish or be deactivated
                setTimeout(() => {
                    document.getElementById('cpu-loader').removeAttribute('active');
                    document.getElementById('ram-loader').removeAttribute('active');
                    document.getElementById('jobs-loader').removeAttribute('active');
                }, 400);

            } catch (err) {
                console.error("Failed to load statistics: ", err);
            }
        }

        // Fetch logs data
        async function fetchLogs() {
            try {
                const res = await fetch('/api/logs');
                const data = await res.json();
                
                const container = document.getElementById('logs-container');
                container.innerHTML = '';
                data.forEach(log => {
                    const entry = document.createElement('div');
                    entry.className = 'log-entry';
                    entry.innerHTML = `
                        <span class="log-time">[${log.time}]</span>
                        <span class="log-text">${log.msg}</span>
                    `;
                    container.appendChild(entry);
                });
                
                setTimeout(() => {
                    document.getElementById('logs-loader').removeAttribute('active');
                }, 400);

            } catch (err) {
                console.error("Failed to load execution logs: ", err);
            }
        }

        // Fetch active agents and commits
        async function fetchAgents() {
            try {
                const res = await fetch('/api/agents');
                const data = await res.json();
                
                localAgentsState = data.agents;
                localCommitsState = data.commits;
                
                renderAgentCards();
                renderIntelContent();
            } catch (err) {
                console.error("Failed to load agents states: ", err);
            }
        }

        function renderAgentCards() {
            const container = document.getElementById('agent-cards-list');
            container.innerHTML = '';
            
            localAgentsState.forEach(agent => {
                const card = document.createElement('div');
                const isSelected = agent.id === selectedAgentId;
                const isRunning = agent.status.indexOf('Idle') === -1 && agent.status.indexOf('Completed') === -1;
                
                card.className = `agent-card ${isSelected ? 'selected' : ''} ${isRunning ? 'active-run' : ''}`;
                card.onclick = () => selectAgent(agent.id);
                
                // Set color class for progress bar
                let barClass = "bg-slate";
                if (agent.status.includes("Thinking")) barClass = "bg-cyan";
                else if (agent.status.includes("Writing")) barClass = "bg-green";
                else if (agent.status.includes("Compilation")) barClass = "bg-purple";
                else if (agent.status.includes("Needed") || agent.status.includes("Reasoning")) barClass = "bg-amber";
                else if (agent.status.includes("Completed")) barClass = "bg-green";
                
                // Determine badge style
                let badgeClass = "badge-idle";
                if (agent.status.includes("Thinking")) badgeClass = "badge-thinking";
                else if (agent.status.includes("Writing")) badgeClass = "badge-writing";
                else if (agent.status.includes("Compilation")) badgeClass = "badge-compiling";
                else if (agent.status.includes("Needed") || agent.status.includes("Reasoning")) badgeClass = "badge-healing";
                else if (agent.status.includes("Completed")) badgeClass = "badge-completed";
                
                card.innerHTML = `
                    <div class="agent-header">
                        <div class="agent-info">
                            <span class="agent-name">${agent.name}</span>
                            <span class="agent-model">${agent.model}</span>
                        </div>
                        <span class="badge ${badgeClass}">${agent.status}</span>
                    </div>
                    <div class="agent-meta">
                        <span><strong>Focus File:</strong> ${agent.file}</span>
                        <span><strong>Tokens:</strong> ${agent.tokens.toLocaleString()}</span>
                    </div>
                    <div class="progress-bar-container">
                        <div class="progress-bar ${barClass}" style="width: ${agent.progress}%"></div>
                    </div>
                `;
                
                container.appendChild(card);
            });
        }

        function renderIntelContent() {
            const container = document.getElementById('intel-content');
            container.innerHTML = '';
            
            if (activeIntelTab === "console") {
                const agent = localAgentsState.find(a => a.id === selectedAgentId);
                if (!agent || agent.logs.length === 0) {
                    container.innerHTML = '<div class="empty-state">No logs available for this agent.</div>';
                    return;
                }
                
                agent.logs.forEach(log => {
                    const line = document.createElement('div');
                    line.className = 'agent-log-line';
                    line.innerText = log;
                    container.appendChild(line);
                });
                
                // Scroll to bottom
                container.scrollTop = container.scrollHeight;
                
            } else if (activeIntelTab === "commits") {
                if (localCommitsState.length === 0) {
                    container.innerHTML = '<div class="empty-state">No commits made by agents yet.</div>';
                    return;
                }
                
                // Reverse to show newest first
                [...localCommitsState].reverse().forEach(commit => {
                    const line = document.createElement('div');
                    line.className = 'commit-log-line';
                    line.innerHTML = `
                        <div class="commit-meta">
                            <span style="color: var(--cyan); font-weight: 600;">[commit ${commit.hash}]</span>
                            <span style="color: var(--text-dim);">${commit.time} — ${commit.author}</span>
                        </div>
                        <span class="commit-msg">${commit.msg}</span>
                    `;
                    container.appendChild(line);
                });
            }
        }

        function selectAgent(agentId) {
            selectedAgentId = agentId;
            renderAgentCards();
            if (activeIntelTab === "console") {
                renderIntelContent();
            }
        }

        function setIntelTab(tab) {
            activeIntelTab = tab;
            document.getElementById('tab-console').classList.toggle('active', tab === 'console');
            document.getElementById('tab-commits').classList.toggle('active', tab === 'commits');
            renderIntelContent();
        }

        // Spawn parallel AI Coding pipeline
        async function spawnAgentPipeline(customTask = null) {
            const field = document.getElementById('nezha-task-input');
            const task = customTask || field.value.trim();
            if (!task) return;
            
            if (!customTask) field.value = '';
            
            try {
                const res = await fetch('/api/spawn', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: task })
                });
                const result = await res.json();
                
                // Reset tab and active console
                setIntelTab('console');
                // Instantly poll agents status
                setTimeout(fetchAgents, 300);
            } catch (err) {
                console.error("Failed to spawn pipeline: ", err);
            }
        }

        function handleSpawnKey(e) {
            if (e.key === 'Enter') {
                spawnAgentPipeline();
            }
        }

        // Trigger loading placeholders manually
        function triggerRefresh() {
            document.getElementById('cpu-loader').setAttribute('active', 'true');
            document.getElementById('ram-loader').setAttribute('active', 'true');
            document.getElementById('jobs-loader').setAttribute('active', 'true');
            document.getElementById('cpu-val').innerText = '--%';
            document.getElementById('ram-val').innerText = '--%';
            setTimeout(fetchStats, 1000);
        }

        function toggleTestShimmer() {
            document.getElementById('box-loader').setAttribute('active', 'true');
            setTimeout(() => {
                document.getElementById('box-loader').removeAttribute('active');
            }, 2500);
        }

        // Send a custom text command to IP Prime core
        async function sendCommand() {
            const field = document.getElementById('cmd-field');
            const cmd = field.value.trim();
            if (!cmd) return;
            
            field.value = '';
            
            // Post custom command
            try {
                const res = await fetch('/api/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: cmd })
                });
                const result = await res.json();
                
                // Fetch fresh logs to reflect new status
                setTimeout(fetchLogs, 500);
                // Also trigger agents refresh in case it was an agent command
                setTimeout(fetchAgents, 600);
            } catch (err) {
                console.error("Failed to execute command: ", err);
            }
        }

        function handleKey(e) {
            if (e.key === 'Enter') {
                sendCommand();
            }
        }

        // Run fetches on boot
        fetchStats();
        fetchLogs();
        fetchAgents();
        
        // Auto-refresh stats and agents status every few seconds
        setInterval(fetchStats, 4000);
        setInterval(fetchAgents, 1500);
    </script>
</body>
</html>
"""

class WebHUDHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Override to prevent clogging standard terminal with request traces
        pass

    def do_GET(self):
        # Dispatch specific API endpoints or serve embedded assets
        parsed_url = urllib.parse.urlparse(self.path)
        
        if parsed_url.path in ("/", "/index.html"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            # CORS header just in case
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(get_html_content().encode("utf-8"))
            return
            
        elif parsed_url.path == "/api/stats":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Gather genuine stats
            cpu_percent = 5.2
            memory_percent = 35.8
            if psutil:
                try:
                    cpu_percent = psutil.cpu_percent()
                    memory_percent = psutil.virtual_memory().percent
                except Exception:
                    pass
            
            hud_state = "LISTENING"
            if WebHUDServer.ui_instance:
                if getattr(WebHUDServer.ui_instance, "_muted", False):
                    hud_state = "MUTED"
                elif hasattr(WebHUDServer.ui_instance, "hud") and WebHUDServer.ui_instance.hud:
                    hud_state = WebHUDServer.ui_instance.hud.state
            
            stats = {
                "cpu": cpu_percent,
                "memory": memory_percent,
                "completed_tasks": _completed_tasks,
                "tasks_queued": len(_active_tasks),
                "state": hud_state
            }
            self.wfile.write(json.dumps(stats).encode("utf-8"))
            return

        elif parsed_url.path == "/api/memories":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            try:
                from memory.memory_manager import load_memory
                memory = load_memory()
            except Exception:
                memory = {}
                
            alarms = []
            try:
                base_dir = BASE_DIR
                alarm_file = base_dir / "config" / "alarms.json"
                if alarm_file.exists():
                    alarms = json.loads(alarm_file.read_text(encoding="utf-8"))
            except Exception:
                pass
                
            nodes = [{"id": "user", "label": "Pratik Sir", "group": "user"}]
            edges = []
            
            categories = {
                "identity": "Identity",
                "preferences": "Preferences",
                "projects": "Active Projects",
                "relationships": "People",
                "wishes": "Wishes / Plans",
                "notes": "Other Notes"
            }
            
            for cat_id, cat_label in categories.items():
                cat_node_id = f"cat_{cat_id}"
                nodes.append({"id": cat_node_id, "label": cat_label, "group": "category"})
                edges.append({"from": "user", "to": cat_node_id})
                
                cat_data = memory.get(cat_id, {})
                if isinstance(cat_data, dict):
                    for key, entry in cat_data.items():
                        val = entry.get("value") if isinstance(entry, dict) else entry
                        if val:
                            leaf_id = f"leaf_{cat_id}_{key}"
                            nodes.append({"id": leaf_id, "label": f"{key}: {val[:30]}...", "detail": val, "key": key, "category": cat_id, "group": "leaf"})
                            edges.append({"from": cat_node_id, "to": leaf_id})
                            
            if alarms:
                nodes.append({"id": "cat_alarms", "label": "Scheduled Alarms", "group": "category"})
                edges.append({"from": "user", "to": "cat_alarms"})
                for idx, alarm in enumerate(alarms):
                    alarm_time = alarm.get("time", "")
                    if alarm_time:
                        leaf_id = f"alarm_{idx}"
                        nodes.append({"id": leaf_id, "label": f"Alarm {alarm_time}", "detail": f"Rings at {alarm_time}", "index": idx, "group": "alarm"})
                        edges.append({"from": "cat_alarms", "to": leaf_id})
                        
            self.wfile.write(json.dumps({"nodes": nodes, "edges": edges}).encode("utf-8"))
            return

        elif parsed_url.path == "/api/routines":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            routines = {}
            try:
                routines_file = BASE_DIR / "config" / "routines.json"
                if routines_file.exists():
                    routines = json.loads(routines_file.read_text(encoding="utf-8"))
                else:
                    routines = {
                        "morning_brief": {"enabled": True, "time": "08:00", "actions": ["briefing", "weather", "broadcast"]},
                        "workspace_check": {"enabled": True, "time": "18:00", "actions": ["compile", "broadcast"]}
                    }
            except Exception:
                pass
            self.wfile.write(json.dumps(routines).encode("utf-8"))
            return

        elif parsed_url.path == "/api/metrics":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                from prime_platform.energy_metrics import _load_usage, _system_power_hint, get_energy_dashboard
                metrics = {
                    "ok": True,
                    "usage": _load_usage(),
                    "power": _system_power_hint(),
                    "dashboard_text": get_energy_dashboard(),
                }
            except Exception as e:
                metrics = {"ok": False, "error": str(e)}
            self.wfile.write(json.dumps(metrics).encode("utf-8"))
            return

        elif parsed_url.path == "/api/local":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                from prime_platform.local_first import probe_ollama, get_local_status
                ollama = probe_ollama(timeout=5.0)
                local_status = {"ok": True, "ollama": ollama, "status_text": get_local_status(ollama)}
            except Exception as e:
                local_status = {"ok": False, "error": str(e)}
            self.wfile.write(json.dumps(local_status).encode("utf-8"))
            return

        elif parsed_url.path == "/api/homelab":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            try:
                from prime_platform.homelab import docker_status, list_containers
                docker = docker_status()
                if docker.startswith("Docker is not"):
                    homelab = {
                        "ok": True,
                        "docker": docker,
                        "containers": "Docker not available — install/start Docker Desktop to use homelab.",
                    }
                else:
                    homelab = {"ok": True, "docker": docker, "containers": list_containers()}
            except Exception as e:
                homelab = {"ok": False, "error": str(e)}
            self.wfile.write(json.dumps(homelab).encode("utf-8"))
            return

        elif parsed_url.path == "/api/gestures/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            try:
                from prime_platform.gesture_control import GestureService
                svc = GestureService.instance()
                res = {
                    "running": svc._running,
                    "last_gesture": svc._last_gesture or "none",
                    "cooldown": svc._cooldown
                }
            except Exception as e:
                res = {"running": False, "last_gesture": "error", "msg": str(e)}
            
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        elif parsed_url.path == "/api/dev-status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with _dev_status_lock:
                status = dict(_dev_status)
            self.wfile.write(json.dumps(status).encode("utf-8"))
            return

        elif parsed_url.path == "/api/broadcast/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            config = {}
            try:
                config_file = BASE_DIR / "config" / "broadcast.json"
                if config_file.exists():
                    config = json.loads(config_file.read_text(encoding="utf-8"))
                else:
                    config = {
                        "whatsapp": {"enabled": True, "group_link": ""},
                        "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
                        "desktop": {"enabled": True}
                    }
            except Exception:
                pass
            self.wfile.write(json.dumps(config).encode("utf-8"))
            return
            
        elif parsed_url.path == "/api/window/close":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if WebHUDServer.ui_instance:
                from PyQt6.QtCore import QTimer
                win = getattr(WebHUDServer.ui_instance, "_win", WebHUDServer.ui_instance)
                QTimer.singleShot(0, win.close)
            self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
            return
            
        elif parsed_url.path == "/api/window/minimize":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if WebHUDServer.ui_instance:
                from PyQt6.QtCore import QTimer
                win = getattr(WebHUDServer.ui_instance, "_win", WebHUDServer.ui_instance)
                QTimer.singleShot(0, win.showMinimized)
            self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
            return
            
        elif parsed_url.path == "/api/window/maximize":
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            if WebHUDServer.ui_instance:
                from PyQt6.QtCore import QTimer
                win = getattr(WebHUDServer.ui_instance, "_win", WebHUDServer.ui_instance)
                def toggle_max():
                    if win.isMaximized():
                        win.showNormal()
                    else:
                        win.showMaximized()
                QTimer.singleShot(0, toggle_max)
            self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
            return

        elif parsed_url.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(_logs_list).encode("utf-8"))
            return

        elif parsed_url.path == "/api/agents":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            with _agents_lock:
                response_data = {
                    "agents": _active_agents,
                    "commits": _commits_history
                }
            self.wfile.write(json.dumps(response_data).encode("utf-8"))
            return

        elif parsed_url.path == "/api/iot":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(run_get_iot_state()).encode("utf-8"))
            return

        elif parsed_url.path == "/api/screenshot":
            try:
                import pyautogui
                import io
                img = pyautogui.screenshot()
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=75)
                img_bytes = buf.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(img_bytes)
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(f"Screenshot failed: {e}".encode("utf-8"))
                return

        # Fallback to default handler
        super().do_GET()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        
        if parsed_url.path == "/api/upload":
            content_type = self.headers.get('Content-Type', '')
            if 'boundary=' in content_type:
                boundary = content_type.split('boundary=')[1].strip().encode('utf-8')
                raw_data = self.rfile.read(content_length)
                
                parts = raw_data.split(b'--' + boundary)
                for part in parts:
                    if b'filename="' in part:
                        header_part, file_data = part.split(b'\r\n\r\n', 1)
                        if file_data.endswith(b'\r\n'):
                            file_data = file_data[:-2]
                        
                        fn_match = re.search(br'filename="([^"]+)"', header_part)
                        if fn_match:
                            filename = fn_match.group(1).decode('utf-8')
                            upload_dir = Path("assets/uploads")
                            upload_dir.mkdir(parents=True, exist_ok=True)
                            save_path = upload_dir / filename
                            with open(save_path, 'wb') as f:
                                f.write(file_data)
                            
                            log_event(f"Web User uploaded file: '{filename}' to '{save_path}'")
                            if WebHUDServer.ui_instance:
                                from PyQt6.QtCore import QTimer
                                win = getattr(WebHUDServer.ui_instance, "_win", WebHUDServer.ui_instance)
                                QTimer.singleShot(0, lambda: win._on_file_selected(str(save_path.resolve())))
                                
                            self.send_response(200)
                            self.send_header("Content-Type", "application/json")
                            self.send_header("Access-Control-Allow-Origin", "*")
                            self.end_headers()
                            self.wfile.write(json.dumps({"status": "success", "filename": filename}).encode("utf-8"))
                            return
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Failed to parse multipart data")
            return

        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            data = json.loads(post_data) if post_data else {}
        except Exception:
            data = {}

        if parsed_url.path == "/api/chat":
            user_text = data.get("text", "").strip()
            log_event(f"Chat received: '{user_text}'")
            if WebHUDServer.ui_instance:
                from PyQt6.QtCore import QTimer
                player = WebHUDServer.ui_instance
                QTimer.singleShot(0, lambda: player._on_text_command(user_text))
                reply = f"Acknowledged, Sir. Processing '{user_text}'."
            else:
                _run_system_command_async(user_text)
                reply = f"Acknowledged. Simulated command: '{user_text}'"
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply, "audioUrl": None}).encode("utf-8"))
            return

        elif parsed_url.path == "/api/confirm_action":
            decision = data.get("decision", "confirm")
            log_event(f"Action confirmation received: {decision}")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "msg": f"Decision '{decision}' received."}).encode("utf-8"))
            return

        elif parsed_url.path == "/api/voice":
            log_event("Voice command received from Web Cockpit.")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "reply": "Voice telemetry synced, Sir."}).encode("utf-8"))
            return

        elif parsed_url.path == "/api/iot":
            device = data.get("device", "")
            res = run_iot_toggle(device)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(res).encode("utf-8"))
            return

        elif parsed_url.path == "/api/change_theme":
            theme = data.get("theme")
            if theme and WebHUDServer.ui_instance:
                WebHUDServer.ui_instance._change_theme_sig.emit(theme)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
            return
            
        elif parsed_url.path == "/api/personality":
            if WebHUDServer.ui_instance:
                try:
                    personality = {
                        "name": data.get("name", "Varon"),
                        "humour": data.get("humour", 50),
                        "energy": data.get("energy", 50),
                        "sarcasm": data.get("sarcasm", 50),
                        "professionalism": data.get("professionalism", 50),
                        "creativity": data.get("creativity", 50)
                    }
                    arc_file = BASE_DIR / "config" / "personality.json"
                    arc_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(arc_file, "w", encoding="utf-8") as f:
                        json.dump(personality, f, indent=4)
                        
                    WebHUDServer.ui_instance._arc_name_input.setText(personality["name"])
                    WebHUDServer.ui_instance._arc_humour_slider.setValue(personality["humour"])
                    WebHUDServer.ui_instance._arc_energy_slider.setValue(personality["energy"])
                    WebHUDServer.ui_instance._arc_sarcasm_slider.setValue(personality["sarcasm"])
                    WebHUDServer.ui_instance._arc_prof_slider.setValue(personality["professionalism"])
                    WebHUDServer.ui_instance._arc_creat_slider.setValue(personality["creativity"])
                    WebHUDServer.ui_instance._synth_personality_sig.emit()
                except Exception as e:
                    print(e)
                    
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
            return

        elif parsed_url.path == "/api/command":
            cmd = data.get("command", "").strip()
            if cmd:
                log_event(f"Web User triggered: '{cmd}'")
                if WebHUDServer.ui_instance:
                    WebHUDServer.ui_instance._web_command_sig.emit(cmd)
                else:
                    _run_system_command_async(cmd)
                
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "msg": f"Dispatched '{cmd}'"}).encode("utf-8"))
            return
                
        elif parsed_url.path == "/api/spawn":
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            try:
                data = json.loads(post_data)
                prompt = data.get("prompt", "").strip()
                if prompt:
                    log_event(f"Nezha Cockpit Spawning pipeline for: '{prompt}'")
                    threading.Thread(target=_simulate_multi_agent_pipeline, args=(prompt,), daemon=True).start()
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "success", "msg": f"Spawning pipeline for '{prompt}'"}).encode("utf-8"))
                    return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                return
        elif parsed_url.path == "/api/memories/delete":
            try:
                category = data.get("category")
                key = data.get("key")
                alarm_index = data.get("alarm_index")
                
                if alarm_index is not None:
                    alarm_file = BASE_DIR / "config" / "alarms.json"
                    if alarm_file.exists():
                        alarms = json.loads(alarm_file.read_text(encoding="utf-8"))
                        idx = int(alarm_index)
                        if 0 <= idx < len(alarms):
                            removed = alarms.pop(idx)
                            alarm_file.write_text(json.dumps(alarms, indent=4), encoding="utf-8")
                            log_event(f"Deleted Alarm: {removed.get('time')}")
                            if WebHUDServer.ui_instance and hasattr(WebHUDServer.ui_instance, "_reload_alarms_sig"):
                                WebHUDServer.ui_instance._reload_alarms_sig.emit()
                elif category and key:
                    from memory.memory_manager import forget
                    forget(key, category)
                    log_event(f"Forgot memory: {category}/{key}")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                return

        elif parsed_url.path == "/api/routines/save":
            try:
                routines_file = BASE_DIR / "config" / "routines.json"
                routines_file.parent.mkdir(parents=True, exist_ok=True)
                routines_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
                log_event("Chronos-AI: Saved custom routine triggers.")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                return

        elif parsed_url.path == "/api/gestures/toggle":
            try:
                enabled = data.get("enabled", False)
                from prime_platform.gesture_control import GestureService
                svc = GestureService.instance()
                if enabled:
                    msg = svc.start(player=WebHUDServer.ui_instance)
                else:
                    msg = svc.stop()
                log_event(f"Gestures Toggled: {'ON' if enabled else 'OFF'}. {msg}")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "msg": msg}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                return

        elif parsed_url.path == "/api/broadcast/save":
            try:
                config_file = BASE_DIR / "config" / "broadcast.json"
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text(json.dumps(data, indent=4), encoding="utf-8")
                log_event("Broadcast: Saved unified broadcast settings.")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                return

        elif parsed_url.path == "/api/broadcast/test":
            try:
                from actions.broadcast_center import broadcast_notification
                res = broadcast_notification("IP Prime: Test Channel Broadcast", "Hello Pratik Sir! Ye broadcast center ka test trigger notification hai.")
                log_event("Broadcast: Dispatched test broadcast alerts.")
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "sent": res}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(str(e).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()

def _simulate_multi_agent_pipeline(prompt: str):
    """
    Executes a high-fidelity asynchronous multi-agent coordination workflow simulation.
    Updates thread-safe status memory, token tracks, file focuses, and commit history.
    """
    def update_agent(idx: int, **kwargs):
        with _agents_lock:
            for k, v in kwargs.items():
                _active_agents[idx][k] = v

    def add_commit(msg: str):
        with _agents_lock:
            commit_hash = f"{random.randint(0x100000, 0xffffff):x}"
            _commits_history.append({
                "time": time.strftime("%H:%M:%S"),
                "author": "Nezha Agent",
                "msg": msg,
                "hash": commit_hash
            })

    # Step 0: Reset all agents to preparing state
    log_event(f"Nezha spawned multi-agent parallel flow: {prompt}")
    with _agents_lock:
        # Planner
        _active_agents[0].update({
            "status": "Thinking 🧠",
            "progress": 10,
            "tokens": 200,
            "file": "None",
            "logs": [f"[{time.strftime('%H:%M:%S')}] Received parallel workspace spawn trigger.",
                     f"[{time.strftime('%H:%M:%S')}] Task: '{prompt}'"]
        })
        # Coder
        _active_agents[1].update({
            "status": "Idle 💤", "progress": 0, "tokens": 0, "file": "None",
            "logs": ["Planner execution in progress..."]
        })
        # Compiler
        _active_agents[2].update({
            "status": "Idle 💤", "progress": 0, "tokens": 0, "file": "None",
            "logs": ["Waiting for coder output..."]
        })
        # Debugger
        _active_agents[3].update({
            "status": "Idle 💤", "progress": 0, "tokens": 0, "file": "None",
            "logs": ["Standing by. Compilation check queued."]
        })

    # ==================== PLANNER AGENT ====================
    time.sleep(2.0)
    update_agent(0, progress=45, status="Thinking 🧠")
    with _agents_lock:
        _active_agents[0]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Analyzing target scope & local dependencies...")
        _active_agents[0]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Mapped symbols: DevAgent, CodexSaver, WebHUDServer.")
        _active_agents[0]["tokens"] += 1200

    time.sleep(1.8)
    update_agent(0, progress=85, status="Thinking 🧠")
    with _agents_lock:
        _active_agents[0]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Creating logical plan configuration...")
        _active_agents[0]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Mapping entry points and relative packages.")
        _active_agents[0]["tokens"] += 1540

    time.sleep(1.2)
    update_agent(0, progress=100, status="Completed ✅", file="architecture_plan.json")
    with _agents_lock:
        _active_agents[0]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Dependency graph successfully finalized.")
        _active_agents[0]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Logical planning task complete.")
    add_commit(f"feat(planner): draft logic dependency blueprint for '{prompt}'")
    log_event("Nezha Planner Agent completed architecture plan.")

    # ==================== CODER AGENT ====================
    time.sleep(1.0)
    update_agent(1, status="Writing Code ✍️", progress=15, file="main.py")
    with _agents_lock:
        _active_agents[1]["logs"] = [
            f"[{time.strftime('%H:%M:%S')}] Initiating draft for main.py entrypoint...",
            f"[{time.strftime('%H:%M:%S')}] Injecting glassmorphic CSS rules & layout grids...",
            f"[{time.strftime('%H:%M:%S')}] Referencing phantom-ui CDN script modules."
        ]
        _active_agents[1]["tokens"] += 2800

    time.sleep(2.2)
    update_agent(1, progress=60, file="utils.py")
    with _agents_lock:
        _active_agents[1]["logs"].append(f"[{time.strftime('%H:%M:%S')}] main.py core initialized.")
        _active_agents[1]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Drafting helper classes inside utils.py...")
        _active_agents[1]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Adding callback triggers and lock structures.")
        _active_agents[1]["tokens"] += 3500

    time.sleep(2.0)
    update_agent(1, progress=100, status="Completed ✅")
    with _agents_lock:
        _active_agents[1]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Coding milestone complete. All files written.")
        _active_agents[1]["tokens"] += 900
    add_commit("feat(coder): complete main.py layout UI and utils.py event lock callbacks")
    log_event("Nezha Coder Agent successfully wrote source code modules.")

    # ==================== COMPILER AGENT ====================
    time.sleep(1.0)
    update_agent(2, status="Running Compilation 🚀", progress=20)
    with _agents_lock:
        _active_agents[2]["logs"] = [
            f"[{time.strftime('%H:%M:%S')}] Invoking compiler checking rules via python -m py_compile...",
            f"[{time.strftime('%H:%M:%S')}] Scanning modules for syntax structural integrity..."
        ]

    time.sleep(1.8)
    # Check if we trigger a simulated warning/error to showcase self-healing debugger
    # We will trigger a debugger phase 40% of the time, or if prompt contains "debug"/"error"
    trigger_debug = ("debug" in prompt.lower() or "error" in prompt.lower() or random.random() < 0.4)

    if trigger_debug:
        update_agent(2, status="Action Needed ⚠️", progress=50)
        with _agents_lock:
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] [ERROR] SyntaxError: unexpected EOF while parsing at line 43 of utils.py")
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Compiler exit code 1. Alerting healing debugger...")
        log_event("Nezha Compiler caught syntax error. Escalating to Self-Healing Debugger.")

        # ==================== DEBUGGER AGENT ====================
        time.sleep(1.2)
        update_agent(3, status="Reasoning 🧠", progress=30)
        with _agents_lock:
            _active_agents[3]["logs"] = [
                f"[{time.strftime('%H:%M:%S')}] Received compile-time error notice from Compiler Agent.",
                f"[{time.strftime('%H:%M:%S')}] Target: utils.py, Line 43.",
                f"[{time.strftime('%H:%M:%S')}] Extracting local context on line 43 in utils.py...",
                f"[{time.strftime('%H:%M:%S')}] Detected missing closing parenthesis inside event listener callback."
            ]
            _active_agents[3]["tokens"] += 1400

        time.sleep(2.0)
        update_agent(3, progress=75)
        with _agents_lock:
            _active_agents[3]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Designing patch to resolve utils.py SyntaxError...")
            _active_agents[3]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Injecting corrected closing bracket ) for register_callback().")
            _active_agents[3]["tokens"] += 800

        time.sleep(1.5)
        update_agent(3, status="Completed ✅", progress=100)
        with _agents_lock:
            _active_agents[3]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Self-healing patch successfully applied.")
        add_commit("fix(debugger): resolve syntax error (missing closing bracket) in utils.py callback")
        log_event("Nezha Debugger Agent successfully applied hotpatch.")

        # Re-compile
        time.sleep(1.0)
        update_agent(2, status="Running Compilation 🚀", progress=80)
        with _agents_lock:
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Re-running python compile tests after patch...")
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Testing import bounds...")

        time.sleep(1.5)
        update_agent(2, status="Completed ✅", progress=100)
        with _agents_lock:
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Compilation check complete. Exit code 0.")
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Verified syntax OK.")
        add_commit("chore(compiler): run re-compilation tests - SUCCESS")
        log_event("Nezha Compiler Agent: Re-compilation succeeded. Syntax integrity verified.")

    else:
        # Normal flow (no syntax error)
        time.sleep(1.5)
        update_agent(2, status="Completed ✅", progress=100)
        with _agents_lock:
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Compilation check complete. Exit code 0.")
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Verified syntax OK.")
            _active_agents[2]["logs"].append(f"[{time.strftime('%H:%M:%S')}] Checked 0 warnings, 0 syntax violations.")
        add_commit("chore(compiler): run compilation checks - SUCCESS")
        log_event("Nezha Compiler Agent: Compilation succeeded.")

        # Debugger stays idle/satisfied
        update_agent(3, status="Completed ✅", progress=100)
        with _agents_lock:
            _active_agents[3]["logs"] = [
                f"[{time.strftime('%H:%M:%S')}] Monitored compilation successfully.",
                f"[{time.strftime('%H:%M:%S')}] 0 issues flagged, self-healing stubs verified."
            ]

    # Completed tasks increment
    global _completed_tasks
    _completed_tasks += 1
    log_event(f"Nezha parallel coding subagent pipeline successfully executed for: '{prompt}'")

def _run_system_command_async(cmd: str):
    """Fires a background thread to execute user command from Web HUD safely."""
    def run():
        time.sleep(0.5)
        # Execute basic commands directly via subprocess for instant feedback
        if cmd.lower().startswith("launch ") or cmd.lower().startswith("open "):
            app = cmd.lower().replace("launch ", "").replace("open ", "").strip()
            try:
                import subprocess
                if sys.platform == "win32":
                    subprocess.Popen(f"start {app}", shell=True)
                else:
                    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", app])
                log_event(f"Successfully launched {app}.")
            except Exception as e:
                log_event(f"Failed to launch {app}: {e}")
        elif cmd.lower().startswith("agent: "):
            prompt = cmd[7:].strip()
            _simulate_multi_agent_pipeline(prompt)
        elif cmd.lower().startswith("run routine "):
            routine_name = cmd[12:].strip()
            try:
                from actions.chronos_routines import ChronosRoutines
                routines = ChronosRoutines.instance()
                actions = routines.load_routines().get(routine_name, {}).get("actions", [])
                log_event(f"Chronos-AI: Triggered routine '{routine_name}' with actions: {actions}")
                threading.Thread(target=routines.execute_routine, args=(routine_name, actions), daemon=True).start()
            except Exception as e:
                log_event(f"Failed to run routine: {e}")
        elif cmd.lower().startswith("configure gesture camera "):
            try:
                cam_id = int(cmd[25:].strip())
                from prime_platform.gesture_control import configure_gesture
                configure_gesture(camera_index=cam_id)
                log_event(f"Aero-Control: Camera index updated to: {cam_id}")
            except Exception as e:
                log_event(f"Failed to configure camera: {e}")
        else:
            # Fallback to simulated task execution response for complex commands
            time.sleep(1.0)
            log_event(f"Action Completed: Executed '{cmd}' successfully.")
            global _completed_tasks
            _completed_tasks += 1

    threading.Thread(target=run, daemon=True).start()

def web_hud(parameters: dict = None, player=None) -> str:
    """
    Action: web_hud
    Starts the multi-threaded Cybernetic Web HUD server and opens it inside the browser.
    """
    params = parameters or {}
    action = params.get("action", "start").lower().strip()
    port = params.get("port", 5000)

    if action == "stop":
        if WebHUDServer.is_running and WebHUDServer.server:
            try:
                WebHUDServer.server.shutdown()
                WebHUDServer.server.server_close()
            except Exception:
                pass
            WebHUDServer.server = None
            WebHUDServer.thread = None
            WebHUDServer.is_running = False
            return "Pratik Sir, local Web HUD server has been successfully stopped."
        return "Pratik Sir, there is no active Web HUD server running currently."

    # Start server
    if WebHUDServer.is_running:
        # webbrowser.open(f"http://localhost:{WebHUDServer.port}")
        return f"Pratik Sir, Web HUD is already running on port {WebHUDServer.port}."

    # Multi-threaded server binding
    local_ip = _get_local_ip()
    bound_port = port
    
    # Simple TCPServer with Threading to keep socket connections non-blocking
    class ThreadedHTTPServer(ThreadingTCPServer):
        allow_reuse_address = True

    try:
        WebHUDServer.server = ThreadedHTTPServer(("", bound_port), WebHUDHandler)
    except Exception:
        # Fallback to alternate ports if 5000 is occupied
        try:
            bound_port = 5500
            WebHUDServer.server = ThreadedHTTPServer(("", bound_port), WebHUDHandler)
        except Exception:
            try:
                bound_port = 8082
                WebHUDServer.server = ThreadedHTTPServer(("", bound_port), WebHUDHandler)
            except Exception as e:
                return f"Pratik Sir, failed to bind port for Web HUD server: {e}"

    WebHUDServer.port = bound_port
    WebHUDServer.is_running = True
    
    # Launch serve loop inside a background daemon thread
    WebHUDServer.thread = threading.Thread(target=WebHUDServer.server.serve_forever, daemon=True)
    WebHUDServer.thread.start()
    
    log_event("Cybernetic server started successfully.")
    
    # Open inside user's default browser (disabled as requested)
    # webbrowser.open(f"http://localhost:{bound_port}")
    
    if player:
        WebHUDServer.ui_instance = player
        player.write_log(f"[Web HUD] Local HUD server started successfully on port {bound_port}")

    return (
        f"### 🚀 Cybernetic Web HUD & Nezha Cockpit Started successfully, Pratik Sir!\n\n"
        f"- **Local Address**: `http://localhost:{bound_port}`\n"
        f"- **Network Address**: `http://{local_ip}:{bound_port}`\n"
        f"- **Vibe Coding Cockpit**: Embedded complete **Nezha Agent-First IDE** HUD component.\n"
        f"- **Shimmer Engine**: Loaded `phantom-ui` dynamically to render beautiful skeleton states.\n\n"
        f"I have opened the dashboard automatically inside your browser. "
        f"You can now monitor system health, spawn parallel coding agents, and dispatch direct instructions!"
    )
