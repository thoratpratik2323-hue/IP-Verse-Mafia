import time
import json
from pathlib import Path
from actions.prime_utils import UnifiedModelClient

try:
    import pyautogui
except ImportError:
    pyautogui = None

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
        # Enforce highly strict 60 minutes interval to protect Gemini API rate limits and CPU resources
        if current_time - self.last_vision_run < 3600:
            return "Vision loop rate-limited (runs once every 60 minutes)."
            
        self.last_vision_run = current_time
        print("[VisionLoop] 👁️ Capturing proactive screenshot for visual diagnostic...")
        
        screenshot_path = Path.home() / ".ipprime" / "vision_temp.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            screenshot = pyautogui.screenshot()
            screenshot.save(str(screenshot_path))
            
            # Analyze screenshot using Gemini 2.5 Flash
            image_bytes = screenshot_path.read_bytes()
            
            prompt = """You are the Proactive Computer Vision Agent for IP Prime.
Analyze the user's active screen layout.
Identify if:
1. There is an active programming error, syntax traceback, compilation failure, or crash visible.
2. The user seems stuck on a specific code block (e.g. staring at an empty file or long-standing error).
3. There are important calendar notifications or alerts on the screen.

Return a strict JSON response:
{
  "issues_detected": true/false,
  "issue_description": "Description of error or stuck state, if any",
  "recommended_action": "Suggested plan to offer help, if any"
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
            if "```" in result:
                result = result.replace("```json", "").replace("```", "").strip()
                
            data = json.loads(result)
            
            # Clean up temp file
            if screenshot_path.exists():
                screenshot_path.unlink()
                
            if data.get("issues_detected"):
                desc = data.get("issue_description")
                act = data.get("recommended_action")
                print(f"[VisionLoop] 👁️ Screen Issue Detected: '{desc}'")
                
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
            print(f"[VisionLoop] ⚠️ Vision diagnostic loop failed: {e}")
            return f"Vision loop failed: {e}"
