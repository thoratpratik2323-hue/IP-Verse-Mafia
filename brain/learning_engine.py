from datetime import datetime

class LearningEngine:
    """
    LAYER 6 - Learning Engine.
    Har baar better hota jaao.
    """
    
    def __init__(self, memory_engine):
        self.memory = memory_engine
    
    def learn_from_success(self, task: str, approach: str):
        """Ye kaam kiya — yaad rakho"""
        self.memory.db.execute("""
            INSERT INTO task_outcomes (task, approach, success, error, timestamp)
            VALUES (?, ?, TRUE, NULL, ?)
        """, (task, approach, datetime.now().isoformat()))
        self.memory.db.commit()
    
    def learn_from_failure(self, task: str, approach: str, error: str):
        """Ye nahi kiya — galti yaad rakho"""
        self.memory.db.execute("""
            INSERT INTO task_outcomes (task, approach, success, error, timestamp)
            VALUES (?, ?, FALSE, ?, ?)
        """, (task, approach, error, datetime.now().isoformat()))
        self.memory.db.commit()
    
    def get_best_approach(self, task: str) -> str:
        """Is kaam ka best tarika kya hai?"""
        cursor = self.memory.db.execute("""
            SELECT approach, COUNT(*) as success_count
            FROM task_outcomes
            WHERE task LIKE ? AND success = TRUE
            GROUP BY approach
            ORDER BY success_count DESC
            LIMIT 1
        """, (f"%{task[:30]}%",))
        result = cursor.fetchone()
        return result[0] if result else None
