"""
semantic_router.py — Routes text queries to the most appropriate action module.

This is a standard action module for the IP Prime personal assistant suite.
"""

import re
import socket
import json
from pathlib import Path

def is_offline() -> bool:
    """Checks if the system has an active internet connection by attempting a quick socket connection."""
    try:
        # Check port 53 (DNS) on Cloudflare (1.1.1.1) with a short timeout
        s = socket.create_connection(("1.1.1.1", 53), timeout=0.8)
        s.close()
        return False
    except Exception:
        try:
            s = socket.create_connection(("8.8.8.8", 53), timeout=0.8)
            s.close()
            return False
        except Exception:
            return True

class SemanticRouter:
    def __init__(self):
        # Keywords indicating complex programming, refactoring, or algorithmic tasks
        self.pro_indicators = [
            r"\brefactor\b", r"\boptimize\b", r"\balgorithm\b", 
            r"\barchitect\b", r"\bcomplex\b", r"\bmathematical\b",
            r"\bdebug complex\b", r"\brewrite core\b", r"\bperformance bottleneck\b",
            r"\banalyze logs\b", r"\bsecurity audit\b", r"\bdeep analysis\b"
        ]

    def route(self, prompt: str) -> str:
        """
        Dynamically analyzes a user prompt or subtask description.
        Returns:
            "ollama/<local_model>" if local_first is enabled or offline.
            "gemini-2.5-pro" if reasoning requirements are high.
            "gemini-2.5-flash" for lightweight/conversational tasks.
        """
        if not prompt or not isinstance(prompt, str):
            return "gemini-2.5-flash"
            
        normalized = prompt.lower()
        
        # 0. Check Offline / Local-first mode first
        try:
            base_dir = Path(__file__).resolve().parent.parent
            feat_path = base_dir / "config" / "prime_features.json"
            if feat_path.exists():
                with open(feat_path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                local_cfg = cfg.get("local_first", {})
                if local_cfg.get("enabled", False) or is_offline():
                    model = local_cfg.get("preferred_local_model", "llama3.2")
                    print(f"[Varon Router] >> Local routing triggered (offline={is_offline()}). Model: ollama/{model}")
                    return f"ollama/{model}"
        except Exception as e:
            print(f"[Varon Router] Error checking local-first features: {e}")
        
        # 1. Fast regex keyword detection
        for pattern in self.pro_indicators:
            if re.search(pattern, normalized):
                print(f"[Varon Router] >> Match found: '{pattern}'. Routing to gemini-2.5-pro.")
                return "gemini-2.5-pro"
                
        # 2. Instruction volume threshold: long detailed specifications need pro
        word_count = len(prompt.split())
        if word_count >= 150:
            print(f"[Varon Router] >> Prompt density exceeds 150 words ({word_count}). Routing to gemini-2.5-pro.")
            return "gemini-2.5-pro"
            
        # 3. Default fallback
        print("[Varon Router] >> Lightweight task. Routing to gemini-2.5-flash.")
        return "gemini-2.5-flash"

def route_model(prompt: str) -> str:
    """Helper function for quick model routing."""
    router = SemanticRouter()
    return router.route(prompt)

