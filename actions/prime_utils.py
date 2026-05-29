"""
prime_utils.py — Core utility helper functions used across action modules.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/prime_utils.py
import sys
import json
import io
import base64
from pathlib import Path

def get_base_dir() -> Path:
    """Returns the base application directory, supporting frozen executables."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

def get_api_key() -> str:
    """Returns the central Gemini API key from config/api_keys.json."""
    path = get_base_dir() / "config" / "api_keys.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("gemini_api_key") or data.get("coding_api_key") or ""
        except Exception as e:
            print(f"[Prime Utils] Error loading API Key: {e}")
    return ""

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
    if category == "vision":
        provider = cfg.get("vision_provider", "gemini").lower()
        api_key = cfg.get("vision_api_key") or cfg.get("coding_api_key") or cfg.get("gemini_api_key", "")
        base_url = cfg.get("vision_base_url", "")
        model = model_name or cfg.get("vision_model", "nvidia/llama-3.2-11b-vision-instruct")
    else:
        provider = cfg.get("coding_provider", "gemini").lower()
        api_key = cfg.get("coding_api_key") or cfg.get("gemini_api_key", "")
        base_url = cfg.get("coding_base_url", "")
        model = model_name or cfg.get("coding_model", "nvidia/llama-3.1-nemotron-70b-instruct")

    if model and "gemini" in model.lower():
        provider = "gemini"

    # If provider is gemini or fallback triggered, run Gemini SDK
    if provider == "gemini" or not base_url or not api_key:
        if provider != "gemini":
            print(f"[Unified Model] Fallback to Gemini: provider is {provider} but base_url or api_key is missing.")
        
        # Determine standard models
        gemini_model = model_name or ("gemini-2.5-flash" if category == "vision" else "gemini-2.5-flash")
        
        try:
            # Check which client call style is being simulated
            # For google-genai style (Client.models.generate_content):
            from google import genai
            client = genai.Client(api_key=api_key or get_api_key())
            
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
            # Try legacy google-generativeai style fallback
            try:
                import google.generativeai as genai
                genai.configure(api_key=api_key or get_api_key())
                legacy_model = genai.GenerativeModel(gemini_model)
                response = legacy_model.generate_content(contents, **kwargs)
                return UnifiedModelResponse(text=response.text or "")
            except Exception as le:
                raise RuntimeError(f"Unified model call failed on both modern and legacy Gemini fallbacks: {e} | {le}")

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
            raise RuntimeError(f"Unified model failed on Nvidia and could not fall back to Gemini: {e} | {fallback_err}")

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
