"""
pomodoro_ai.py — Smart Pomodoro Timer with AI Breaks

Work sessions with intelligent break suggestions and wellness tips.
"""

import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, List
import random


class PomodoroAI:
    """AI-enhanced Pomodoro timer with smart breaks."""
    
    def __init__(self):
        self.work_duration = 25 * 60  # 25 minutes
        self.break_duration = 5 * 60  # 5 minutes
        self.long_break_duration = 15 * 60  # 15 minutes
        self.sessions_until_long_break = 4
        
        self.current_session = None
        self.session_history = []
        self.is_running = False
    
    def start_work_session(self, task: str = "Focused work", 
                          duration_minutes: int = 25) -> Dict[str, Any]:
        """Start a Pomodoro work session."""
        
        self.work_duration = duration_minutes * 60
        self.current_session = {
            "type": "work",
            "task": task,
            "start_time": datetime.now(),
            "duration": self.work_duration,
            "end_time": datetime.now() + timedelta(seconds=self.work_duration),
            "completed": False,
            "interruptions": 0
        }
        
        self.is_running = True
        
        return {
            "session": "started",
            "task": task,
            "duration_minutes": duration_minutes,
            "start_time": self.current_session["start_time"].isoformat(),
            "message": f"🎯 Focus mode activated! Work on '{task}' for {duration_minutes} minutes."
        }
    
    def get_break_suggestion(self) -> Dict[str, str]:
        """Get AI-suggested break activity."""
        
        suggestions = {
            "stretching": {
                "description": "Full body stretch (2 min)",
                "duration": 120,
                "benefits": "Improves blood flow, reduces tension"
            },
            "hydration": {
                "description": "Drink water and rest eyes (1 min)",
                "duration": 60,
                "benefits": "Keeps you hydrated, reduces eye strain"
            },
            "walk": {
                "description": "Quick walk around (3 min)",
                "duration": 180,
                "benefits": "Gets circulation going, clears mind"
            },
            "breathing": {
                "description": "Deep breathing exercise (2 min)",
                "duration": 120,
                "benefits": "Reduces stress, improves oxygen flow"
            },
            "snack": {
                "description": "Healthy snack break (2 min)",
                "duration": 120,
                "benefits": "Replenishes energy, prevents fatigue"
            },
            "meditation": {
                "description": "Quick meditation (2 min)",
                "duration": 120,
                "benefits": "Mental clarity, stress relief"
            }
        }
        
        activity = random.choice(list(suggestions.values()))
        return activity
    
    def start_break(self, duration_minutes: int = 5) -> Dict[str, Any]:
        """Start a break session."""
        
        suggestion = self.get_break_suggestion()
        
        self.current_session = {
            "type": "break",
            "start_time": datetime.now(),
            "duration": duration_minutes * 60,
            "end_time": datetime.now() + timedelta(minutes=duration_minutes),
            "suggestion": suggestion
        }
        
        self.is_running = True
        
        return {
            "session": "break_started",
            "duration_minutes": duration_minutes,
            "suggestion": f"{suggestion['description']} - {suggestion['benefits']}",
            "message": f"☕ Break time! Try this: {suggestion['description']}"
        }
    
    def get_time_remaining(self) -> Dict[str, Any]:
        """Get remaining time in current session."""
        
        if not self.current_session:
            return {"error": "No session in progress"}
        
        elapsed = (datetime.now() - self.current_session["start_time"]).total_seconds()
        remaining = self.current_session["duration"] - elapsed
        
        if remaining <= 0:
            return {
                "status": "completed",
                "session_type": self.current_session["type"]
            }
        
        minutes = int(remaining // 60)
        seconds = int(remaining % 60)
        
        return {
            "remaining": f"{minutes}:{seconds:02d}",
            "total_duration": f"{int(self.current_session['duration'] // 60)}:00",
            "progress_percent": round((elapsed / self.current_session["duration"]) * 100, 1),
            "session_type": self.current_session["type"]
        }
    
    def get_wellness_tips(self) -> List[str]:
        """Get wellness tips for during breaks."""
        
        tips = [
            "💧 Stay hydrated - drink water regularly",
            "👀 Practice 20-20-20 rule: Every 20 min, look 20 feet away for 20 seconds",
            "🧘 Try box breathing: Inhale 4, hold 4, exhale 4, hold 4",
            "🚶 Walk around - movement improves focus",
            "🤸 Do light stretches - especially neck and shoulders",
            "😴 Get good sleep - 7-9 hours helps productivity",
            "🥗 Eat healthy - avoid sugar crashes",
            "📵 Keep phone away during work sessions",
            "🎵 Gentle background music can help focus",
            "📝 Take notes - helps consolidate learning"
        ]
        
        return random.sample(tips, 3)
    
    def complete_session(self) -> Dict[str, Any]:
        """Mark current session as complete."""
        
        if not self.current_session:
            return {"error": "No session in progress"}
        
        self.current_session["completed"] = True
        self.current_session["end_time"] = datetime.now()
        
        self.session_history.append(self.current_session)
        self.is_running = False
        
        if self.current_session["type"] == "work":
            completed_work = len([s for s in self.session_history if s["type"] == "work"])
            
            if completed_work % self.sessions_until_long_break == 0:
                break_msg = f"Time for a long break! (15 min)"
            else:
                remaining_for_long = self.sessions_until_long_break - (completed_work % self.sessions_until_long_break)
                break_msg = f"{remaining_for_long} more sessions until a long break"
            
            return {
                "status": "completed",
                "task": self.current_session.get("task"),
                "work_sessions_today": completed_work,
                "next_break": break_msg
            }
        else:
            return {
                "status": "break_completed",
                "ready_for": "Next work session!"
            }
    
    def get_daily_stats(self) -> Dict[str, Any]:
        """Get productivity stats for the day."""
        
        today = datetime.now().date()
        today_sessions = [s for s in self.session_history 
                         if s["start_time"].date() == today]
        
        work_sessions = [s for s in today_sessions if s["type"] == "work"]
        work_time = sum(s["duration"] for s in work_sessions) // 60  # in minutes
        
        return {
            "date": today.isoformat(),
            "work_sessions": len(work_sessions),
            "total_work_minutes": work_time,
            "total_work_hours": round(work_time / 60, 1),
            "sessions_history": [{
                "type": s["type"],
                "duration": s["duration"] // 60,
                "task": s.get("task")
            } for s in today_sessions[-10:]]  # Last 10 sessions
        }


pomodoro = PomodoroAI()
