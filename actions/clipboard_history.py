"""
clipboard_history.py — Smart Clipboard History with Search

Track and search clipboard history, extract insights.
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any
import hashlib
import re


class ClipboardHistory:
    """Manages clipboard history and smart search."""
    
    def __init__(self, db_path: str = "memory/clipboard_history.db"):
        self.db_path = db_path
        Path(self.db_path).parent.mkdir(exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS clipboard_items (
            id INTEGER PRIMARY KEY,
            timestamp TEXT,
            content TEXT,
            content_hash TEXT UNIQUE,
            content_type TEXT,
            size INTEGER,
            starred INTEGER DEFAULT 0
        )''')
        
        conn.commit()
        conn.close()
    
    def add_item(self, content: str) -> Dict[str, Any]:
        """Add content to clipboard history."""
        content_hash = hashlib.md5(content.encode()).hexdigest()
        content_type = self._detect_type(content)
        
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''INSERT OR IGNORE INTO clipboard_items 
                        (timestamp, content, content_hash, content_type, size)
                        VALUES (?, ?, ?, ?, ?)''',
                     (datetime.now().isoformat(), content, content_hash, content_type, len(content)))
            
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "hash": content_hash,
                "type": content_type,
                "size": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _detect_type(self, content: str) -> str:
        """Detect content type."""
        if re.match(r'^https?://', content):
            return "url"
        elif re.match(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-Z]{2,}', content):
            return "email"
        elif re.match(r'^\d+$', content):
            return "number"
        elif content.startswith('{') or content.startswith('['):
            return "json"
        elif len(content) > 100 and '\n' in content:
            return "document"
        else:
            return "text"
    
    def search(self, query: str, limit: int = 20) -> List[Dict]:
        """Search clipboard history."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        search_query = f"%{query}%"
        c.execute('''SELECT id, timestamp, content, content_type FROM clipboard_items
                    WHERE content LIKE ? ORDER BY timestamp DESC LIMIT ?''',
                 (search_query, limit))
        
        results = [{
            "id": row[0],
            "timestamp": row[1],
            "preview": row[2][:100] + "..." if len(row[2]) > 100 else row[2],
            "type": row[3]
        } for row in c.fetchall()]
        
        conn.close()
        return results
    
    def search_by_type(self, content_type: str, limit: int = 20) -> List[Dict]:
        """Get clipboard items by type."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT id, timestamp, content, content_type FROM clipboard_items
                    WHERE content_type = ? ORDER BY timestamp DESC LIMIT ?''',
                 (content_type, limit))
        
        results = [{
            "id": row[0],
            "timestamp": row[1],
            "content": row[2],
            "type": row[3]
        } for row in c.fetchall()]
        
        conn.close()
        return results
    
    def get_recent(self, hours: int = 24, limit: int = 20) -> List[Dict]:
        """Get recent clipboard items."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        c.execute('''SELECT id, timestamp, content, content_type FROM clipboard_items
                    WHERE timestamp > ? ORDER BY timestamp DESC LIMIT ?''',
                 (cutoff, limit))
        
        results = [{
            "id": row[0],
            "timestamp": row[1],
            "preview": row[2][:80] + "..." if len(row[2]) > 80 else row[2],
            "type": row[3]
        } for row in c.fetchall()]
        
        conn.close()
        return results
    
    def star_item(self, item_id: int) -> bool:
        """Star an item for later reference."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('UPDATE clipboard_items SET starred = 1 WHERE id = ?', (item_id,))
            conn.commit()
            conn.close()
            return True
        except:
            return False
    
    def get_starred(self) -> List[Dict]:
        """Get all starred items."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''SELECT id, timestamp, content, content_type FROM clipboard_items
                    WHERE starred = 1 ORDER BY timestamp DESC''')
        
        results = [{
            "id": row[0],
            "timestamp": row[1],
            "content": row[2],
            "type": row[3]
        } for row in c.fetchall()]
        
        conn.close()
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get clipboard history statistics."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM clipboard_items')
        total_items = c.fetchone()[0]
        
        c.execute('''SELECT content_type, COUNT(*) as count FROM clipboard_items
                    GROUP BY content_type''')
        type_counts = {row[0]: row[1] for row in c.fetchall()}
        
        c.execute('SELECT AVG(size) FROM clipboard_items')
        avg_size = c.fetchone()[0] or 0
        
        conn.close()
        
        return {
            "total_items": total_items,
            "type_distribution": type_counts,
            "average_size": int(avg_size),
            "db_size_kb": Path(self.db_path).stat().st_size / 1024
        }
    
    def cleanup(self, days: int = 30) -> int:
        """Delete old clipboard items."""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            c.execute('DELETE FROM clipboard_items WHERE timestamp < ?', (cutoff,))
            
            deleted_count = c.rowcount
            conn.commit()
            conn.close()
            return deleted_count
        except:
            return 0


clipboard = ClipboardHistory()
