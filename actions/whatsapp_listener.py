"""
whatsapp_listener.py — Playwright listener monitoring incoming WhatsApp Web messages.

This is a standard action module for the IP Prime personal assistant suite.
"""

import re
import json
import time
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright

def _load_stealth_config() -> dict:
    try:
        import sys
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).resolve().parent.parent
        config_path = base_dir / "config" / "api_keys.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[WhatsAppBot] Error loading config: {e}")
    return {}

def _parse_proxy_string(proxy_str: str) -> dict | None:
    proxy_str = proxy_str.strip()
    if not proxy_str:
        return None
    from urllib.parse import urlparse
    try:
        if not (proxy_str.startswith("http://") or proxy_str.startswith("https://") or proxy_str.startswith("socks5://") or proxy_str.startswith("socks4://")):
            parsed = urlparse("http://" + proxy_str)
        else:
            parsed = urlparse(proxy_str)
        
        netloc = parsed.netloc
        if "@" in netloc:
            auth, _, host = netloc.rpartition("@")
            username, _, password = auth.partition(":")
        else:
            host = netloc
            username, password = None, None
        
        scheme = parsed.scheme or "http"
        server = f"{scheme}://{host}"
        p = {"server": server}
        if username:
            p["username"] = username
        if password:
            p["password"] = password
        return p
    except Exception as e:
        print(f"[WhatsAppBot] Proxy parse error for '{proxy_str}': {e}")
        return None


