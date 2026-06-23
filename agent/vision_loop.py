import time
import json
from pathlib import Path
from actions.prime_utils import UnifiedModelClient

try:
    import pyautogui
except ImportError:
    pyautogui = None

def safe_print(msg: str):
    try:
        print(msg)
    except UnicodeEncodeError:
        try:
            print(msg.encode('ascii', errors='replace').decode('ascii'))
        except Exception:
            pass

class VisionLoop:
    """
    Phase 4: Proactive Computer Vision Loop.
    Captures and analyzes screenshots periodically to detect errors, blocked states, or deadlines.
    """
    def __init__(self, core_engine):
        self.core = core_engine
        self.last_vision_run = 0
        self._init_session()

    def _init_session(self):
        try:
            self.client = UnifiedModelClient(category="vision")
        except Exception:
            self.client = None

    def _reconnect_with_backoff(self, attempt):
        wait = min(2 ** attempt, 300)  # Max 5 min wait
        time.sleep(wait)
        self._init_session()

    def proactive_screen_watch(self) -> str:
        """Captures screen and analyzes with Gemini Vision under rate-safe thresholds."""
        if not pyautogui:
            return "PyAutoGUI not installed, skipping vision capture."
        if not self.client:
            return "API Key not loaded, skipping vision loop."
            
        current_time = time.time()
        
        # Option B: Proactive Screen Crash Auditor
        # Detect active window foreground app to dynamically scale loop speed.
        from actions.screen_time import get_active_window_app
        active_app = get_active_window_app().lower()
        dev_apps = ["code", "cursor", "pycharm", "cmd", "powershell", "python", "terminal", "bash", "sh", "zsh", "windowsterminal"]
        is_dev = any(dev_app in active_app for dev_app in dev_apps)
        
        # 3 minutes (180 seconds) for dev tools, 60 minutes (3600 seconds) otherwise
        interval = 180 if is_dev else 3600
        if getattr(self.core, "power_save_mode", False):
            interval *= 5  # Scale down frequency by 5x (15 minutes for dev, 5 hours for general)
        
        if current_time - self.last_vision_run < interval:
            return f"Vision loop rate-limited (runs once every {interval // 60} minutes)."
            
        self.last_vision_run = current_time
        msg = f"[VisionLoop] 👁️ Capturing proactive screenshot for visual diagnostic (Active app: '{active_app}')..."
        safe_print(msg)
        
        screenshot_path = Path.home() / ".ipprime" / "vision_temp.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(str(screenshot_path))
            
            # Analyze screenshot using Gemini Vision
            image_bytes = screenshot_path.read_bytes()
            
            prompt = """You are the Proactive Computer Vision Agent for IP Prime.
Analyze the user's active screen layout.
Identify if:
1. There is an active programming error, syntax traceback, compilation failure, compiler/interpreter crash, or traceback visible in terminal or code editor.
2. The user seems stuck on a specific code block (e.g. staring at an empty file or long-standing error).
3. There are important calendar notifications or alerts on the screen.

If a traceback/compilation/syntax error is visible, specify detailed recovery commands or steps under 'recommended_action' (e.g., 'run claude_code to fix X in file Y'). Ensure issues_detected is set to true.

Return a strict JSON response:
{
  "issues_detected": true/false,
  "issue_description": "Description of error or stuck state, if any",
  "recommended_action": "Suggested plan or CLI command to offer help, if any"
}
Do NOT include markdown blocks. Return only raw JSON."""

            response = self.client.models.generate_content(
                model=None,
                contents=[
                    {"inline_data": {"mime_type": "image/png", "data": image_bytes}},
                    prompt
                ]
            )
            
            result = response.text.strip()
            # Robust JSON extraction — strip markdown fences and grab first valid JSON object
            import re
            # Remove markdown code fences if present
            result = re.sub(r"```json\s*", "", result)
            result = re.sub(r"```\s*", "", result)
            result = result.strip()
            # Extract first {...} JSON block to avoid "Extra data" errors
            json_match = re.search(r'\{.*?\}', result, re.DOTALL)
            if json_match:
                result = json_match.group(0)
            data = json.loads(result)
            
            # Clean up temp file
            if screenshot_path.exists():
                screenshot_path.unlink()
                
            if data.get("issues_detected"):
                desc = data.get("issue_description")
                act = data.get("recommended_action")
                safe_print(f"[VisionLoop] 👁️ Screen Issue Detected: '{desc}'")
                
                # Proactively register a recovery task!
                self.core.add_goal(
                    f"Offer dynamic assistant help to Pratik Sir for: '{desc}'. Recommendation: '{act}'",
                    context=f"Proactive vision analysis of screen detected an active issue: {desc}",
                    priority=1
                )
                return f"Issue registered: {desc}"
            
            return "Screen clean. No issues detected."
            
        except Exception as e:
            # Safe cleanup fallback
            if screenshot_path.exists():
                try:
                    screenshot_path.unlink()
                except Exception:
                    pass
            safe_print(f"[VisionLoop] ⚠️ Vision diagnostic loop failed: {e}")
            return f"Vision loop failed: {e}"
