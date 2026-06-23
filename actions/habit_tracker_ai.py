"""
habit_tracker_ai.py — Advanced Habit Formation with AI Coaching

Track habits, get AI coaching, and build streaks.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional


class HabitTrackerAI:
    """AI-powered habit tracking and coaching."""
    
    def __init__(self, db_path: str = "memory/habits.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            description TEXT,
            category TEXT,
            frequency TEXT,
            goal_per_day REAL,
            created_at TEXT,
            active INTEGER DEFAULT 1
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY,
            habit_id INTEGER,
            date TEXT,
            value REAL,
            notes TEXT,
            FOREIGN KEY(habit_id) REFERENCES habits(id)
        )''')
        
        conn.commit()
        conn.close()
    
    def create_habit(self, name: str, description: str, category: str, 
                    frequency: str = "daily", goal_per_day: float = 1) -> Dict[str, Any]:
        """Create a new habit to track."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''INSERT INTO habits (name, description, category, frequency, goal_per_day, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (name, description, category, frequency, goal_per_day, datetime.now().isoformat()))
            
            habit_id = c.lastrowid
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "habit_id": habit_id,
                "name": name,
                "message": f"✅ Habit '{name}' created! Let's build this streak."
            }
        except sqlite3.IntegrityError:
            return {"success": False, "error": f"Habit '{name}' already exists"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def log_habit(self, habit_name: str, value: float = 1, notes: str = "") -> Dict[str, Any]:
        """Log a habit completion."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('SELECT id FROM habits WHERE name = ?', (habit_name,))
            result = c.fetchone()
            
            if not result:
                conn.close()
                return {"success": False, "error": f"Habit '{habit_name}' not found"}
            
            habit_id = result[0]
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Update or insert
            c.execute('''INSERT OR REPLACE INTO habit_logs (habit_id, date, value, notes)
                        VALUES (?, ?, ?, ?)''',
                     (habit_id, today, value, notes))
            
            conn.commit()
            conn.close()
            
            # Get streak
            streak = self._get_current_streak(habit_name)
            
            return {
                "success": True,
                "habit": habit_name,
                "logged": value,
                "streak": streak,
                "message": self._get_motivational_message(streak)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _get_current_streak(self, habit_name: str) -> int:
        """Get current streak for a habit."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('SELECT id FROM habits WHERE name = ?', (habit_name,))
            result = c.fetchone()
            
            if not result:
                return 0
            
            habit_id = result[0]
            c.execute('''SELECT date FROM habit_logs WHERE habit_id = ? ORDER BY date DESC LIMIT 100''',
                     (habit_id,))
            
            dates = [row[0] for row in c.fetchall()]
            conn.close()
            
            if not dates:
                return 0
            
            streak = 0
            current_date = datetime.now().date()
            
            for date_str in dates:
                log_date = datetime.fromisoformat(date_str).date()
                if (current_date - log_date).days == streak:
                    streak += 1
                else:
                    break
            
            return streak
        except:
            return 0
    
    def _get_motivational_message(self, streak: int) -> str:
        """Get motivational message based on streak."""
        if streak == 1:
            return "🎉 Great start! Every journey begins with one step."
        elif streak == 7:
            return "🔥 One week down! You're building momentum!"
        elif streak == 30:
            return "🏆 30-day streak! This is becoming a real habit!"
        elif streak == 100:
            return "🚀 100 days! You're unstoppable!"
        elif streak % 10 == 0:
            return f"✨ {streak} days strong! Keep it up!"
        else:
            return f"💪 {streak}-day streak! Don't break it!"
    
    def get_habit_stats(self, habit_name: str, days: int = 30) -> Dict[str, Any]:
        """Get statistics for a habit."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('SELECT id, goal_per_day FROM habits WHERE name = ?', (habit_name,))
            result = c.fetchone()
            
            if not result:
                return {"error": "Habit not found"}
            
            habit_id, goal = result
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            
            c.execute('''SELECT value, date FROM habit_logs 
                        WHERE habit_id = ? AND date > ? ORDER BY date''',
                     (habit_id, cutoff))
            
            logs = c.fetchall()
            conn.close()
            
            completed_days = len(logs)
            total_value = sum(v[0] for v in logs)
            
            return {
                "habit": habit_name,
                "period_days": days,
                "completed_days": completed_days,
                "completion_rate": round(completed_days / days * 100, 1),
                "total_value": total_value,
                "average_per_day": round(total_value / completed_days, 2) if completed_days > 0 else 0,
                "goal_per_day": goal,
                "streak": self._get_current_streak(habit_name)
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_all_habits(self) -> List[Dict]:
        """Get all active habits."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''SELECT name, description, category, frequency, created_at FROM habits 
                        WHERE active = 1 ORDER BY created_at DESC''')
            
            habits = [{
                "name": row[0],
                "description": row[1],
                "category": row[2],
                "frequency": row[3],
                "streak": self._get_current_streak(row[0])
            } for row in c.fetchall()]
            
            conn.close()
            return habits
        except:
            return []
    
    def get_ai_coaching(self, habit_name: str) -> Dict[str, str]:
        """Get AI coaching tips for a habit."""
        stats = self.get_habit_stats(habit_name)
        
        if "error" in stats:
            return {"error": "Could not load habit"}
        
        tips = []
        
        if stats["completion_rate"] < 50:
            tips.append("🎯 You're completing this habit less than half the time. Try removing barriers to completion.")
        elif stats["completion_rate"] < 80:
            tips.append("⚡ You're close! Aim for 80%+ completion by adding it to your daily routine.")
        else:
            tips.append("🌟 Excellent consistency! Now try to reach 30-day streak.")
        
        if stats["streak"] == 0:
            tips.append("💪 Start your streak today! Even 1 day is better than 0.")
        elif stats["streak"] < 7:
            tips.append(f"🔥 Keep going! You're {7 - stats['streak']} days away from a full week.")
        
        return {
            "habit": habit_name,
            "current_streak": stats["streak"],
            "completion_rate": f"{stats['completion_rate']}%",
            "tips": tips,
            "motivation": self._get_motivational_message(stats["streak"])
        }


tracker = HabitTrackerAI()
