import json
import re
import google.generativeai as genai
from actions.prime_utils import get_api_key

class ReasoningEngine:
    """
    LAYER 4 - Reasoning Engine.
    Ye decide karta hai — kya karna hai, kaise karna hai.
    """
    
    def __init__(self, memory_engine):
        genai.configure(api_key=get_api_key())
        self.ai = genai.GenerativeModel("gemini-2.5-flash")
        self.memory = memory_engine
    
    def create_plan(self, goal: str, context: dict) -> dict:
        """
        Creates a JSON execution plan considering past experiences, emotion, and urgency.
        """
        # Pehle past experience dekho
        past = self.memory.recall_similar(goal)
        profile = self.memory.get_user_profile()
        
        from agent.skills_manager import format_tools_for_prompt
        available_tools = format_tools_for_prompt()
        
        prompt = f"""
        You are IP Prime's reasoning engine.
        
        USER GOAL: {goal}
        USER EMOTION: {context.get('emotion', 'neutral')}
        USER URGENCY: {context.get('urgency', 'NORMAL')}
        USER PROFILE: {profile}
        PAST SIMILAR TASKS: {past}
        
        AVAILABLE TOOLS:
        {available_tools}
        
        Create a step by step plan.
        Consider user's emotion and urgency.
        Learn from past experiences (avoid what failed, repeat what worked).
        You MUST use one of the AVAILABLE TOOLS in the 'action' field. If no tool fits perfectly, use 'generated_code'.
        
        Return ONLY valid JSON (no markdown):
        {{
            "understanding": "what user actually wants",
            "approach": "how to do it",
            "confidence": 0.95,
            "steps": [
                {{"action": "tool_name", "reason": "why", "parameters": {{"key":"val"}} }}
            ],
            "expected_time": "...",
            "things_to_avoid": ["..."]
        }}
        """
        
        try:
            response = self.ai.generate_content(prompt)
            result_text = response.text.strip()
            text_json = re.sub(r"```(?:json)?", "", result_text).strip().rstrip("`").strip()
            return json.loads(text_json)
        except Exception as e:
            print(f"[ReasoningEngine] ⚠️ Failed to generate reasoning plan: {e}")
            return {
                "understanding": goal,
                "approach": "Fallback direct execution",
                "confidence": 0.5,
                "steps": [{"action": "generated_code", "reason": "Fallback", "parameters": {"prompt": goal}}],
                "expected_time": "unknown",
                "things_to_avoid": []
            }
    
    def should_ask_or_assume(self, confidence: float) -> str:
        """
        Poochna chahiye ya assume kar lena chahiye?
        High confidence = assume karo, mat poochho
        Low confidence  = poochho
        """
        if confidence > 0.85:
            return "ASSUME"   # Seedha karo
        elif confidence > 0.60:
            return "INFORM"   # Karo lekin batao
        else:
            return "ASK"      # Poochho pehle
