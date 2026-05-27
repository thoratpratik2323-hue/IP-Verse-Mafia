import os
import json
from pathlib import Path
import pyautogui
from PIL import Image
from google import genai
from google.genai import types

BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"
TEMP_DIR = BASE_DIR / "memory"

def _get_gemini_client() -> genai.Client:
    """Loads API key and returns a Gemini Client."""
    try:
        with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
            api_key = json.load(f)["gemini_api_key"]
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[Screen Vision] Error loading key: {e}")
        raise ValueError("Gemini API key not configured properly in config/api_keys.json")

def capture_and_analyze_screen(prompt: str = "Explain what is currently on my screen.") -> str:
    """Captures a fullscreen screenshot and uses Gemini 2.5 Flash's multimodal model to analyze it."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = TEMP_DIR / "temp_screen.png"
    
    try:
        # Take screenshot
        screenshot = pyautogui.screenshot()
        screenshot.save(temp_path)
    except Exception as e:
        return f"Error capturing screenshot: {e}"
        
    try:
        client = _get_gemini_client()
        image = Image.open(temp_path)
        
        system_instruction = """You are IP PRIME's Visual Screen Assistant. 
You will be provided with a screenshot of the user's desktop/application and a prompt. 
Analyze the image with absolute precision. Describe what you see, transcribe any errors, and offer clear, concise solutions or insights. 
Use clean markdown to present your answer."""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        
        # Safely clean up screenshot file
        try:
            image.close()
            os.remove(temp_path)
        except Exception:
            pass
            
        return response.text
    except Exception as e:
        # Cleanup fallback
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return f"Error analyzing screenshot with Gemini Vision: {e}"

def screen_peel_to_code(prompt: str = "Extract all text, code, and UI elements from this screenshot and convert them into clean code/text.") -> str:
    """Screen Peeler: OCR & UI-to-Code generator using Gemini Vision."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = TEMP_DIR / "temp_peel.png"
    
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(temp_path)
    except Exception as e:
        return f"Peel Error (Screenshot failed): {e}"
        
    try:
        client = _get_gemini_client()
        image = Image.open(temp_path)
        
        system_instruction = """You are the Screen Peeler. Extract all text and code from the provided screenshot.
If it is a UI, convert it to clean HTML/Tailwind or React code. If it is raw text or a document, transcribe it perfectly.
Output ONLY the requested code or text. DO NOT output conversational filler."""
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1
            )
        )
        
        try:
            image.close()
            os.remove(temp_path)
        except Exception:
            pass
            
        return response.text
    except Exception as e:
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return f"Peel Error (Vision processing failed): {e}"
