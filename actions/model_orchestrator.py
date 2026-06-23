"""
model_orchestrator.py — Multi-Model AI Support for IP Prime

Switches between Gemini, Claude, OpenRouter, Ollama for optimal response.
"""

import os
import requests
from typing import Optional, Dict, Any


class ModelOrchestrator:
    """Manages multiple AI models and routes queries intelligently."""
    
    def __init__(self):
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.claude_key = os.getenv("ANTHROPIC_API_KEY")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.active_model = "gemini"
    
    def set_model(self, model: str) -> str:
        """Switch AI model: 'gemini', 'claude', 'gpt4', 'ollama'"""
        valid_models = ["gemini", "claude", "gpt4", "ollama"]
        if model.lower() in valid_models:
            self.active_model = model.lower()
            return f"Switched to {model}"
        return f"Invalid model. Choose from: {valid_models}"
    
    def query(self, prompt: str, context: Optional[str] = None, model: Optional[str] = None) -> str:
        """Route query to appropriate model."""
        target_model = model or self.active_model
        
        if target_model == "gemini":
            return self._query_gemini(prompt, context)
        elif target_model == "claude":
            return self._query_claude(prompt, context)
        elif target_model == "gpt4":
            return self._query_openrouter(prompt, context)
        elif target_model == "ollama":
            return self._query_ollama(prompt, context)
        else:
            return "Model not found"
    
    def _query_gemini(self, prompt: str, context: Optional[str]) -> str:
        """Query Gemini API."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.gemini_key)
            model = genai.GenerativeModel("gemini-pro")
            full_prompt = f"{context}\n{prompt}" if context else prompt
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Gemini Error: {str(e)}"
    
    def _query_claude(self, prompt: str, context: Optional[str]) -> str:
        """Query Claude via OpenRouter."""
        try:
            headers = {"Authorization": f"Bearer {self.openrouter_key}"}
            data = {
                "model": "anthropic/claude-3-sonnet",
                "messages": [{"role": "user", "content": f"{context}\n{prompt}" if context else prompt}]
            }
            response = requests.post("https://openrouter.io/api/v1/chat/completions", 
                                   headers=headers, json=data, timeout=30)
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Claude Error: {str(e)}"
    
    def _query_openrouter(self, prompt: str, context: Optional[str]) -> str:
        """Query GPT-4 via OpenRouter."""
        try:
            headers = {"Authorization": f"Bearer {self.openrouter_key}"}
            data = {
                "model": "openai/gpt-4",
                "messages": [{"role": "user", "content": f"{context}\n{prompt}" if context else prompt}]
            }
            response = requests.post("https://openrouter.io/api/v1/chat/completions", 
                                   headers=headers, json=data, timeout=30)
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"GPT-4 Error: {str(e)}"
    
    def _query_ollama(self, prompt: str, context: Optional[str]) -> str:
        """Query local Ollama model."""
        try:
            full_prompt = f"{context}\n{prompt}" if context else prompt
            response = requests.post(f"{self.ollama_url}/api/generate", 
                                   json={"model": "mistral", "prompt": full_prompt, "stream": False},
                                   timeout=60)
            return response.json()["response"]
        except Exception as e:
            return f"Ollama Error: {str(e)}"
    
    def compare_models(self, prompt: str) -> Dict[str, str]:
        """Get responses from all available models for comparison."""
        results = {}
        for model in ["gemini", "claude", "gpt4", "ollama"]:
            try:
                results[model] = self.query(prompt, model=model)[:200]  # Truncate for comparison
            except:
                results[model] = "Failed"
        return results


# Global instance
orchestrator = ModelOrchestrator()
