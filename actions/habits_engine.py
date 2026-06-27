"""
actions/habits_engine.py — Dynamic habit tracker that integrates auto-checking rules based on developer activities.

This is a premium action module for the IP Prime personal assistant suite.
"""

from pathlib import Path
from datetime import datetime

class HabitsEngine:
    """Core habit engine managing HABITS.md vault file."""
    def __init__(self):
        self.second_brain_dir = Path.home() / "Documents" / "SecondBrain"
        self.habits_file = self.second_brain_dir / "HABITS.md"
        
    def init_habits(self):
        """Creates HABITS.md with customized pillars if it does not exist."""
        if not self.second_brain_dir.exists():
            return
            
        if not self.habits_file.exists():
            today_str = datetime.now().strftime("%Y-%m-%d")
            content = f"""# Pratik's Atomic Habits Ledger

## Pillars of Daily Growth
1. **Coding & Dev**: Commit to coding daily (Auto-Checked on Git commit).
2. **CS Roadmap Study**: Read articles, slides, or guides (Auto-Checked on PDF/PPTX download).
3. **Daily Reflection**: Maintain clean conversation highlights in logs (Auto-Checked on system close).

---

## Today's Checklist ({today_str})
- [ ] 💻 Coding & Dev Progress
- [ ] 📚 CS Roadmap Reading
- [ ] ✍️ Daily Journal Reflection

---

## History Log
* 2026-05-28: [x] Daily habits initialized!
"""
            try:
                self.habits_file.write_text(content, encoding="utf-8")
                print("[HabitsEngine] ✓ Initialized HABITS.md inside Second Brain.")
            except Exception as e:
                print(f"[HabitsEngine] Error initializing HABITS.md: {e}")

    def trigger_habit_check(self, coding: bool = False, study: bool = False, journal: bool = False):
        """Safely updates specific checkbox items in HABITS.md."""
        self.init_habits()
        if not self.habits_file.exists():
            return
            
        try:
            content = self.habits_file.read_text(encoding="utf-8")
            lines = content.splitlines()
            changed = False
            
            for idx, line in enumerate(lines):
                if coding and "Coding & Dev Progress" in line and "[ ]" in line:
                    lines[idx] = line.replace("[ ]", "[x]")
                    changed = True
                if study and "CS Roadmap Reading" in line and "[ ]" in line:
                    lines[idx] = line.replace("[ ]", "[x]")
                    changed = True
                if journal and "Daily Journal Reflection" in line and "[ ]" in line:
                    lines[idx] = line.replace("[ ]", "[x]")
                    changed = True
                    
            if changed:
                self.habits_file.write_text("\n".join(lines), encoding="utf-8")
                print(f"[HabitsEngine] ✓ Auto-checked daily habit (Coding={coding}, Study={study}, Journal={journal}).")
        except Exception as e:
            print(f"[HabitsEngine] Error updating habit checks: {e}")

# Global instance helper
_engine = HabitsEngine()

def init_habits():
    _engine.init_habits()

def check_coding_habit():
    _engine.trigger_habit_check(coding=True)

def check_study_habit():
    _engine.trigger_habit_check(study=True)

def check_journal_habit():
    _engine.trigger_habit_check(journal=True)
