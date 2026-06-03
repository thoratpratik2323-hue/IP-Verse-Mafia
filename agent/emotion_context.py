import json
import re
from google import genai
from typing import Dict, Any

from actions.prime_utils import get_api_key
from memory.autonomous_memory import AutonomousMemory

class EmotionContextDetector:
    """
    Detects user emotion and context from text/voice, and adjusts the AI's behavior accordingly.
    """
    def __init__(self, memory_system: AutonomousMemory):
        self.memory = memory_system
        self._client = genai.Client(api_key=get_api_key())
        self._model_name = "gemini-2.5-flash-lite"
        
    def analyze_input(self, text: str) -> Dict[str, Any]:
        """
        Analyzes user input to determine mood and context.
        Returns a dictionary with 'mood', 'confidence', and 'suggested_adaptation'.
        """
        prompt = f"""You are an Emotion and Context Detection Engine for IP Prime.
Analyze the user's input and determine their emotional state.

Input: "{text}"

Determine:
1. Mood: (e.g., Stressed, Happy, Focused, Frustrated, Tired, Neutral)
2. Confidence: (High, Medium, Low)
3. Suggested Adaptation: How should IP Prime respond? (e.g., "Be concise and calm", "Be energetic and proactive")

Return ONLY valid JSON:
{{
  "mood": "Stressed",
  "confidence": "High",
  "suggested_adaptation": "Be concise and calm. Suggest taking a break."
}}
"""
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=prompt
            )
            result_text = response.text.strip()
            text_json = re.sub(r"```(?:json)?", "", result_text).strip().rstrip("`").strip()
            
            result = json.loads(text_json)
            print(f"[EmotionContext] 🎭 Detected Mood: {result.get('mood')} ({result.get('confidence')} confidence)")
            
            # Save emotional state to long-term memory pattern
            self._record_mood(result.get('mood'))
            
            return result
        except Exception as e:
            print(f"[EmotionContext] ⚠️ Emotion detection failed: {e}")
            return {"mood": "Neutral", "confidence": "Low", "suggested_adaptation": "Be helpful."}

    def _record_mood(self, mood: str):
        """Records the mood into preferences/long-term memory to detect patterns over time."""
        if not mood or mood == "Neutral":
            return
            
        current_moods = self.memory.recall_preferences().get("frequent_moods", {})
        if isinstance(current_moods, str):
            try:
                current_moods = json.loads(current_moods)
            except:
                current_moods = {}
                
        current_moods[mood] = current_moods.get(mood, 0) + 1
        
        self.memory.learn_preference("frequent_moods", json.dumps(current_moods))
        
    def get_behavioral_context(self, current_mood_data: Dict[str, Any] = None) -> str:
        """
        Generates a context string to inject into the planner/executor based on mood.
        """
        context = ""
        if current_mood_data:
            adaptation = current_mood_data.get("suggested_adaptation", "")
            if adaptation:
                context += f"\nEMOTIONAL CONTEXT: The user is currently {current_mood_data.get('mood')}. {adaptation}\n"
                
        # Inject long term emotional patterns
        frequent_moods = self.memory.recall_preferences().get("frequent_moods")
        if frequent_moods:
            try:
                moods_dict = json.loads(frequent_moods) if isinstance(frequent_moods, str) else frequent_moods
                if isinstance(moods_dict, dict) and moods_dict:
                    top_mood = max(moods_dict.items(), key=lambda x: x[1])[0]
                    context += f"\nHISTORICAL CONTEXT: The user is frequently {top_mood}. Keep this in mind for proactive suggestions.\n"
            except:
                pass
                
        return context
