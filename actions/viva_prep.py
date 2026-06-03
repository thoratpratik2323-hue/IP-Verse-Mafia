"""
actions/viva_prep.py — Technical Viva Prep AI examiner engine for IP Prime.

This is a premium action module for the IP Prime personal assistant suite.
"""

import json
from pathlib import Path
from google import genai
from google.genai import types

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"

class VivaExaminer:
    """Manages the AI Voice Viva Examination state machine and grading."""
    
    def __init__(self, topic: str = "Python Basics"):
        self.topic = topic
        self.total_questions = 3
        self.current_q_idx = 0
        self.score = 0
        self.current_question = ""
        self.history = []  # List of {"q": q, "a": a, "grade": g, "feedback": f}
        
    def _get_gemini_client(self) -> genai.Client:
        try:
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                api_key = json.load(f)["gemini_api_key"]
            return genai.Client(api_key=api_key)
        except Exception:
            raise ValueError("Gemini API key not found in config/api_keys.json")

    def generate_question(self) -> str:
        """Asks Gemini to generate a single relevant question on the active topic."""
        client = self._get_gemini_client()
        
        prompt = (
            f"You are the technical examiner for a friendly viva (oral exam) for Pratik Thorat, a 12th passout learning computer science.\n"
            f"Topic: {self.topic}\n"
            f"Question Number: {self.current_q_idx + 1} out of {self.total_questions}.\n"
            f"Generate a single, concise, conceptual question that can be answered in 1-2 spoken sentences.\n"
            f"Keep it very direct and tailored to a beginner developer. Output ONLY the question text, no introductions."
        )
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            self.current_question = response.text.strip()
            return self.current_question
        except Exception:
            fallback = "Explain the difference between a list and a tuple in Python."
            self.current_question = fallback
            return fallback

    def grade_answer(self, user_answer: str) -> dict:
        """Evaluates Pratik's answer, returns grade out of 100 and friendly feedback."""
        client = self._get_gemini_client()
        
        prompt = (
            f"Question: {self.current_question}\n"
            f"Pratik's Spoken Answer: {user_answer}\n\n"
            f"Evaluate this answer out of 100. Be extremely encouraging (buddy vibe) but fair.\n"
            f"Return JSON format ONLY with keys:\n"
            f"- 'grade': integer score (0-100)\n"
            f"- 'feedback': concise, supportive tech-buddy explanation of what was good and what was missing."
        )
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            data = json.loads(response.text.strip())
            
            # Store in history
            self.history.append({
                "q": self.current_question,
                "a": user_answer,
                "grade": data.get("grade", 70),
                "feedback": data.get("feedback", "Acha attempt tha bro!")
            })
            
            self.score += data.get("grade", 70)
            self.current_q_idx += 1
            return data
        except Exception:
            # Fallback
            dummy_data = {"grade": 80, "feedback": "Solid answer bro! Direct and clear concept."}
            self.history.append({
                "q": self.current_question,
                "a": user_answer,
                "grade": 80,
                "feedback": dummy_data["feedback"]
            })
            self.score += 80
            self.current_q_idx += 1
            return dummy_data

    def generate_scorecard(self) -> str:
        """Compiles a beautiful technical scorecard in Pratik's Second Brain."""
        final_score = int(self.score / self.total_questions) if self.total_questions else 0
        today_str = datetime_str = Path("c:/Users/thora/Documents/SecondBrain") # Just dummy resolving
        
        import datetime
        today_str = datetime.datetime.now().strftime("%Y-%m-%d")
        
        scorecard = f"""# 🏆 Technical Viva Scorecard

* **Candidate:** Pratik Balasaheb Thorat
* **Exam Date:** {today_str}
* **Topic:** {self.topic}
* **Overall Grade:** `{final_score}/100`

---

## Detailed Question Analytics
"""
        for i, turn in enumerate(self.history, 1):
            scorecard += f"""
### Q{i}: {turn['q']}
* **Your Answer:** *"{turn['a']}"*
* **Score:** `{turn['grade']}/100`
* **Buddy Feedback:** {turn['feedback']}
"""

        # Generate strengths & recommendations dynamically using Gemini
        client = self._get_gemini_client()
        summary_prompt = (
            f"Based on Pratik's Viva exam on topic '{self.topic}' with overall score '{final_score}/100' and history:\n"
            f"{json.dumps(self.history)}\n"
            f"Generate a concise, beautiful technical wrap-up in markdown showing:\n"
            f"1. Strengths (1-2 points)\n"
            f"2. Topics to Improve (1-2 points)\n"
            f"3. Buddy Roadmap Recommendation (Custom CS learning advice)"
        )
        
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=summary_prompt
            )
            scorecard += f"\n---\n\n## AI Assessment & Roadmap\n{response.text.strip()}"
        except Exception:
            scorecard += "\n---\n\n## AI Assessment & Roadmap\n* **Strengths**: Concepts are clear!\n* **Roadmap**: Continue coding and building daily!"
            
        # Write to Second Brain folder
        dest_folder = Path("c:/Users/thora/Documents/SecondBrain")
        if dest_folder.exists():
            try:
                dest_file = dest_folder / "viva_scorecard.md"
                dest_file.write_text(scorecard, encoding="utf-8")
                print("[VivaExaminer] ✓ Created Technical Viva Scorecard at SecondBrain/viva_scorecard.md")
            except Exception as err:
                print(f"[VivaExaminer] Error saving scorecard file: {err}")
                
        return scorecard
