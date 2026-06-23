"""
sentiment_analyzer.py — Real-time Emotion & Sentiment Detection

Analyzes user tone and adapts AI responses accordingly.
"""

from typing import Dict, Tuple
import re


class SentimentAnalyzer:
    """Analyzes sentiment and emotion in text."""
    
    # Lexicon for sentiment scoring
    POSITIVE_WORDS = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic", 
        "love", "happy", "awesome", "perfect", "brilliant", "glad"
    }
    
    NEGATIVE_WORDS = {
        "bad", "terrible", "awful", "hate", "angry", "sad", "frustrated",
        "annoyed", "disappointed", "useless", "horrible", "pathetic"
    }
    
    URGENT_WORDS = {
        "urgent", "asap", "emergency", "critical", "help", "stuck", "broken",
        "error", "crash", "fail", "immediately", "now", "quick"
    }
    
    def analyze(self, text: str) -> Dict[str, any]:
        """Analyze sentiment and emotion in text."""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        positive_count = sum(1 for w in words if w in self.POSITIVE_WORDS)
        negative_count = sum(1 for w in words if w in self.NEGATIVE_WORDS)
        urgent_count = sum(1 for w in words if w in self.URGENT_WORDS)
        
        # Calculate sentiment score (-1 to 1)
        total_sentiment = len(words)
        if total_sentiment == 0:
            sentiment_score = 0
        else:
            sentiment_score = (positive_count - negative_count) / total_sentiment
        
        # Determine emotion
        if urgent_count > 2:
            emotion = "urgent"
        elif sentiment_score > 0.5:
            emotion = "positive"
        elif sentiment_score < -0.5:
            emotion = "negative"
        elif "?" in text:
            emotion = "curious"
        elif "!" in text:
            emotion = "excited"
        else:
            emotion = "neutral"
        
        return {
            "emotion": emotion,
            "sentiment_score": round(sentiment_score, 2),
            "positive_words": positive_count,
            "negative_words": negative_count,
            "urgency": "high" if urgent_count > 2 else "normal",
            "confidence": min(100, (positive_count + negative_count) * 10)
        }
    
    def get_response_tone(self, sentiment: Dict) -> str:
        """Suggest response tone based on sentiment."""
        if sentiment["emotion"] == "urgent":
            return "concise and actionable"
        elif sentiment["emotion"] == "positive":
            return "enthusiastic and encouraging"
        elif sentiment["emotion"] == "negative":
            return "empathetic and helpful"
        elif sentiment["emotion"] == "curious":
            return "informative and detailed"
        else:
            return "professional and balanced"


analyzer = SentimentAnalyzer()
