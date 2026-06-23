"""
advanced_memory.py — Long-term Persistent Learning Memory

Stores interactions and learns user patterns over time.
"""

import json
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path


class AdvancedMemory:
    """Advanced persistent memory system with learning."""
    
    def __init__(self, db_path: str = "memory/advanced_memory.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            user_input TEXT,
            ai_response TEXT,
            sentiment TEXT,
            category TEXT,
            useful INTEGER
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS user_patterns (
            id INTEGER PRIMARY KEY,
            pattern TEXT,
            frequency INTEGER,
            last_seen TEXT,
            context TEXT
        )''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS learned_preferences (
            id INTEGER PRIMARY KEY,
            key TEXT UNIQUE,
            value TEXT,
            confidence REAL
        )''')
        
        conn.commit()
        conn.close()
    
    def store_interaction(self, user_input: str, ai_response: str, 
                         sentiment: str = "neutral", category: str = "general") -> None:
        """Store user-AI interaction."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT INTO interactions 
                    (timestamp, user_input, ai_response, sentiment, category, useful)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (datetime.now().isoformat(), user_input, ai_response, sentiment, category, 0))
        
        conn.commit()
        conn.close()
    
    def get_interaction_history(self, days: int = 30) -> List[Dict]:
        """Get interaction history from last N days."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        c.execute('''SELECT timestamp, user_input, ai_response, sentiment, category
                    FROM interactions WHERE timestamp > ? ORDER BY timestamp DESC''',
                 (cutoff_date,))
        
        results = [{
            "timestamp": row[0],
            "user_input": row[1],
            "ai_response": row[2],
            "sentiment": row[3],
            "category": row[4]
        } for row in c.fetchall()]
        
        conn.close()
        return results
    
    def learn_pattern(self, pattern: str, context: str = "") -> None:
        """Learn and store a user pattern."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT frequency FROM user_patterns WHERE pattern = ?', (pattern,))
        existing = c.fetchone()
        
        if existing:
            c.execute('''UPDATE user_patterns 
                        SET frequency = frequency + 1, last_seen = ?
                        WHERE pattern = ?''',
                     (datetime.now().isoformat(), pattern))
        else:
            c.execute('''INSERT INTO user_patterns (pattern, frequency, last_seen, context)
                        VALUES (?, 1, ?, ?)''',
                     (pattern, datetime.now().isoformat(), context))
        
        conn.commit()
        conn.close()
    
    def get_learned_patterns(self, top_n: int = 10) -> List[Dict]:
        """Get most frequent patterns."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT pattern, frequency, last_seen, context
                    FROM user_patterns ORDER BY frequency DESC LIMIT ?''',
                 (top_n,))
        
        results = [{
            "pattern": row[0],
            "frequency": row[1],
            "last_seen": row[2],
            "context": row[3]
        } for row in c.fetchall()]
        
        conn.close()
        return results
    
    def set_preference(self, key: str, value: str, confidence: float = 1.0) -> None:
        """Store learned user preference."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''INSERT OR REPLACE INTO learned_preferences (key, value, confidence)
                    VALUES (?, ?, ?)''',
                 (key, value, confidence))
        
        conn.commit()
        conn.close()
    
    def get_preference(self, key: str) -> Optional[str]:
        """Retrieve learned preference."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT value FROM learned_preferences WHERE key = ?', (key,))
        result = c.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_all_preferences(self) -> Dict[str, str]:
        """Get all learned preferences."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT key, value FROM learned_preferences')
        results = {row[0]: row[1] for row in c.fetchall()}
        
        conn.close()
        return results
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM interactions')
        interaction_count = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM user_patterns')
        pattern_count = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM learned_preferences')
        preference_count = c.fetchone()[0]
        
        conn.close()
        
        return {
            "total_interactions": interaction_count,
            "learned_patterns": pattern_count,
            "stored_preferences": preference_count,
            "db_size_kb": Path(self.db_path).stat().st_size / 1024
        }


memory = AdvancedMemory()
