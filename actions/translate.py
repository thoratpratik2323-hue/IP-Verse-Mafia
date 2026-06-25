from google import genai
from memory.config_manager import get_gemini_key

def detect_language(text: str) -> str:
    """
    Detects the primary language of the input text using Gemini.
    """
    if not text or not text.strip():
        return "English"
    api_key = get_gemini_key()
    if not api_key:
        return "English"
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"Identify the primary language of this text. Reply with ONLY the language name (e.g. English, Hindi, Spanish, French, German):\n\n{text}"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        lang = response.text.strip().capitalize()
        return lang
    except Exception as e:
        print(f"[LangDetect] Error: {e}")
        return "English"

def translate_text(text: str, target_lang: str = "English") -> str:
    """
    Translates input text to target language using Gemini.
    """
    if not text or not text.strip():
        return ""
    api_key = get_gemini_key()
    if not api_key:
        return text
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"Translate this to {target_lang}. Only return the translated text, nothing else:\n\n{text}"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        print(f"[Translation] Error: {e}")
        return text
