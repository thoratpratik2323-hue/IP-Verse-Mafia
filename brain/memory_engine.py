import sqlite3
from datetime import datetime
from pathlib import Path

class MemoryEngine:
    """
    LAYER 3 - The Memory Engine.
    Uses SQLite to persistently remember conversations, habits, tasks, and user profiles.
    """
    
    def __init__(self):
        # Ensure memory directory exists
        db_dir = Path("memory")
        db_dir.mkdir(exist_ok=True)
        self.db_path = db_dir / "brain.db"
        
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.setup_tables()
    
    def setup_tables(self):
        self.db.executescript("""
            -- Har conversation yaad rakho
            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user_said TEXT,
                ai_did    TEXT,
                result    TEXT,
                emotion   TEXT
            );
            
            -- User ki aadat yaad rakho
            CREATE TABLE IF NOT EXISTS habits (
                habit     TEXT PRIMARY KEY,
                frequency INTEGER,
                last_time TEXT,
                context   TEXT
            );
            
            -- Kya kaam kiya, kya nahi
            CREATE TABLE IF NOT EXISTS task_outcomes (
                task      TEXT,
                approach  TEXT,
                success   BOOLEAN,
                error     TEXT,
                timestamp TEXT
            );
            
            -- User ke baare mein jo pata chala
            CREATE TABLE IF NOT EXISTS user_profile (
                key       TEXT PRIMARY KEY,
                value     TEXT,
                updated   TEXT
            );
        """)
    
    def remember(self, user_said: str, ai_did: str, result: str, emotion: str):
        """Har interaction yaad rakho"""
        self.db.execute("""
            INSERT INTO conversations (timestamp, user_said, ai_did, result, emotion)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().isoformat(), user_said, ai_did, result, emotion))
        self.db.commit()
        
        # Aadat bhi update karo (simple count for demonstration)
        self.update_habit(ai_did)
        
    def update_habit(self, action: str):
        """Increments the habit frequency."""
        if not action:
            return
        # check if exists
        cursor = self.db.execute("SELECT frequency FROM habits WHERE habit = ?", (action,))
        row = cursor.fetchone()
        if row:
            freq = row[0] + 1
            self.db.execute("UPDATE habits SET frequency = ?, last_time = ? WHERE habit = ?", 
                            (freq, datetime.now().isoformat(), action))
        else:
            self.db.execute("INSERT INTO habits (habit, frequency, last_time, context) VALUES (?, 1, ?, '')", 
                            (action, datetime.now().isoformat()))
        self.db.commit()
    
    def recall_similar(self, current_task: str):
        """Pehle aisa kaam hua tha? Kaise kiya tha?"""
        cursor = self.db.execute("""
            SELECT ai_did, result 
            FROM conversations 
            WHERE user_said LIKE ? 
            ORDER BY timestamp DESC 
            LIMIT 5
        """, (f"%{current_task[:20]}%",))
        # Returns list of dicts for easier use
        return [{"ai_did": row[0], "result": row[1]} for row in cursor.fetchall()]
    
    def learn_preference(self, key: str, value: str):
        """User ki pasand yaad rakho"""
        self.db.execute("""
            INSERT OR REPLACE INTO user_profile (key, value, updated)
            VALUES (?, ?, ?)
        """, (key, value, datetime.now().isoformat()))
        self.db.commit()
    
    def get_user_profile(self) -> dict:
        """Pura user profile do"""
        cursor = self.db.execute("SELECT key, value FROM user_profile")
        return dict(cursor.fetchall())
        
    def close(self):
        self.db.close()
