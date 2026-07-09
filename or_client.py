import json
import sys
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception as _exc:  # noqa: BLE001
        logging.debug("[%s] Suppressed: %s", __name__, _exc)
import time
import base64
import logging
import re
from pathlib import Path
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("openrouter_client")

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


BASE_DIR     = _get_base_dir()
API_KEY_PATH = BASE_DIR / "config" / "api_keys.json"

def _load_api_key() -> str:
    try:
        with open(API_KEY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = data.get("openrouter_api_key", "").strip()
        if not key or len(key) < 10:
            raise ValueError(
                "openrouter_api_key missing or invalid "
                "in api_keys.json (min 10 chars expected)"
            )
        return key
    except FileNotFoundError:
        raise RuntimeError(f"api_keys.json not found at: {API_KEY_PATH}")
    except Exception as e:
        raise RuntimeError(f"Failed to load OpenRouter API key: {e}")

def _load_nvidia_key() -> str:
    try:
        if not API_KEY_PATH.exists():
            return ""
        with open(API_KEY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("nvidia_api_key", "").strip()
    except Exception:
        return ""

TEXT_MODELS: list[str] = [
    "nvidia/nemotron-3-super-120b-a12b:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "minimax/minimax-m2.5:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "qwen/qwen3-coder:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-3-27b-it:free",
    "arcee-ai/trinity-large-preview:free",
    "z-ai/glm-4.5-air:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
    "google/gemma-3-12b-it:free",
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-3-4b-it:free",
    "google/gemma-3n-e4b-it:free",
    "meta-llama/llama-3.2-3b-instruct:free",
    "google/gemma-3n-e2b-it:free",
    "liquid/lfm-2.5-1.2b-instruct:free",
    "liquid/lfm-2.5-1.2b-thinking:free",
]

VISION_MODELS: list[str] = [
    "nvidia/nemotron-nano-12b-v2-vl:free",
    "nvidia/llama-nemotron-embed-vl-1b-v2:free",
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "google/gemma-3n-e4b-it:free",
    "google/gemma-3n-e2b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

NVIDIA_MODELS: list[str] = [
    "meta/llama-3.3-70b-instruct",
    "meta/llama-3.1-70b-instruct",
    "meta/llama-3.1-8b-instruct",
]

NVIDIA_VISION_MODELS: list[str] = [
    "nvidia/llama-3.2-11b-vision-instruct",
]

API_URL               = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MAX_TOKENS    = 4096
DEFAULT_TEMPERATURE   = 0.7
REQUEST_TIMEOUT       = 60   # seconds per request
MAX_RETRIES_PER_MODEL = 2    # attempts before moving to next model
RETRY_DELAY           = 2    # seconds between retries
RATE_LIMIT_COOLDOWN   = 60   # seconds before retrying a rate-limited model

class OpenRouterClient:

    def __init__(self) -> None:
        self.api_key  = _load_api_key()
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
            "HTTP-Referer":  "https://github.com/mark-xxv",
            "X-Title":       "MARK XXV",
        }
        self.nvidia_key = _load_nvidia_key()
        
        # Local copies of models to prevent mutation of the global module lists
        model_pool = list(TEXT_MODELS)
        if self.nvidia_key:
            for model in reversed(NVIDIA_MODELS):
                if model not in model_pool:
                    model_pool.insert(0, model)
        self.text_models = model_pool

        vision_pool = list(VISION_MODELS)
        if self.nvidia_key:
            for model in reversed(NVIDIA_VISION_MODELS):
                if model not in vision_pool:
                    vision_pool.insert(0, model)
        self.vision_models = vision_pool
        
        # Instance-specific rate-limited dict
        self._rate_limited: dict[str, float] = {}

    def _is_rate_limited(self, model: str) -> bool:
        ts = self._rate_limited.get(model)
        if ts is None:
            return False
        if time.time() - ts > RATE_LIMIT_COOLDOWN:
            del self._rate_limited[model]
            return False
        return True

    def _mark_rate_limited(self, model: str) -> None:
        self._rate_limited[model] = time.time()
        logger.warning(
            f"[OpenRouter] Rate limited: {model} — "
            f"cooling down for {RATE_LIMIT_COOLDOWN}s"
        )

    def _call(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> Optional[str]:
        # Route to Nvidia direct API if nvidia_key is configured and model is an Nvidia model
        is_nvidia_model = model in NVIDIA_MODELS or model in NVIDIA_VISION_MODELS or (model.startswith("nvidia/") and not model.endswith(":free"))
        if is_nvidia_model and self.nvidia_key:
            url = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.nvidia_key}",
                "Content-Type":  "application/json",
            }
            payload = {
                "model":       model,
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": temperature,
            }
            if response_format:
                payload["response_format"] = response_format

            for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
                try:
                    resp = requests.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=REQUEST_TIMEOUT,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        return content.strip() if content else None
                    logger.warning(
                        f"[Nvidia Direct] {model} → HTTP {resp.status_code} "
                        f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                    )
                except Exception as e:
                    logger.error(f"[Nvidia Direct] {model} → Unexpected error: {e}")
                if attempt < MAX_RETRIES_PER_MODEL:
                    time.sleep(RETRY_DELAY)
            return None

        # Standard OpenRouter payload
        payload: dict = {
            "model":       model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format

        for attempt in range(1, MAX_RETRIES_PER_MODEL + 1):
            try:
                resp = requests.post(
                    API_URL,
                    headers=self._headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )

                if resp.status_code == 429:
                    self._mark_rate_limited(model)
                    return None

                if resp.status_code == 200:
                    data    = resp.json()
                    content = (
                        data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                    )
                    return content.strip() if content else None

                logger.warning(
                    f"[OpenRouter] {model} → HTTP {resp.status_code} "
                    f"body: {resp.text[:200]} "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )

            except requests.exceptions.Timeout:
                logger.warning(
                    f"[OpenRouter] {model} → Timeout "
                    f"(attempt {attempt}/{MAX_RETRIES_PER_MODEL})"
                )
            except Exception as e:
                logger.error(f"[OpenRouter] {model} → Unexpected error: {e}")

            if attempt < MAX_RETRIES_PER_MODEL:
                time.sleep(RETRY_DELAY)

        return None

    def _try_ollama(self, messages: list[dict]) -> Optional[str]:
        """Try local Ollama server as last-resort fallback (localhost:11434)."""
        import shutil
        try:
            # Only attempt if ollama binary exists
            if not shutil.which("ollama"):
                return None
            resp = requests.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": "llama3",   # falls back to mistral if not found
                    "messages": messages,
                    "stream": False,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                return content.strip() if content else None
            # Try mistral as secondary local model
            resp2 = requests.post(
                "http://localhost:11434/api/chat",
                json={"model": "mistral", "messages": messages, "stream": False},
                timeout=30,
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                content2 = data2.get("message", {}).get("content", "")
                return content2.strip() if content2 else None
        except Exception as e:
            logger.debug(f"[Ollama] Local fallback unavailable: {e}")
        return None

    def _call_with_fallback(
        self,
        pool: list[str],
        messages: list[dict],
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        response_format: Optional[dict] = None,
    ) -> str:
        if model and not self._is_rate_limited(model):
            result = self._call(model, messages, max_tokens, temperature, response_format)
            if result:
                return result
            logger.info(
                f"[OpenRouter] Requested model failed, "
                f"falling back to pool: {model}"
            )

        for m in pool:
            if self._is_rate_limited(m):
                continue
            logger.info(f"[OpenRouter] Trying: {m}")
            result = self._call(m, messages, max_tokens, temperature, response_format)
            if result:
                logger.info(f"[OpenRouter] ✓ Success: {m}")
                return result

        # ── Ollama local LLM last-resort fallback ────────────────────────
        ollama_result = self._try_ollama(messages)
        if ollama_result:
            logger.info("[Ollama] ✓ Local fallback succeeded.")
            return ollama_result

        raise RuntimeError(
            "[OpenRouter] All models failed or are rate-limited. "
            "Check your API key and network connection."
        )

    def chat(
        self,
        prompt: str,
        system: str = (
            "You are a component of MARK XXV, an AI assistant inspired by SATURDAY. "
            "Be concise, helpful, and precise."
        ),
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ]
        return self._call_with_fallback(
            self.text_models, messages, model, max_tokens, temperature
        )

    def chat_json(
        self,
        prompt: str,
        system: str = (
            "Return ONLY valid JSON. "
            "No markdown fences, no extra text, no explanation."
        ),
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> dict:
        messages = [
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ]
        raw = self._call_with_fallback(
            self.text_models, messages, model, max_tokens, temperature=0.2
        )

        clean = raw.strip()
        # Robust regex code fences stripping
        clean = re.sub(r"^```(?:json)?\s*\n?", "", clean, flags=re.IGNORECASE)
        clean = re.sub(r"\n?```$", "", clean, flags=re.IGNORECASE)
        clean = clean.strip()

        try:
            return json.loads(clean)
        except json.JSONDecodeError as e:
            logger.error(
                f"[OpenRouter] JSON parse failed: {e}\n"
                f"Raw response (first 300 chars): {raw[:300]}"
            )
            raise ValueError(
                f"Model returned unparseable JSON: {e}\n"
                f"Raw output: {raw[:200]}"
            )

    def vision(
        self,
        prompt: str,
        image_b64: str,
        mime: str = "image/png",
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        messages = [
            {"role": "system", "content": system},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime};base64,{image_b64}"
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]
        return self._call_with_fallback(
            self.vision_models, messages, model, max_tokens, temperature=temperature
        )

    def vision_from_file(
        self,
        prompt: str,
        image_path: str,
        system: str = "Analyze the image and describe what you see clearly and concisely.",
        model: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.2,
    ) -> str:
        path = Path(image_path)
        mime_map = {
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif":  "image/gif",
        }
        mime = mime_map.get(path.suffix.lower(), "image/png")

        with open(path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode("utf-8")

        return self.vision(prompt, image_b64, mime, system, model, max_tokens, temperature=temperature)

    def multi_turn(
        self,
        messages: list[dict],
        system: Optional[str] = None,
        model: Optional[str] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
    ) -> str:
        if system and not any(m.get("role") == "system" for m in messages):
            messages = [{"role": "system", "content": system}] + messages
    
        return self._call_with_fallback(
            self.text_models, messages, model, max_tokens, temperature
        )

    def available_models(self) -> dict:
        return {
            "text_models":   self.text_models,
            "vision_models": self.vision_models,
            "rate_limited":  list(self._rate_limited.keys()),
            "total_text":    len(self.text_models),
            "total_vision":  len(self.vision_models),
        }

# Module-level lazy client initialization to prevent crash on import when config is missing
_client = None

def get_client() -> OpenRouterClient:
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client

class OpenRouterProxy:
    def __getattr__(self, name):
        return getattr(get_client(), name)

client = OpenRouterProxy()

if __name__ == "__main__":
    print("=" * 55)
    print("  MARK XXV — OpenRouter Client Self-Test")
    print("=" * 55)

    client = OpenRouterClient()

    print("\n[TEST 1] Basic chat...")
    try:
        reply = client.chat("Introduce yourself in one sentence.")
        print(f"  Response : {reply}")
        print(f"  Status   : PASS ✓")
    except Exception as e:
        print(f"  Status   : FAIL ✗ — {e}")

    print("\n[TEST 2] JSON mode...")
    try:
        data = client.chat_json(
            'List 3 programming languages. Format: {"languages": ["a", "b", "c"]}',
            system="Return only valid JSON. No extra text."
        )
        print(f"  Response : {data}")
        print(f"  Status   : PASS ✓")
    except Exception as e:
        print(f"  Status   : FAIL ✗ — {e}")

    print("\n[TEST 3] Multi-turn conversation...")
    try:
        history = [
            {"role": "system",    "content": "You are a helpful assistant. Be brief."},
            {"role": "user",      "content": "My name is Tony."},
            {"role": "assistant", "content": "Hello Tony, how can I help you?"},
            {"role": "user",      "content": "What is my name?"},
        ]
        reply = client.multi_turn(history)
        print(f"  Response : {reply}")
        print(f"  Status   : PASS ✓")
    except Exception as e:
        print(f"  Status   : FAIL ✗ — {e}")

    print("\n[TEST 4] Model pool info...")
    info = client.available_models()
    print(f"  Text models   : {info['total_text']}")
    print(f"  Vision models : {info['total_vision']}")
    print(f"  Rate limited  : {info['rate_limited'] or 'none'}")
    print(f"  Status        : PASS ✓")

    print("\n" + "=" * 55)
    print("  All tests complete.")
    print("=" * 55)