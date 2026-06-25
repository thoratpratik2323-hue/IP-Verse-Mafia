import logging
import socket
import requests
import json
from pathlib import Path

# Base default settings
DEFAULT_OLLAMA_URL = "http://localhost:11434"

def load_local_runner_settings() -> dict:
    """Loads local runner configurations from settings.json."""
    settings_path = Path(__file__).resolve().parent.parent / "config" / "settings.json"
    if settings_path.exists():
        try:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception as e:
            logging.debug("Failed to read settings: %s", e)
    return {}

def is_internet_available(host="8.8.8.8", port=53, timeout=2.0) -> bool:
    """Checks if the computer has an active internet connection by resolving a socket."""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error:
        pass
    return False

def is_local_runner_available() -> bool:
    """Checks if the configured local runner is running and available."""
    settings = load_local_runner_settings()
    runner = settings.get("local_runner_type", "Ollama").lower()
    url = settings.get("local_runner_url", DEFAULT_OLLAMA_URL)
    
    try:
        if runner == "ollama":
            res = requests.get(f"{url}/api/tags", timeout=1.5)
            return res.status_code == 200
        else:
            # llama.cpp or LocalAI - check if server connects
            res = requests.get(url, timeout=1.5)
            return res.status_code in (200, 404, 401)
    except Exception:
        return False

def is_ollama_available() -> bool:
    """Alias for backward compatibility."""
    return is_local_runner_available()

def get_first_available_ollama_model() -> str:
    """Queries the local runner for available models or returns the configured one."""
    settings = load_local_runner_settings()
    configured_model = settings.get("local_runner_model")
    if configured_model:
        return configured_model
        
    runner = settings.get("local_runner_type", "Ollama").lower()
    url = settings.get("local_runner_url", DEFAULT_OLLAMA_URL)
    
    if runner == "ollama":
        try:
            res = requests.get(f"{url}/api/tags", timeout=1.5)
            if res.status_code == 200:
                models = res.json().get("models", [])
                if models:
                    return models[0]["name"]
        except Exception as _exc:
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
        return "mistral"
    else:
        # llama.cpp / LocalAI
        try:
            res = requests.get(f"{url}/v1/models", timeout=1.5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data:
                    return data[0]["id"]
        except Exception as _exc:
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
        return "local-model"

def query_ollama(user_prompt: str, system_prompt: str = "") -> str:
    """Sends a chat request to the configured local runner instance (Ollama/llama.cpp/LocalAI)."""
    settings = load_local_runner_settings()
    runner = settings.get("local_runner_type", "Ollama")
    url = settings.get("local_runner_url", DEFAULT_OLLAMA_URL)
    
    if not is_local_runner_available():
        return f"I am offline, and I couldn't find a running local {runner} instance at {url}, sir. Please start your local runner."
        
    model = get_first_available_ollama_model()
    print(f"[Offline Fallback] Routing request to local {runner} (Model: {model})...")
    
    if runner.lower() == "ollama":
        chat_url = f"{url}/api/chat"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        try:
            response = requests.post(chat_url, json=payload, timeout=30.0)
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "No response content from Ollama.")
            else:
                return f"Ollama returned status code {response.status_code}: {response.text}"
        except Exception as e:
            return f"Failed to connect to local Ollama model: {e}"
    else:
        # llama.cpp or LocalAI - OpenAI compatible endpoint
        chat_url = f"{url}/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False
        }
        try:
            response = requests.post(chat_url, json=payload, timeout=30.0)
            if response.status_code == 200:
                result = response.json()
                choices = result.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "No response content from local runner.")
                return "No choices returned from local server."
            else:
                return f"Local server returned status code {response.status_code}: {response.text}"
        except Exception as e:
            return f"Failed to connect to local server: {e}"
