import logging
import time
import mss
import pyautogui
import pyperclip
from PIL import Image
from google import genai
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

def auto_code_helper(parameters: dict, player=None) -> str:
    try:
        # Check if clipboard has highlighted text first by trying to copy
        original_clip = pyperclip.paste()
        pyperclip.copy("")
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.15)
        selected_text = pyperclip.paste().strip()
        pyperclip.copy(original_clip) # restore
        
        from main import _get_api_key
        client = genai.Client(api_key=_get_api_key())
        
        if selected_text:
            prompt = (
                "Identify any bugs, explain this code snippet, and provide a corrected version "
                f"with clear, developer-friendly comments in Hinglish:\n\n{selected_text}"
            )
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            return f"### [AUTO CODE HELPER] Explaining Selected Code:\n\n{response.text}"
            
        else:
            # Fallback to screenshot
            temp_screenshot = BASE_DIR / "data" / "code_helper_screen.png"
            temp_screenshot.parent.mkdir(parents=True, exist_ok=True)
            
            with mss.MSS() as sct:
                sct.shot(output=str(temp_screenshot))
                
            if not temp_screenshot.exists():
                return "Failed to capture screen screenshot, sir."
                
            img = Image.open(str(temp_screenshot))
            prompt = (
                "Look at this screenshot of the user's workspace. Locate any code editors, "
                "terminal tracebacks, or error logs. Identify what the code does or what the error "
                "means, and suggest the exact lines and values to modify to fix it. "
                "Respond in helpful developer-friendly Hinglish."
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[img, prompt]
            )
            
            try:
                temp_screenshot.unlink()
            except Exception as _exc:  # noqa: BLE001
                logging.debug("[%s] Suppressed: %s", __name__, _exc)
                
            return f"### [AUTO CODE HELPER] Screen Capture Analysis:\n\n{response.text}"
            
    except Exception as e:
        return f"Auto code helper failed: {e}, sir."
