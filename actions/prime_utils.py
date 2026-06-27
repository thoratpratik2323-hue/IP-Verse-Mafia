"""
prime_utils.py — Core utility helper functions used across action modules.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/prime_utils.py
import sys
import json
import io
import base64
import os
import threading
from pathlib import Path

def get_base_dir() -> Path:
    """Returns the base application directory, supporting frozen executables."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def load_env_file():
    """Loads environment variables from .env file securely."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    base_dir = get_base_dir()
    dot_env_path = base_dir / ".env"
    if dot_env_path.exists():
        try:
            with open(dot_env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k:
                            os.environ[k] = v
        except Exception as e:
            print(f"[Prime Utils] Error reading .env fallback: {e}")

# Load .env variables on import
load_env_file()

_current_key_index = 0

def get_all_gemini_keys() -> list[str]:
    """Loads primary and backup Gemini API keys prioritizing env variables, then config/api_keys.json."""
    keys = []
    
    # Priority 1: Environment variables
    env_gemini = os.environ.get("GEMINI_API_KEY", "").strip()
    env_coding = os.environ.get("CODING_API_KEY", "").strip()
    if env_gemini:
        keys.append(env_gemini)
    if env_coding and env_coding not in keys:
        keys.append(env_coding)
        
    # Priority 2: config/api_keys.json
    path = get_base_dir() / "config" / "api_keys.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            primary = data.get("gemini_api_key") or data.get("coding_api_key") or ""
            if primary and primary not in keys:
                keys.append(primary)
            backups = data.get("gemini_api_key_backups", [])
            for bk in backups:
                if bk and bk not in keys:
                    keys.append(bk)
        except Exception as e:
            print(f"[Prime Utils] Error loading keys for rotation: {e}")
    return keys

def confirm_dangerous_action(action_name: str, details: str, player=None) -> bool:
    """
    Blocks and prompts the user for confirmation via PyQt's thread-safe confirmation signal.
    Returns True if user clicked Yes/Confirm, False otherwise.
    """
    msg = (
        f"🛡️ SECURITY GATE 🛡️\n\n"
        f"Pratik Sir, an autonomous tool wants to run a potentially dangerous action:\n\n"
        f"• Action: {action_name}\n"
        f"• Details: {details}\n\n"
        f"Do you want to authorize this execution?"
    )
    print(f"[Security Gate] Prompting confirmation: {action_name} - {details}")
    if player and hasattr(player, "confirm_action"):
        return player.confirm_action(msg)
    
    print("[Security Gate] WARNING: No player/GUI context found to show confirmation prompt.")
    if sys.stdin.isatty():
        try:
            ans = input(f"{msg}\nAuthorize? (yes/no): ").strip().lower()
            return ans in ("yes", "y", "confirm")
        except Exception:
            pass
    return False

def get_api_key() -> str:
    """Returns the currently active Gemini API key from the rotation list."""
    global _current_key_index
    keys = get_all_gemini_keys()
    if not keys:
        return ""
    if _current_key_index >= len(keys):
        _current_key_index = 0
    return keys[_current_key_index]

def rotate_api_key() -> bool:
    """Rotates to the next available API key in the backup list. Returns True if successfully rotated."""
    global _current_key_index
    keys = get_all_gemini_keys()
    if len(keys) <= 1:
        print("[Prime Utils] ⚠️ No backup API keys available to rotate.")
        return False
    _current_key_index = (_current_key_index + 1) % len(keys)
    print(f"[Prime Utils] 🔄 Rotated to Gemini API key index {_current_key_index} (ending with ...{keys[_current_key_index][-6:] if len(keys[_current_key_index]) > 6 else ''})")
    return True

# ==========================================
# Unified Model Adapter for NVIDIA/OpenAI & Gemini
# ==========================================

class UnifiedModelResponse:
    def __init__(self, text: str):
        self.text = text

def image_to_base64_url(image_in) -> str:
    if isinstance(image_in, bytes):
        b64 = base64.b64encode(image_in).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    elif hasattr(image_in, "save"):  # PIL Image
        try:
            buf = io.BytesIO()
            image_in.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/png;base64,{b64}"
        except Exception as e:
            print(f"[Unified Model] PIL convert failed: {e}")
    elif hasattr(image_in, "inline_data") and image_in.inline_data:  # google Part
        try:
            mime = getattr(image_in.inline_data, "mime_type", "image/png")
            b64 = base64.b64encode(image_in.inline_data.data).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        except Exception as e:
            print(f"[Unified Model] Part convert failed: {e}")
    elif hasattr(image_in, "data") and hasattr(image_in, "mime_type"):
        try:
            b64 = base64.b64encode(image_in.data).decode("utf-8")
            return f"data:{image_in.mime_type};base64,{b64}"
        except Exception as e:
            print(f"[Unified Model] Part-like convert failed: {e}")
    return ""

def _call_openrouter_fallback(contents, config=None, model_name=None) -> UnifiedModelResponse:
    """Helper to perform OpenRouter free LLM fallback call."""
    import base64
    from actions.openrouter_helper import client as or_client
    
    prompt_text = ""
    image_b64 = ""
    mime_type = "image/png"
    
    contents_list = contents if isinstance(contents, list) else [contents]
    for item in contents_list:
        if isinstance(item, str):
            prompt_text += item + "\n"
        elif hasattr(item, "inline_data") and item.inline_data:
            image_b64 = base64.b64encode(item.inline_data.data).decode("utf-8")
            mime_type = getattr(item.inline_data, "mime_type", mime_type)
        elif isinstance(item, bytes):
            image_b64 = base64.b64encode(item).decode("utf-8")
            
    prompt_text = prompt_text.strip()
    system_instruction = ""
    if config:
        system_instruction = getattr(config, "system_instruction", "")
        if isinstance(config, dict):
            system_instruction = config.get("system_instruction", "")

    if image_b64:
        res = or_client.vision(prompt_text, image_b64, mime=mime_type, system=system_instruction or "Analyze the image.", model=model_name)
    else:
        res = or_client.chat(prompt_text, system=system_instruction or "You are a helpful assistant.", model=model_name)
    return UnifiedModelResponse(text=res)

def call_unified_model(contents, config=None, category="coding", model_name=None, **kwargs) -> UnifiedModelResponse:
    """Central dispatch for all non-live LLM calls in the codebase."""
    base_dir = get_base_dir()

    # ─── OLLAMA / LOCAL FIRST ROUTING INTERCEPT ───
    is_ollama = (model_name and (model_name.startswith("ollama/") or model_name.startswith("local/")))
    
    # Check if we are currently offline
    try:
        from actions.semantic_router import is_offline
        offline_flag = is_offline()
    except Exception:
        offline_flag = False

    if is_ollama or offline_flag:
        ollama_url = "http://127.0.0.1:11434"
        local_model = "llama3.2"
        fallback_allowed = True
        try:
            feat_path = base_dir / "config" / "prime_features.json"
            if feat_path.exists():
                with open(feat_path, "r", encoding="utf-8") as f:
                    feats = json.load(f)
                local_cfg = feats.get("local_first", {})
                ollama_url = local_cfg.get("ollama_url", ollama_url)
                local_model = local_cfg.get("preferred_local_model", local_model)
                fallback_allowed = local_cfg.get("fallback_to_cloud", True)
        except Exception:
            pass

        target_model = model_name.replace("ollama/", "").replace("local/", "") if model_name else local_model
        
        import requests
        system_instruction = ""
        if config:
            system_instruction = getattr(config, "system_instruction", "")
            if isinstance(config, dict):
                system_instruction = config.get("system_instruction", "")

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": str(system_instruction)})

        user_content = []
        contents_list = contents if isinstance(contents, list) else [contents]
        for item in contents_list:
            if isinstance(item, str):
                user_content.append({"type": "text", "text": item})
            else:
                b64_url = image_to_base64_url(item)
                if b64_url:
                    user_content.append({"type": "image_url", "image_url": {"url": b64_url}})
                elif isinstance(item, (int, float, bool)):
                    user_content.append({"type": "text", "text": str(item)})

        if len(user_content) == 1 and user_content[0]["type"] == "text":
            messages.append({"role": "user", "content": user_content[0]["text"]})
        else:
            messages.append({"role": "user", "content": user_content})

        local_payload = {
            "model": target_model,
            "messages": messages,
            "temperature": 0.2
        }

        try:
            url = f"{ollama_url.rstrip('/')}/v1/chat/completions"
            print(f"[Unified Model] Sending local POST to {url} with model {target_model}...")
            resp = requests.post(url, json=local_payload, timeout=10)
            resp.raise_for_status()
            res_json = resp.json()
            text_out = res_json["choices"][0]["message"]["content"]
            return UnifiedModelResponse(text=text_out)
        except Exception as local_err:
            print(f"[Unified Model] Local Ollama call failed: {local_err}.")
            if not fallback_allowed or offline_flag:
                raise RuntimeError(f"Ollama execution failed and cloud fallback is disabled/offline: {local_err}")
            print("[Unified Model] Fallback to cloud provider active...")

    # 1. Load config
    config_path = base_dir / "config" / "api_keys.json"
    cfg = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception as e:
            print(f"[Unified Model] Config read error: {e}")

    # 2. Extract provider details
    import os
    is_groq = (model_name and model_name.startswith("groq/"))
    if category == "vision":
        provider = cfg.get("vision_provider", "gemini").lower()
        if is_groq or provider == "groq":
            provider = "groq"
            api_key = cfg.get("groq_api_key") or os.environ.get("GROQ_API_KEY", "")
            base_url = cfg.get("groq_base_url") or "https://api.groq.com/openai/v1"
            model = (model_name.replace("groq/", "") if model_name else None) or cfg.get("groq_model") or "llama-3.2-11b-vision-preview"
        else:
            api_key = cfg.get("vision_api_key") or cfg.get("coding_api_key") or cfg.get("gemini_api_key", "")
            base_url = cfg.get("vision_base_url", "")
            model = model_name or cfg.get("vision_model", "nvidia/llama-3.2-11b-vision-instruct")
    else:
        provider = cfg.get("coding_provider", "gemini").lower()
        if is_groq or provider == "groq":
            provider = "groq"
            api_key = cfg.get("groq_api_key") or os.environ.get("GROQ_API_KEY", "")
            base_url = cfg.get("groq_base_url") or "https://api.groq.com/openai/v1"
            model = (model_name.replace("groq/", "") if model_name else None) or cfg.get("groq_model") or "llama-3.1-8b-instant"
        else:
            api_key = cfg.get("coding_api_key") or cfg.get("gemini_api_key", "")
            base_url = cfg.get("coding_base_url", "")
            model = model_name or cfg.get("coding_model", "nvidia/llama-3.1-nemotron-70b-instruct")

    # If provider is freellmapi and key/url is missing, use standard defaults
    if provider == "freellmapi":
        if not api_key:
            api_key = "freellmapi-key"
        if not base_url:
            base_url = "http://localhost:3000/v1"

    if model and "gemini" in model.lower() and provider != "freellmapi" and provider != "openrouter":
        provider = "gemini"

    if provider == "openrouter":
        print(f"[Unified Model] OpenRouter provider active. Target model: {model}")
        try:
            return _call_openrouter_fallback(contents, config, model_name=model_name)
        except Exception as e:
            print(f"[Unified Model] OpenRouter call failed: {e}. Falling back to Gemini...")
            provider = "gemini"

    # If provider is gemini or fallback triggered, run Gemini SDK
    if (provider == "gemini" or not base_url or not api_key) and provider != "freellmapi":
        if provider != "gemini":
            print(f"[Unified Model] Fallback to Gemini: provider is {provider} but base_url or api_key is missing.")
        
        # Determine standard models
        gemini_model = model_name or ("gemini-2.5-flash" if category == "vision" else "gemini-2.5-flash")
        
        keys = get_all_gemini_keys()
        max_attempts = max(1, len(keys))
        
        for attempt in range(max_attempts):
            active_key = api_key or get_api_key()
            try:
                # Check which client call style is being simulated
                # For google-genai style (Client.models.generate_content):
                from google import genai
                client = genai.Client(api_key=active_key)
                
                # Map standard structure
                native_contents = []
                if isinstance(contents, list):
                    native_contents = contents
                else:
                    native_contents = [contents]

                response = client.models.generate_content(
                    model=gemini_model,
                    contents=native_contents,
                    config=config,
                    **kwargs
                )
                return UnifiedModelResponse(text=response.text or "")
            except Exception as e:
                err_msg = str(e)
                is_rate_limit = "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower()
                if is_rate_limit and attempt < max_attempts - 1:
                    print(f"[Unified Model] Rate limit hit (429) on attempt {attempt+1}. Attempting key rotation...")
                    if rotate_api_key():
                        continue
                
                # Try legacy google-generativeai style fallback
                try:
                    import warnings
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", category=FutureWarning)
                        import google.generativeai as genai
                    genai.configure(api_key=active_key)
                    legacy_model = genai.GenerativeModel(gemini_model)
                    response = legacy_model.generate_content(contents, **kwargs)
                    return UnifiedModelResponse(text=response.text or "")
                except Exception as le:
                    le_msg = str(le)
                    is_legacy_rate_limit = "429" in le_msg or "RESOURCE_EXHAUSTED" in le_msg or "quota" in le_msg.lower()
                    if is_legacy_rate_limit and attempt < max_attempts - 1:
                        print(f"[Unified Model] Legacy rate limit hit (429) on attempt {attempt+1}. Attempting key rotation...")
                        if rotate_api_key():
                            continue
                    
                    if attempt == max_attempts - 1:
                        try:
                            print("[Unified Model] Gemini fallbacks failed. Trying OpenRouter free fallback...")
                            return _call_openrouter_fallback(contents, config, model_name=model_name)
                        except Exception as or_err:
                            raise RuntimeError(f"Unified model call failed on both modern and legacy Gemini fallbacks and OpenRouter fallback: {e} | {le} | {or_err}")

    # 3. NVIDIA/OpenAI API Call
    import requests
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    # Extract system instruction
    system_instruction = ""
    if config:
        # Check modern types.GenerateContentConfig
        system_instruction = getattr(config, "system_instruction", "")
        # Check if config is dict
        if isinstance(config, dict):
            system_instruction = config.get("system_instruction", "")

    messages = []
    if system_instruction:
        messages.append({"role": "system", "content": str(system_instruction)})

    # Build User Message
    user_content = []
    
    contents_list = contents if isinstance(contents, list) else [contents]
    for item in contents_list:
        if isinstance(item, str):
            user_content.append({"type": "text", "text": item})
        else:
            # Convert to base64
            b64_url = image_to_base64_url(item)
            if b64_url:
                user_content.append({"type": "image_url", "image_url": {"url": b64_url}})
            elif isinstance(item, (int, float, bool)):
                user_content.append({"type": "text", "text": str(item)})

    # If user_content only has text, simplify it
    if len(user_content) == 1 and user_content[0]["type"] == "text":
        messages.append({"role": "user", "content": user_content[0]["text"]})
    else:
        messages.append({"role": "user", "content": user_content})

    temperature = 0.2
    if config:
        temp_val = getattr(config, "temperature", None)
        if temp_val is not None:
            temperature = temp_val
        elif isinstance(config, dict) and "temperature" in config:
            temperature = config["temperature"]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }

    try:
        url = f"{base_url.rstrip('/')}/chat/completions"
        print(f"[Unified Model] Sending POST to {url} with model {model}...")
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
        resp.raise_for_status()
        res_json = resp.json()
        text_out = res_json["choices"][0]["message"]["content"]
        return UnifiedModelResponse(text=text_out)
    except Exception as e:
        if provider == "freellmapi":
            raise RuntimeError(f"FreeLLMAPI execution failed: {e}")
        print(f"[Unified Model] NVIDIA/OpenAI request failed: {e}. Falling back to Gemini...")
        # Graceful fallback to Gemini on HTTP error
        try:
            from google import genai
            client = genai.Client(api_key=get_api_key())
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=config,
                **kwargs
            )
            return UnifiedModelResponse(text=response.text or "")
        except Exception as fallback_err:
            try:
                print("[Unified Model] Nvidia and Gemini fallbacks failed. Trying OpenRouter free fallback...")
                return _call_openrouter_fallback(contents, config, model_name=model_name)
            except Exception as or_err:
                raise RuntimeError(f"Unified model failed on Nvidia, Gemini and OpenRouter: {e} | {fallback_err} | {or_err}")

# Legacy google-generativeai API compatibility wrapper
class UnifiedGenerativeModel:
    def __init__(self, model_name: str, category: str = "coding"):
        self.model_name = model_name
        self.category = category

    def generate_content(self, contents, **kwargs):
        return call_unified_model(contents, category=self.category, model_name=self.model_name, **kwargs)

# Modern google-genai API compatibility wrapper
class UnifiedModelsService:
    def __init__(self, category: str = "vision"):
        self.category = category

    def generate_content(self, model: str, contents, config=None, **kwargs):
        return call_unified_model(contents, config=config, category=self.category, model_name=model, **kwargs)

class UnifiedModelClient:
    def __init__(self, api_key: str = None, category: str = "vision", **kwargs):
        self.models = UnifiedModelsService(category=category)
