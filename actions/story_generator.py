"""
story_generator.py — AI-Generated Interactive Stories

Create and play interactive AI-generated stories.
"""

from typing import Dict, List, Any, Optional
import random


class StoryGenerator:
    """Generates interactive AI stories."""
    
    def __init__(self):
        self.genres = ["fantasy", "sci-fi", "mystery", "adventure", "romance", "horror", "comedy"]
        self.current_story = None
        self.story_history = []
    
    def generate_story_premise(self, genre: str = "fantasy", protagonist: str = "You", 
                              setting: str = None) -> Dict[str, str]:
        """Generate story premise and opening."""
        
        premises = {
            "fantasy": f"You awaken in {setting or 'an ancient forest'} with no memory of how you got there. A mysterious figure approaches...",
            "sci-fi": f"Your spaceship crashes on {setting or 'an unknown planet'}. Amidst the wreckage, you find something unexpected...",
            "mystery": f"A cryptic message arrives: 'The truth is hidden in {setting or 'the old mansion'}'...",
            "adventure": f"You discover an old map in {setting or 'your attic'} pointing to treasure...",
            "romance": f"A stranger walks into {setting or 'your life'} and everything changes...",
            "horror": f"You're alone in {setting or 'an abandoned building'} when you hear something..."
        }
        
        return {
            "genre": genre,
            "protagonist": protagonist,
            "setting": setting,
            "opening": premises.get(genre.lower(), premises["fantasy"]),
            "chapters_so_far": 1
        }
    
    def generate_story(self, prompt: str, genre: str = "fantasy", 
                      max_words: int = 500) -> Dict[str, Any]:
        """Generate a complete short story."""
        
        # Simulate story generation (in real implementation, would use AI)
        story_structure = [
            "Once upon a time...",
            f"[Story about: {prompt}]",
            "[Challenge or conflict develops...]",
            "[Resolution or twist...]",
            "And so the story goes on..."
        ]
        
        return {
            "genre": genre,
            "prompt": prompt,
            "story": "\n\n".join(story_structure),
            "word_count": max_words,
            "estimated_read_time": f"{max(1, max_words // 200)} minutes"
        }
    
    def create_interactive_story(self, title: str, opening: str) -> Dict[str, Any]:
        """Create an interactive story with choices."""
        
        self.current_story = {
            "title": title,
            "opening": opening,
            "chapters": [{"text": opening, "choices": []}],
            "current_chapter": 0,
            "player_choices": []
        }
        
        return {
            "story_title": title,
            "chapter": 1,
            "text": opening,
            "choices": self._generate_choices(opening)
        }
    
    def _generate_choices(self, text: str) -> List[Dict]:
        """Generate story choices based on current text."""
        return [
            {"id": 1, "text": "Continue cautiously", "outcome": "careful"},
            {"id": 2, "text": "Act boldly", "outcome": "bold"},
            {"id": 3, "text": "Seek help", "outcome": "cooperative"},
            {"id": 4, "text": "Examine surroundings", "outcome": "investigative"}
        ]
    
    def make_choice(self, choice_id: int) -> Dict[str, Any]:
        """Process player choice and continue story."""
        
        if not self.current_story:
            return {"error": "No story in progress"}
        
        outcomes = {
            "careful": "You proceed slowly and observe everything carefully. Suddenly...",
            "bold": "You charge forward confidently. This catches attention of...",
            "cooperative": "You look for allies. A figure emerges from shadows...",
            "investigative": "You examine every detail. You discover..."
        }
        
        choice = self._get_choice(choice_id)
        if not choice:
            return {"error": "Invalid choice"}
        
        new_text = outcomes.get(choice["outcome"], "Something unexpected happens...")
        
        self.current_story["chapters"].append({
            "text": new_text,
            "player_choice": choice["text"]
        })
        self.current_story["player_choices"].append(choice_id)
        self.current_story["current_chapter"] += 1
        
        return {
            "chapter": self.current_story["current_chapter"] + 1,
            "text": new_text,
            "choices": self._generate_choices(new_text),
            "choices_made": len(self.current_story["player_choices"])
        }
    
    def _get_choice(self, choice_id: int) -> Optional[Dict]:
        """Get a specific choice."""
        choices = self._generate_choices("")
        return next((c for c in choices if c["id"] == choice_id), None)
    
    def get_story_summary(self) -> Dict[str, Any]:
        """Get summary of current story."""
        if not self.current_story:
            return {"error": "No story in progress"}
        
        return {
            "title": self.current_story["title"],
            "chapters_completed": len(self.current_story["chapters"]),
            "choices_made": len(self.current_story["player_choices"]),
            "current_position": self.current_story["current_chapter"]
        }
    
    def save_story(self) -> bool:
        """Save current story."""
        if self.current_story:
            self.story_history.append(self.current_story)
            return True
        return False
    
    def get_story_ideas(self, genre: str = None) -> List[str]:
        """Get creative story ideas."""
        
        ideas = {
            "fantasy": [
                "A hero discovers they're actually the villain",
                "Magic is forbidden but you're awakening powers",
                "You must save a world you never knew existed"
            ],
            "sci-fi": [
                "You're the last human in a robot civilization",
                "Time travel reveals you're your own ancestor",
                "Your consciousness is copied to a spaceship"
            ],
            "mystery": [
                "Your reflection is one day older than you",
                "Every suspect has a perfect alibi... except one",
                "The victim is still alive but nobody remembers them"
            ]
        }
        
        selected = ideas.get(genre or "fantasy", [])
        return selected or list(ideas.values())[0]
    
    def generate_character(self, archetype: str = "hero") -> Dict[str, str]:
        """Generate a character for the story."""
        
        traits = ["mysterious", "loyal", "cunning", "brave", "witty", "melancholic"]
        motivations = ["revenge", "love", "redemption", "knowledge", "power", "freedom"]
        
        return {
            "archetype": archetype,
            "trait": random.choice(traits),
            "motivation": random.choice(motivations),
            "flaw": random.choice(traits),
            "strength": random.choice(traits)
        }


generator = StoryGenerator()
