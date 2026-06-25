import pyautogui
import pyperclip
import time
from google import genai

def voice_to_code(parameters: dict, player=None) -> str:
    instruction = parameters.get("instruction", "").strip()
    if not instruction:
        return "Please tell me what code you want to generate, sir."
        
    try:
        from main import _get_api_key
        client = genai.Client(api_key=_get_api_key())
        
        prompt = (
            "Write the code matching this request. Return only the raw code snippet. "
            "Do not include explanation, introduction, markdown code block fences (like ```python or ```), "
            f"or conversational dialogue. Here is the instruction: {instruction}"
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        code = response.text.strip()
        # Fallback strip of backticks
        if code.startswith("```"):
            lines = code.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            code = "\n".join(lines).strip()
            
        if not code:
            return "No code could be generated, sir."
            
        # Store code, paste, restore clipboard
        original_clip = pyperclip.paste()
        pyperclip.copy(code)
        
        # Give user time to make sure cursor is in correct place
        time.sleep(0.5)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.2)
        pyperclip.copy(original_clip)
        
        return "Code generated and pasted successfully, sir!"
        
    except Exception as e:
        return f"Failed to generate or paste code: {e}, sir."
