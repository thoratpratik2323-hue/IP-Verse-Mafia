"""
quick_notes.py — Quick Voice-to-Text Notes with AI Organization

Capture thoughts quickly and auto-organize by topic.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional


class QuickNotes:
    """Rapid note-taking with auto-categorization."""
    
    def __init__(self, notes_dir: str = "memory/quick_notes"):
        self.notes_dir = Path(notes_dir)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_notes: List[Dict] = []
    
    def add_note(self, text: str, voice_input: bool = False) -> Dict[str, Any]:
        """Add a quick note."""
        timestamp = datetime.now()
        note = {
            "id": len(self.current_session_notes) + 1,
            "text": text,
            "timestamp": timestamp.isoformat(),
            "voice_input": voice_input,
            "category": self._auto_categorize(text),
            "tags": self._extract_tags(text)
        }
        
        self.current_session_notes.append(note)
        return note
    
    def _auto_categorize(self, text: str) -> str:
        """Automatically categorize note by content."""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["meeting", "call", "discuss", "talk", "agenda"]):
            return "meeting"
        elif any(word in text_lower for word in ["todo", "task", "do", "need to", "must", "reminder"]):
            return "todo"
        elif any(word in text_lower for word in ["idea", "thought", "concept", "think", "brainstorm"]):
            return "idea"
        elif any(word in text_lower for word in ["bug", "error", "issue", "fix", "problem"]):
            return "issue"
        elif any(word in text_lower for word in ["learn", "study", "research", "read", "tutorial"]):
            return "learning"
        elif any(word in text_lower for word in ["quote", "insight", "wisdom", "remember", "important"]):
            return "insight"
        else:
            return "general"
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract hashtags and important keywords."""
        import re
        
        # Extract hashtags
        hashtags = re.findall(r'#\w+', text)
        
        # Extract important keywords (all caps words)
        important = re.findall(r'\b[A-Z]{2,}\b', text)
        
        return hashtags + important
    
    def get_notes_by_category(self, category: str) -> List[Dict]:
        """Get all notes in a category."""
        return [n for n in self.current_session_notes if n["category"] == category]
    
    def search_notes(self, query: str) -> List[Dict]:
        """Search notes by text content."""
        query_lower = query.lower()
        return [n for n in self.current_session_notes 
                if query_lower in n["text"].lower()]
    
    def get_all_tags(self) -> Dict[str, int]:
        """Get all tags and their frequencies."""
        tag_count = {}
        for note in self.current_session_notes:
            for tag in note["tags"]:
                tag_count[tag] = tag_count.get(tag, 0) + 1
        return dict(sorted(tag_count.items(), key=lambda x: x[1], reverse=True))
    
    def export_notes(self, filename: Optional[str] = None) -> str:
        """Export notes to JSON file."""
        if not filename:
            filename = f"notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        filepath = self.notes_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "exported_at": datetime.now().isoformat(),
                "total_notes": len(self.current_session_notes),
                "notes": self.current_session_notes
            }, f, indent=2, ensure_ascii=False)
        
        return str(filepath)
    
    def export_as_markdown(self, filename: Optional[str] = None) -> str:
        """Export notes as markdown."""
        if not filename:
            filename = f"notes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        filepath = self.notes_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Quick Notes - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            
            # Group by category
            categories = {}
            for note in self.current_session_notes:
                cat = note["category"]
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(note)
            
            for category, notes in sorted(categories.items()):
                f.write(f"## {category.title()}\n\n")
                for note in notes:
                    f.write(f"- {note['text']}\n")
                    if note["tags"]:
                        f.write(f"  _Tags: {', '.join(note['tags'])}_\n")
                    f.write(f"  _{note['timestamp']}_\n\n")
        
        return str(filepath)
    
    def summarize(self) -> Dict[str, Any]:
        """Get summary of current session notes."""
        return {
            "total_notes": len(self.current_session_notes),
            "categories": {cat: len(self.get_notes_by_category(cat)) 
                          for cat in set(n["category"] for n in self.current_session_notes)},
            "all_tags": self.get_all_tags(),
            "first_note": self.current_session_notes[0]["timestamp"] if self.current_session_notes else None,
            "last_note": self.current_session_notes[-1]["timestamp"] if self.current_session_notes else None
        }
    
    def clear_session(self) -> int:
        """Clear current session and return note count."""
        count = len(self.current_session_notes)
        self.current_session_notes = []
        return count


notes = QuickNotes()