class WhatsAppListenerService:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(WhatsAppListenerService, cls).__new__(cls)
                cls._instance.is_running = False
                cls._instance.thread = None
                cls._instance.player = None
                cls._instance.processed_commands = {}
                cls._instance.group_joined = False
            return cls._instance

    def start(self, player=None):
        with self._lock:
            if self.is_running:
                return "WhatsApp Bot Service is already running, sir."
            self.is_running = True
            self.player = player
            self.group_joined = False
            self.thread = threading.Thread(target=self._run_loop, daemon=True, name="WhatsAppListenerThread")
            self.thread.start()
            return "WhatsApp Bot Service started successfully, sir!"

    def stop(self):
        with self._lock:
            if not self.is_running:
                return "WhatsApp Bot Service is not running, sir."
            self.is_running = False
            return "WhatsApp Bot Service stopped, sir."

    def get_status(self) -> str:
        return "Connected & Listening" if self.is_running else "Stopped"

    def _log(self, msg: str):
        print(f"[WhatsAppBot] {msg}")
        if self.player:
            self.player.write_log(f"[WhatsAppBot] {msg}")

    def _check_and_join_group(self, page):
        if self.group_joined:
            return

        cfg = _load_stealth_config()
        group_link = cfg.get("whatsapp_group_link", "").strip()
        if not group_link:
            self.group_joined = True
            return

        # Extract invite code
        match = re.search(r'(?:chat\.whatsapp\.com/|accept\?code=)([A-Za-z0-9_-]+)', group_link)
        code = match.group(1) if match else group_link
        if not code:
            self.group_joined = True
            return

        self._log(f"Attempting to join group/chat with invite code: {code}...")
        try:
            # Navigate to Accept URL directly
            page.goto(f"https://web.whatsapp.com/accept?code={code}")
            self._log("Navigated accept URL. Waiting for interface to render...")
            time.sleep(6)

            # Try to auto-click "Join group" button
            joined = page.evaluate("""() => {
                const btn = Array.from(document.querySelectorAll('button, div[role="button"]'))
                    .find(b => b.innerText && b.innerText.toLowerCase().includes('join group'));
                if (btn) {
                    btn.click();
                    return true;
                }
                return false;
            }""")
            if joined:
                self._log("Group Join Request sent successfully!")
                time.sleep(4)
            else:
                self._log("No Join Popup found (either already joined or chat window opened directly).")
            self.group_joined = True
        except Exception as e:
            self._log(f"Error while auto-joining group: {e}")

    def _process_chat_message(self, page, chat_name):
        try:
            msg_data = page.evaluate("""() => {
                const msgs = document.querySelectorAll('.message-in');
                if (msgs.length === 0) return null;
                const lastMsg = msgs[msgs.length - 1];
                const textSpan = lastMsg.querySelector('.selectable-text span');
                const text = textSpan ? textSpan.innerText : lastMsg.innerText;
                
                let dataId = lastMsg.getAttribute('data-id');
                if (!dataId) {
                    const parentWithId = lastMsg.closest('[data-id]');
                    if (parentWithId) dataId = parentWithId.getAttribute('data-id');
                }
                return { text: text, id: dataId || text };
            }""")

            if not msg_data:
                return

            last_msg = msg_data.get("text", "").strip()
            last_msg_id = msg_data.get("id", "")

            is_cmd = last_msg.lower().startswith(('/ip', '!ip'))
            if is_cmd:
                if self.processed_commands.get(chat_name) == last_msg_id:
                    return

                self._log(f"New command from '{chat_name}': {last_msg}")
                self.processed_commands[chat_name] = last_msg_id

                result = execute_ip_prime_command(last_msg, player=self.player)
                self._log("Execution done. Sending response...")

                page.evaluate("""(text) => {
                    const input = document.querySelector('div[contenteditable="true"][data-tab="10"]') || document.querySelector('div[contenteditable="true"]');
                    if (input) {
                        input.focus();
                        document.execCommand('insertText', false, text);
                    }
                }""", f"🤖 *IP PRIME BOT RESPONSE* 🤖\n\n{result}")
                time.sleep(0.5)
                page.keyboard.press("Enter")
                self._log(f"Response dispatched successfully to '{chat_name}'.")
        except Exception as err:
            self._log(f"Failed to process message inside chat '{chat_name}': {err}")

    def _execute_whatsapp_loop(self, page):
        # 1. QR Code Check
        qr_visible = page.locator("canvas").is_visible()
        if qr_visible:
            self._log("⚠️ WhatsApp QR Code scan required! Please scan the QR code in the browser window.")
            time.sleep(10)
            return

        # 2. Check if logged in & join group if not yet done
        is_ready = page.locator("#side").is_visible()
        if not is_ready:
            return

        if not self.group_joined:
            self._check_and_join_group(page)
            return

        # 3. Read currently active/opened chat (instant processing)
        active_chat_name = page.evaluate("""() => {
            const header = document.querySelector('header');
            if (!header) return null;
            const span = header.querySelector('span[dir="auto"]');
            return span ? span.innerText : null;
        }""")

        if active_chat_name:
            self._process_chat_message(page, active_chat_name)

        # 4. Search and process unread sidebar chats
        unread_chat = page.evaluate("""() => {
            const pane = document.querySelector('#pane-side') || document.querySelector('[aria-label="Chat list"]') || document.querySelector('[role="grid"]');
            if (!pane) return null;
            const badges = Array.from(pane.querySelectorAll('span'));
            for (const badge of badges) {
                const label = (badge.getAttribute('aria-label') || '').toLowerCase();
                const text = badge.innerText || '';
                if (label.includes('unread') || (badge.classList.contains('x10l5t2y') && /^\d+$/.test(text))) {
                    let parent = badge.parentElement;
                    while (parent && parent !== pane) {
                        if (parent.getAttribute('role') === 'row' || parent.classList.contains('lhwtacf6') || parent.classList.contains('_199zF')) {
                            return true;
                        }
                        parent = parent.parentElement;
                    }
                }
            }
            return null;
        }""")

        if unread_chat:
            self._log("Sidebar unread badge detected. Switching context...")
            page.evaluate("""() => {
                const pane = document.querySelector('#pane-side') || document.querySelector('[aria-label="Chat list"]') || document.querySelector('[role="grid"]');
                if (!pane) return;
                const badges = Array.from(pane.querySelectorAll('span'));
                for (const badge of badges) {
                    const label = (badge.getAttribute('aria-label') || '').toLowerCase();
                    const text = badge.innerText || '';
                    if (label.includes('unread') || (badge.classList.contains('x10l5t2y') && /^\d+$/.test(text))) {
                        let parent = badge.parentElement;
                        while (parent && parent !== pane) {
                            if (parent.getAttribute('role') === 'row' || parent.classList.contains('lhwtacf6') || parent.classList.contains('_199zF')) {
                                parent.click();
                                return;
                            }
                            parent = parent.parentElement;
                        }
                    }
                }
            }""")
            time.sleep(1.5)

            new_active_chat = page.evaluate("""() => {
                const header = document.querySelector('header');
                if (!header) return 'Unknown';
                const span = header.querySelector('span[dir="auto"]');
                return span ? span.innerText : 'Unknown';
            }""")

            self._process_chat_message(page, new_active_chat)

    def _run_loop(self):
        cfg = _load_stealth_config()
        use_camou = cfg.get("use_camoufox", False)
        
        if use_camou:
            try:
                from camoufox.sync_api import Camoufox
                self._log("🕷 Booting sync Camoufox Stealth browser for WhatsApp Remote...")
                
                user_data_dir = Path.home() / ".ipprime_camoufox_whatsapp"
                user_data_dir.mkdir(parents=True, exist_ok=True)
                
                # Force headless = False for WhatsApp so the user can see the QR code to scan!
                headless = False
                os_spoof = cfg.get("camoufox_os", "random")
                if os_spoof not in ("windows", "macos", "linux"):
                    os_spoof = "random"
                
                block_assets = cfg.get("camoufox_block_assets", False)
                humanize = cfg.get("camoufox_human_mimic", True)
                proxy_str = cfg.get("camoufox_proxy", "")
                
                proxy_dict = _parse_proxy_string(proxy_str) if proxy_str else None
                
                # Load advanced stealth options
                block_webrtc = cfg.get("camoufox_block_webrtc", True)
                allow_webgl = cfg.get("camoufox_allow_webgl", False)
                geoip = cfg.get("camoufox_geoip", True)
                addons_path_str = cfg.get("camoufox_addons_path", "")
                
                # Scan add-ons path if specified
                addons_list = []
                if addons_path_str:
                    try:
                        addons_dir = Path(addons_path_str)
                        if addons_dir.exists() and addons_dir.is_dir():
                            for item in addons_dir.iterdir():
                                if item.is_dir() and (item / "manifest.json").exists():
                                    addons_list.append(str(item.resolve()))
                            if (addons_dir / "manifest.json").exists():
                                addons_list.append(str(addons_dir.resolve()))
                    except Exception as ae:
                        self._log(f"Error scanning addons directory: {ae}")
                
                self._log(f"Launching sync Camoufox (headless={headless}, os={os_spoof}, block_images={block_assets}, humanize={humanize}, proxy={proxy_str}, block_webrtc={block_webrtc}, allow_webgl={allow_webgl}, geoip={geoip}, addons={len(addons_list)} found)...")
                
                with Camoufox(
                    persistent_context=True,
                    user_data_dir=str(user_data_dir),
                    headless=headless,
                    os=os_spoof,
                    block_images=block_assets,
                    humanize=humanize,
                    proxy=proxy_dict,
                    geoip=geoip,
                    block_webrtc=block_webrtc,
                    allow_webgl=allow_webgl,
                    addons=addons_list if addons_list else None,
                ) as context:
                    page = context.new_page()
                    page.goto("https://web.whatsapp.com")
                    self._log("Waiting for WhatsApp Web to load...")
                    
                    while self.is_running:
                        try:
                            self._execute_whatsapp_loop(page)
                            time.sleep(3)
                        except Exception as loop_err:
                            self._log(f"Error in listener loop: {loop_err}")
                            time.sleep(5)
                    
                    self._log("WhatsApp Bot Service background thread terminated.")
                    return
            except ImportError:
                self._log("⚠️ Camoufox package not found. Falling back to standard Chromium...")
            except Exception as e:
                self._log(f"⚠️ Camoufox startup failed: {e}. Falling back to standard Chromium...")
                
        # FALLBACK TO STANDARD CHROMIUM
        self._log("Booting Playwright in persistent mode...")
        user_data_dir = Path.home() / ".ipprime_playwright_whatsapp"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    channel="chrome",
                    args=["--disable-blink-features=AutomationControlled"]
                )
            except Exception as e:
                self._log(f"Failed to launch Chrome channel ({e}). Retrying with default chromium...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir=str(user_data_dir),
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"]
                )

            page = context.new_page()
            page.goto("https://web.whatsapp.com")
            self._log("Waiting for WhatsApp Web to load...")

            while self.is_running:
                try:
                    self._execute_whatsapp_loop(page)
                    time.sleep(3)
                except Exception as loop_err:
                    self._log(f"Error in listener loop: {loop_err}")
                    time.sleep(5)

            try:
                context.close()
            except Exception:
                pass
            self._log("WhatsApp Bot Service background thread terminated.")




