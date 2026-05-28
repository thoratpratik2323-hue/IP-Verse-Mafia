class EmotionEngine:
    """
    LAYER 5 - Emotion Engine.
    User ki emotion samjho. Apna response accordingly badlo.
    """
    
    RESPONSE_STYLES = {
        "frustrated": {
            "tone": "calm, solution-focused",
            "speed": "fast",
            "extra": "acknowledge frustration first"
        },
        "happy": {
            "tone": "energetic, matching enthusiasm", 
            "speed": "normal",
            "extra": "keep the positive vibe"
        },
        "stressed": {
            "tone": "reassuring, break it down simply",
            "speed": "fast",
            "extra": "suggest taking a breath"
        },
        "confused": {
            "tone": "patient, very clear explanations",
            "speed": "slow",
            "extra": "use simple examples"
        },
        "tired": {
            "tone": "gentle, minimal",
            "speed": "slow", 
            "extra": "suggest rest if possible"
        }
    }
    
    def adapt_response(self, response: str, emotion: str) -> str:
        """Modifies the output text based on detected user emotion."""
        

        if emotion == "frustrated":
            return f"Samjha Pratik Sir, ye problem solve karte hain. {response}"
        
        if emotion == "tired":
            return f"Ye kar deta hoon. {response} \n\nAur thoda rest lo Sir. 😊"
        
        if emotion == "stressed":
            return f"Tension mat lo Sir, main hoon na. \n{response}"
            
        if emotion == "happy":
            return f"Arey waah Sir! {response}"
            
        if emotion == "confused":
            return f"Chaliye main isko ekdum simple karke samjhata hoon. {response}"
            
        return response
