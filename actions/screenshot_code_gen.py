import os
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path
from PIL import Image

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"
OUTPUT_DIR = Path(r"C:\Users\thora\Downloads\IP Given\code")

def _get_gemini_client():
    """Loads API key and returns a UnifiedModelClient configured for vision tasks."""
    try:
        from actions.prime_utils import UnifiedModelClient
        return UnifiedModelClient(category="vision")
    except Exception as e:
        print(f"[ScreenshotCodeGen] Error loading unified client: {e}")
    return None

def _capture_screenshot(save_path: Path) -> bool:
    """Captures a fullscreen screenshot using PyAutoGUI or PIL fallback."""
    # Try PyAutoGUI first
    try:
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot.save(save_path)
        return True
    except Exception as e:
        print(f"[ScreenshotCodeGen] PyAutoGUI capture failed, trying PIL: {e}")
        
    # Fallback to PIL ImageGrab (excellent on Windows)
    try:
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        screenshot.save(save_path)
        return True
    except Exception as e:
        print(f"[ScreenshotCodeGen] PIL ImageGrab capture failed, trying mss: {e}")
        
    # Fallback to mss
    try:
        from mss import mss
        with mss() as sct:
            sct.shot(output=str(save_path))
            return True
    except Exception as e:
        print(f"[ScreenshotCodeGen] mss capture failed: {e}")
        
    return False

def screenshot_to_code(target: str = 'screen', language: str = 'html', framework: str = 'vanilla', save: bool = True, player=None) -> str:
    """Captures the current screen and uses Gemini 2.5 Flash Vision to write production-ready code."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API key not configured properly, sir."
        
    # Ensure temp dir exists
    temp_dir = BASE_DIR / "memory"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = temp_dir / "temp_screenshot_clone.png"
    
    if player:
        player.write_thought("Capturing screen screenshot...")
        
    if not _capture_screenshot(temp_path):
        return "Failed to capture screenshot, sir."
        
    try:
        image = Image.open(temp_path)
        
        system_instruction = (
            "You are an elite front-end developer and designer. "
            "Analyze the provided screenshot of a UI/screen. "
            f"Generate production-ready, clean, well-structured, modern {language} code that recreates this interface as closely as possible. "
            f"Styling Framework / Options: {framework}. "
            "Ensure all colors, sizing, spacing, positioning, and layouts match precisely. "
            "Include inline or internal styles, responsiveness, and modern interactive hover effects. "
            "Return ONLY the raw production-ready source code. Do NOT output markdown backticks (like ```html or ```), explanations, or comments."
        )
        
        prompt = f"Convert this screen design into clean {language} code using {framework} framework. Make it feel alive and beautiful, sir."
        
        if player:
            player.write_thought("Sending screenshot to Gemini for visual analysis and code generation...")
            
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        
        # Clean response code
        code_content = response.text.strip()
        if "```" in code_content:
            code_content = code_content.replace(f"```{language}", "").replace("```html", "").replace("```", "").strip()
            
        # Clean up temp image
        try:
            image.close()
            os.remove(temp_path)
        except Exception:
            pass
            
        if not code_content:
            return "Gemini generated empty code, sir."
            
        # Determine extension
        ext = "html"
        if "react" in language.lower():
            ext = "jsx"
        elif "vue" in language.lower():
            ext = "vue"
        elif "css" in language.lower():
            ext = "css"
        elif "javascript" in language.lower() or "js" in language.lower():
            ext = "js"
            
        # Save output
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screen_clone_{timestamp}.{ext}"
        filepath = OUTPUT_DIR / filename
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(code_content)
            
        result_msg = (
            f"### [CLONE] Screen-to-Code Clone Complete!\n"
            f"Pratik Sir, I successfully captured your screen, analyzed the UI design, and generated high-quality {language} code!\n\n"
            f"- **Saved Path**: `{filepath}`\n"
            f"- **Framework used**: {framework}\n"
            f"- **File Size**: {len(code_content)} bytes\n\n"
            "Code has been formatted and saved successfully, sir!"
        )
        
        if save:
            if player:
                player.write_thought("Launching notepad to show the generated code...")
            try:
                subprocess.Popen(["notepad.exe", str(filepath)])
            except Exception as ne:
                result_msg += f"\n*(Failed to open in Notepad automatically: {ne})*"
                
        return result_msg
        
    except Exception as e:
        # Clean up temp image if error
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return f"Error during UI conversion: {e}, sir."

def clone_ui_from_url(url: str, language: str = 'html', framework: str = 'vanilla', player=None) -> str:
    """Opens a URL using browser_control and clones its interface."""
    if not url:
        return "URL cannot be empty, sir."
        
    try:
        from actions.browser_control import browser_control
        
        if player:
            player.write_thought(f"Navigating to URL '{url}' via browser control to render visual UI...")
            
        # Call browser_control to navigate
        nav_params = {"action": "navigate", "url": url}
        # browser_control is usually synchronous and starts a Playwright page
        browser_control(nav_params, player)
        
        # Give it a few seconds to load completely
        if player:
            player.write_thought("Waiting 4 seconds for UI assets and scripts to render...")
        time.sleep(4)
        
        # Take a screenshot of the active screen (which now displays the browser window) and convert it
        return screenshot_to_code(target='screen', language=language, framework=framework, save=True, player=player)
        
    except Exception as e:
        return f"Error cloning UI from URL '{url}': {e}, sir."

def screenshot_code_gen(parameters: dict, player=None) -> str:
    """Dispatcher for screen-to-code cloning tool."""
    action = parameters.get("action", "capture").lower().strip()
    language = parameters.get("language", "html").lower().strip()
    framework = parameters.get("framework", "vanilla").lower().strip()
    url = parameters.get("url", "")
    save = parameters.get("save", True)
    if isinstance(save, str):
        save = save.lower().strip() in ["true", "yes", "1"]
        
    if action == "capture":
        return screenshot_to_code(target='screen', language=language, framework=framework, save=save, player=player)
    elif action == "clone_url":
        return clone_ui_from_url(url, language=language, framework=framework, player=player)
    else:
        return f"Unknown action '{action}' for Screenshot Code Gen, sir."