def execute_ip_prime_command(command_text: str, player=None) -> str:
    cleaned = re.sub(r'^[/*!]ip\s+', '', command_text, flags=re.IGNORECASE).strip()
    
    import warnings
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning)
        import google.generativeai as genai
    from actions.dev_agent import _get_api_key, _strip_fences
    
    try:
        genai.configure(api_key=_get_api_key())
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # Fetch active MCP tools
        mcp_tools_desc = ""
        try:
            from actions.mcp_client import MCPClientManager
            mcp_mgr = MCPClientManager()
            all_mcp = mcp_mgr.get_all_tools()
            for t in all_mcp:
                s_name = t.get("server_name")
                t_name = t.get("name").replace("-", "_")
                desc = t.get("description", "")
                params_schema = t.get("inputSchema", {}).get("properties", {})
                mcp_tools_desc += f"- \"mcp__{s_name}__{t_name}\": {desc}. Parameters: {json.dumps(params_schema)}\n"
        except Exception as e:
            print(f"[WhatsAppBot] Error loading MCP tools: {e}")
        
        prompt = f"""You are the backend AI coordinator for IP PRIME. 
The user has sent a command via WhatsApp: "{cleaned}"

Map this request to one of the following IP PRIME actions and return ONLY a valid JSON payload.
Available actions:
1. "web_search": parameters: {{"query": "search query"}}
2. "weather": parameters: {{"location": "city name"}}
3. "open_app": parameters: {{"app_name": "notepad/calculator/chrome/etc"}}
4. "computer_settings": parameters: {{"setting": "volume/brightness/wifi/etc", "value": "up/down/on/off"}}
5. "file_processor": parameters: {{"file_path": "path/to/file", "action": "summarize/extract_text/parse_document"}}
6. "refactor_code": parameters: {{"file_path": "path/to/code/file", "action": "refactor/simplify/docstrings"}}
7. "git_assistant": parameters: {{"action_type": "commit/push/dry-run", "project_path": "path/to/repo"}}
8. "system_info": parameters: {{}}
9. "semantic_search": parameters: {{"query": "search query"}}
10. "index_workspace": parameters: {{"path": "path/to/workspace/directory"}}
11. "media_control": parameters: {{"action": "play/pause/next/prev/volume_up/volume_down/now_playing"}}
12. "github_assistant": parameters: {{"action": "get_diff/commit_push/create_pr", "repo_path": "path/to/repo", "commit_message": "message", "title": "PR Title", "body": "PR Body"}}
13. "schedule_manager": parameters: {{"action": "add/list/delete", "title": "Event description", "date": "YYYY-MM-DD", "time": "HH:MM", "event_id": "8-char event id"}}
14. "n8n_automation": parameters: {{"webhook_name": "invoice/backup/etc", "payload": {{"key": "value"}}}}
15. "index_obsidian_vault": parameters: {{}}
16. "search_obsidian_notes": parameters: {{"query": "search query", "limit": 5}}
17. "capture_and_analyze_screen": parameters: {{"prompt": "Specific question or analysis prompt for screen state"}}
18. "search_spotify_track": parameters: {{"query": "track/song query to search"}}
19. "execute_smart_home_command": parameters: {{"action": "turn_on/turn_off/toggle", "device_name": "device name", "domain": "light/switch/climate"}}
20. "list_active_audio_sessions": parameters: {{}}
21. "set_application_volume": parameters: {{"app_name": "app process name (e.g. chrome.exe)", "volume_level": 50}}
22. "mute_application": parameters: {{"app_name": "app process name (e.g. chrome.exe)", "mute_state": true}}
23. "run_aider_coding_task": parameters: {{"instruction": "instruction/prompt for Aider to execute", "file_paths": ["optional relative/absolute paths to edit"], "project_path": "optional repository folder path"}}
24. "get_awesome_repo_info": parameters: {{"query": "optional name of repository, index number, or search query (e.g. 'Aider AI', '18', 'list')"}}
25. "clone_awesome_repo": parameters: {{"repo_name": "name or index number of repository to clone (e.g. 'Open Interpreter', '11')"}}
{mcp_tools_desc}

Return JSON format:
{{
  "action": "action_name",
  "parameters": {{ ... }}
}}
"""
        response = model.generate_content(prompt)
        raw_json = _strip_fences(response.text)
        routing = json.loads(raw_json)
        
        action = routing.get("action")
        params = routing.get("parameters", {})
        
        if player:
            player.write_log(f"[WhatsAppBot] Intent mapped: action={action}, params={params}")

        if action.startswith("mcp__"):
            parts = action.split("__")
            if len(parts) >= 3:
                server_name = parts[1]
                actual_tool_name = parts[2]
                
                # Check for original tool name (mapping back underscores to hyphens if needed)
                try:
                    from actions.mcp_client import MCPClientManager
                    mcp_mgr = MCPClientManager()
                    conn = mcp_mgr.connections.get(server_name)
                    if conn:
                        for t in conn.tools:
                            orig = t.get("name")
                            if orig.replace("-", "_") == actual_tool_name:
                                actual_tool_name = orig
                                break
                except Exception:
                    pass
                
                if player:
                    player.write_log(f"[WhatsAppBot] Routing to MCP server '{server_name}', tool '{actual_tool_name}' with args {params}")
                
                from actions.mcp_client import MCPClientManager
                return MCPClientManager().execute_tool(server_name, actual_tool_name, params)
            else:
                return f"Error: Invalid MCP action format: {action}"

        elif action == "web_search":
            from actions.web_search import web_search_action
            return web_search_action(params, player=player)
        elif action == "weather":
            from actions.weather_report import weather_action
            return weather_action(params, player=player)
        elif action == "open_app":
            from actions.open_app import open_app
            return open_app(params, player=player)
        elif action == "computer_settings":
            from actions.computer_settings import computer_settings
            return computer_settings(params, player=player)
        elif action == "file_processor":
            from actions.file_processor import file_processor
            return file_processor(params, player=player)
        elif action == "refactor_code":
            from actions.dev_agent import refactor_code
            return refactor_code(params.get("file_path"), params.get("action", "refactor"), player=player)
        elif action == "git_assistant":
            from actions.dev_agent import git_assistant
            return git_assistant(params.get("action_type", "commit"), params.get("project_path", ""), player=player)
        elif action == "system_info":
            import platform
            import psutil
            return f"IP PRIME System Info:\nOS: {platform.system()} {platform.release()}\nCPU: {psutil.cpu_percent()}%\nRAM: {psutil.virtual_memory().percent}%"
        elif action == "semantic_search":
            from actions.semantic_store import semantic_search
            return semantic_search(params.get("query", ""))
        elif action == "index_workspace":
            from actions.semantic_store import index_directory
            return index_directory(params.get("path", ""))
        elif action == "media_control":
            from actions.media_controller import execute_media_control
            return execute_media_control(params.get("action", ""))
        elif action == "github_assistant":
            from actions.github_assistant import execute_git_automation
            return execute_git_automation(
                action=params.get("action", ""),
                repo_path=params.get("repo_path"),
                commit_message=params.get("commit_message"),
                title=params.get("title"),
                body=params.get("body")
            )
        elif action == "schedule_manager":
            from actions.calendar_helper import execute_schedule_manager
            return execute_schedule_manager(
                action=params.get("action", ""),
                title=params.get("title"),
                date=params.get("date"),
                time=params.get("time"),
                event_id=params.get("event_id")
            )
        elif action == "n8n_automation":
            from actions.n8n_dispatcher import trigger_n8n_webhook
            return trigger_n8n_webhook(
                webhook_name=params.get("webhook_name", ""),
                payload=params.get("payload")
            )
        elif action == "index_obsidian_vault":
            from actions.obsidian_helper import index_obsidian_vault
            return index_obsidian_vault()
        elif action == "search_obsidian_notes":
            from actions.obsidian_helper import search_obsidian_notes
            return search_obsidian_notes(
                query=params.get("query", ""),
                limit=int(params.get("limit", 5))
            )
        elif action == "capture_and_analyze_screen":
            from actions.screen_vision import capture_and_analyze_screen
            return capture_and_analyze_screen(
                prompt=params.get("prompt", "Explain what is currently on my screen.")
            )
        elif action == "search_spotify_track":
            from actions.spotify_helper import search_spotify_track
            return search_spotify_track(
                query=params.get("query", "")
            )
        elif action == "execute_smart_home_command":
            from actions.smart_home import execute_smart_home_command
            return execute_smart_home_command(
                action=params.get("action", "turn_on"),
                device_name=params.get("device_name", ""),
                domain=params.get("domain", "light")
            )
        elif action == "list_active_audio_sessions":
            from actions.audio_mixer import list_active_audio_sessions
            return list_active_audio_sessions()
        elif action == "set_application_volume":
            from actions.audio_mixer import set_application_volume
            return set_application_volume(
                app_name=params.get("app_name", ""),
                volume_level=int(params.get("volume_level", 100))
            )
        elif action == "mute_application":
            from actions.audio_mixer import mute_application
            return mute_application(
                app_name=params.get("app_name", ""),
                mute_state=bool(params.get("mute_state", False))
            )
        elif action == "run_aider_coding_task":
            from actions.aider_helper import run_aider_coding_task
            return run_aider_coding_task(
                instruction=params.get("instruction"),
                file_paths=params.get("file_paths"),
                project_path=params.get("project_path")
            )
        elif action == "get_awesome_repo_info":
            from actions.awesome_repos_helper import get_awesome_repo_info
            return get_awesome_repo_info(
                query=params.get("query")
            )
        elif action == "clone_awesome_repo":
            from actions.awesome_repos_helper import clone_awesome_repo
            return clone_awesome_repo(
                repo_name=params.get("repo_name")
            )
        else:
            return f"Intent mapped to unknown action: {action}"
            
    except Exception as e:
        return f"Failed to execute command: {e}"

