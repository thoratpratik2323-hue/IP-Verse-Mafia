from google import genai
from actions.prime_utils import get_api_key

class PerceptionEngine:
    """
    LAYER 2 - Perception Engine.
    IP Prime jo bhi input aata hai usse samjhta hai (Text, Voice, etc.)
    """
    
    def __init__(self):
        self.client = genai.Client(api_key=get_api_key())
        self.model_name = "gemini-2.5-flash-lite"
        
    def perceive(self, raw_input: str) -> dict:
        """Fully analyzes the input before any execution."""
        return {
            "type"     : self.detect_input_type(raw_input),
            "intent"   : self.extract_intent(raw_input),
            "emotion"  : self.detect_emotion(raw_input),
            "urgency"  : self.detect_urgency(raw_input),
            "context"  : self.get_context(raw_input),
            "entities" : self.extract_entities(raw_input)
        }
        
    def detect_input_type(self, text: str) -> str:
        """Determines if the input is a direct command, question, or casual chat."""
        # Simple heuristic or could use Gemini. Let's use simple heuristic for speed.
        text_lower = text.lower()
        if any(w in text_lower for w in ["what", "how", "why", "who", "when", "where", "?"]):
            return "QUESTION"
        if text_lower.startswith(("open", "close", "run", "do", "make", "create", "delete", "turn")):
            return "COMMAND"
        return "CHAT"
        
    def extract_intent(self, text: str) -> str:
        """Extracts the core intent."""
        # We can just return the text as the intent for now, or ask Gemini.
        return text
    
    def detect_emotion(self, text: str) -> str:
        """
        Detects user emotion using predefined keywords + Gemini fallback.
        """
        text_lower = text.lower()
        emotions = {
            "frustrated" : ["kaam nahi kar raha", "ugh", "bakwaas", "stupid", "not working", "fail"],
            "happy"      : ["thanks", "badiya", "achha", "good", "great", "awesome", "nice"],
            "stressed"   : ["jaldi", "urgent", "abhi", "please", "fast", "quick"],
            "confused"   : ["samjha nahi", "kya", "matlab", "how to", "help"],
            "tired"      : ["neend", "thaka", "kal karo", "exhausted", "sleep"]
        }
        
        for emo, words in emotions.items():
            if any(w in text_lower for w in words):
                return emo
                
        try:
            prompt = f"Analyze the emotion of this text. Return exactly one word from this list: [frustrated, happy, stressed, confused, tired, neutral]. Text: '{text}'"
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            res = response.text.strip().lower()
            if res in emotions or res == "neutral":
                return res
        except Exception:
            pass
            
        return "neutral"
    
    def detect_urgency(self, text: str) -> str:
        """
        High urgency = abhi karo
        Low urgency  = baad mein theek hai
        """
        urgent_words = ["abhi", "jaldi", "urgent", "asap", "immediately", "quick", "fast"]
        return "HIGH" if any(w in text.lower() for w in urgent_words) else "NORMAL"
        
    def get_context(self, text: str) -> str:
        """Extracts any situational context mentioned."""
        return "general" # Can be expanded with NLP
        
    def extract_entities(self, text: str) -> list:
        """Extracts names, places, dates, etc."""
        return [] # Can be expanded with NLP
