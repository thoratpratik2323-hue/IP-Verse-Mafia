from google import genai
from memory.config_manager import get_gemini_key

def detect_emotion(text: str) -> str:
    """
    Analyzes the emotion in the given text using Gemini.
    """
    if not text or not text.strip():
        return "neutral"
    api_key = get_gemini_key()
    if not api_key:
        return "neutral"
    try:
        client = genai.Client(api_key=api_key)
        prompt = f"""Analyze the emotion in this text. Reply with only one word from: 
        [happy, sad, angry, stressed, excited, confused, neutral]
        
        Text: {text}"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        emotion = response.text.strip().lower()
        # Clean up in case Gemini returns extra characters (e.g. quotes or markdown)
        for e in ["happy", "sad", "angry", "stressed", "excited", "confused", "neutral"]:
            if e in emotion:
                return e
        return "neutral"
    except Exception as e:
        print(f"[Emotion Detection] Error: {e}")
        return "neutral"

def adapt_response_for_emotion(emotion: str, response: str) -> str:
    """
    Prepends a supportive/contextual Hinglish or English prefix depending on the user's emotion.
    """
    prefixes = {
        "stressed": "Hey, relax. ",
        "sad": "I'm here for you. ",
        "confused": "Let me explain clearly. ",
        "excited": "Love the energy! ",
        "angry": "I understand. Let me help. ",
    }
    prefix = prefixes.get(emotion, "")
    return prefix + response