class WhatsAppAutoReplyService:
    """Background service that monitors WhatsApp Web for new messages and sends auto-replies when busy mode is active."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if not cls._instance:
                cls._instance = super(WhatsAppAutoReplyService, cls).__new__(cls)
                cls._instance.is_running = False
                cls._instance.auto_reply_message = "Pratik bhai abhi thode busy hain, sir. Baad mein reply karenge, sir!"
                cls._instance.busy_mode = False
                cls._instance.replied_to = set()
                cls._instance.thread = None
                cls._instance.player = None
            return cls._instance

    def start(self, auto_reply_msg: str = "", player=None) -> str:
        with self._lock:
            if self.is_running:
                return "WhatsApp Auto-Reply Service is already active, sir."
                
            if auto_reply_msg:
                self.auto_reply_message = auto_reply_msg
                
            self.player = player
            self.busy_mode = True
            self.is_running = True
            self.replied_to.clear()
            
            self.thread = threading.Thread(target=self._run_auto_reply_loop, daemon=True, name="WhatsAppAutoReplyThread")
            self.thread.start()
            
            return f"WhatsApp Auto-Reply Service started, sir! Busy Mode is ON. Message set: '{self.auto_reply_message}'"

    def stop(self) -> str:
        with self._lock:
            if not self.is_running:
                return "WhatsApp Auto-Reply Service active nahi hai, sir."
                
            self.is_running = False
            self.busy_mode = False
            return "WhatsApp Auto-Reply Service stopped, sir. Busy Mode is OFF."

    def set_message(self, message: str) -> str:
        if not message:
            return "Message content empty hai, sir."
        self.auto_reply_message = message
        return f"Auto-reply message successfully updated to: '{message}', sir."

    def _log(self, msg: str):
        print(f"[WhatsAppAutoReply] {msg}")
        if self.player:
            self.player.write_log(f"[WhatsAppAutoReply] {msg}")

    def _run_auto_reply_loop(self):
        self._log("Auto-reply background thread spawned.")
        try:
            with sync_playwright() as p:
                cfg = _load_stealth_config()
                # Determine proxy
                proxy_dict = None
                proxy_str = cfg.get("whatsapp_proxy", "").strip()
                if proxy_str:
                    proxy_dict = _parse_proxy_string(proxy_str)
                    
                user_data_dir = str(Path.home() / ".ipprime" / "whatsapp_session")
                
                self._log("Launching persistent context in headless mode...")
                context = p.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=True,
                    proxy=proxy_dict,
                    viewport={"width": 1280, "height": 720}
                )
                page = context.new_page() if not context.pages else context.pages[0]
                page.goto("https://web.whatsapp.com")
                
                # Give it time to load or detect login
                for i in range(15):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
                self._log("Loop active. Scanning for unread incoming messages...")
                
                while self.is_running and self.busy_mode:
                    try:
                        # Find and click any unread chat badge
                        unread_clicked = page.evaluate("""() => {
                            const badge = document.querySelector('span[aria-label*="unread"], span[aria-label*="Unread"]');
                            if (badge) {
                                const card = badge.closest('[role="row"]');
                                if (card) {
                                    card.click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        
                        if unread_clicked:
                            time.sleep(2.0)
                            
                            # Get chat name
                            chat_name = page.evaluate("""() => {
                                const header = document.querySelector('header');
                                if (header) {
                                    const span = header.querySelector('span[title]');
                                    return span ? span.getAttribute('title') : 'Unknown';
                                }
                                return 'Unknown';
                            }""")
                            
                            if chat_name and chat_name not in self.replied_to:
                                self._log(f"Auto-replying to new incoming message from '{chat_name}'...")
                                
                                # Input and send message
                                page.focus('div[contenteditable="true"]')
                                page.keyboard.type(self.auto_reply_message)
                                page.keyboard.press("Enter")
                                
                                self.replied_to.add(chat_name)
                                self._log(f"Replied successfully to '{chat_name}'!")
                                
                        time.sleep(5)
                    except Exception:
                        # loop warning silently
                        time.sleep(5)
                        
                context.close()
        except Exception as e:
            self._log(f"Crash in auto-reply loop: {e}")
            self.is_running = False

# Module level exports
def enable_whatsapp_auto_reply(message: str = "Pratik bhai abhi busy hain, baad mein baat karo, sir!", player=None) -> str:
    """Starts the auto-reply background service."""
    return WhatsAppAutoReplyService().start(message, player)

def disable_whatsapp_auto_reply(player=None) -> str:
    """Stops the auto-reply background service."""
    return WhatsAppAutoReplyService().stop()

def set_auto_reply_message(message: str, player=None) -> str:
    """Updates the message sent by the auto-reply service."""
    return WhatsAppAutoReplyService().set_message(message)

def get_auto_reply_status(player=None) -> str:
    """Returns current auto-reply service status and configured message."""
    service = WhatsAppAutoReplyService()
    status = "ACTIVE (Busy Mode)" if service.is_running else "INACTIVE"
    return f"WhatsApp Auto-Reply Status: {status} | Configured Message: '{service.auto_reply_message}', sir."

