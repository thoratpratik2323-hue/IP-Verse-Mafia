# actions/huggingface_tool.py
import os
import sys
import time
import json
import requests
from io import BytesIO
from pathlib import Path

# Try to import optional packages for screenshot and webcam
try:
    import PIL.Image as Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import mss
    _MSS_OK = True
except ImportError:
    _MSS_OK = False

try:
    import cv2
    _CV2_OK = True
except ImportError:
    _CV2_OK = False

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()

def get_hf_api_key() -> str:
    # 1. Try to load from config/api_keys.json
    api_config_path = BASE_DIR / "config" / "api_keys.json"
    if api_config_path.exists():
        try:
            with open(api_config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                key = config.get("huggingface_api_key", "").strip()
                if key:
                    return key
        except Exception as e:
            print(f"[HF Tool] Warning: Failed to read api_keys.json: {e}")

    # 2. Fall back to environment variables
    key = os.environ.get("HUGGINGFACE_API_KEY") or os.environ.get("HF_TOKEN")
    if key:
        return key.strip()

    return ""

def query_hf_api(model_id: str, payload, api_key: str = None, is_binary: bool = False) -> dict:
    url = f"https://api-inference.huggingface.co/models/{model_id}"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    if is_binary:
        headers["Content-Type"] = "application/octet-stream"

    max_retries = 5
    for attempt in range(max_retries):
        try:
            if is_binary:
                response = requests.post(url, headers=headers, data=payload, timeout=45)
            else:
                response = requests.post(url, headers=headers, json=payload, timeout=45)

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    # Some models might return raw text or binary data directly, but standard serverless returns JSON
                    return {"result": response.text}
            elif response.status_code == 503:
                # Model is loading
                try:
                    error_data = response.json()
                except Exception:
                    error_data = {}
                estimated_time = error_data.get("estimated_time", 5.0)
                wait_time = min(estimated_time, 10.0)
                print(f"[HF Tool] Model {model_id} is loading. Waiting {wait_time}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait_time)
            elif response.status_code == 401:
                return {"error": "Unauthorized. Please check your Hugging Face API key."}
            elif response.status_code == 404:
                return {"error": f"Model {model_id} not found."}
            else:
                return {"error": f"API returned HTTP {response.status_code}", "details": response.text}
        except Exception as e:
            print(f"[HF Tool] Exception on attempt {attempt+1}: {e}")
            if attempt == max_retries - 1:
                return {"error": f"Failed to connect to Hugging Face: {str(e)}"}
            time.sleep(2.0)

    return {"error": "Model failed to load after multiple retries."}

def capture_screenshot() -> bytes:
    if not _MSS_OK or not _PIL_OK:
        raise RuntimeError("Screenshot capabilities are unavailable (mss/pillow missing).")
    with mss.MSS() as sct:
        # Grab primary monitor safely (fallback to 0 if 1 is not present)
        monitor = sct.monitors[1] if len(sct.monitors) >= 2 else sct.monitors[0]
        sct_img = sct.grab(monitor)
        img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        output = BytesIO()
        img.save(output, format="JPEG")
        return output.getvalue()

def capture_webcam() -> bytes:
    if not _CV2_OK or not _PIL_OK:
        raise RuntimeError("Webcam capabilities are unavailable (opencv/pillow missing).")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam device.")
    
    # Warm up camera frame buffer
    for _ in range(5):
        cap.read()
    ret, frame = cap.read()
    cap.release()

    if not ret:
        raise RuntimeError("Failed to capture image frame from webcam.")

    # Convert BGR to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb_frame)
    output = BytesIO()
    img.save(output, format="JPEG")
    return output.getvalue()

def get_image_bytes(image_path: str) -> bytes:
    # 1. Handle special triggers
    if image_path.lower() == "screenshot":
        return capture_screenshot()
    elif image_path.lower() == "webcam":
        return capture_webcam()

    # 2. Handle URL
    if image_path.startswith("http://") or image_path.startswith("https://"):
        response = requests.get(image_path, timeout=20)
        response.raise_for_status()
        return response.content

    # 3. Handle Local File Path
    p = Path(image_path)
    if not p.is_absolute():
        # Try resolving relative to BASE_DIR
        p = BASE_DIR / p
    if not p.exists():
        raise FileNotFoundError(f"Local image file not found at: {image_path}")
    with open(p, "rb") as f:
        return f.read()

def huggingface_tool(parameters=None, player=None, speak=None) -> str:
    params = parameters or {}
    task = params.get("task", "").lower().strip()
    text = params.get("text", "").strip()
    image_path = params.get("image_path", "").strip()
    model = params.get("model", "").strip()

    if not task:
        return "Error: Missing required parameter 'task'."

    api_key = get_hf_api_key()
    if player and hasattr(player, "write_log"):
        player.write_log(f"HF: Executing task '{task}' with model '{model or 'default'}'")

    try:
        if task == "text_generation":
            if not text:
                return "Error: Parameter 'text' is required for text_generation."
            # Default model
            model_id = model or "mistralai/Mistral-7B-Instruct-v0.3"
            payload = {
                "inputs": text,
                "parameters": {
                    "max_new_tokens": 250,
                    "temperature": 0.7
                }
            }
            res = query_hf_api(model_id, payload, api_key)
            if "error" in res:
                # Try fallback model
                fallback = "Qwen/Qwen2.5-7B-Instruct"
                if model_id != fallback and not model:
                    print(f"[HF Tool] Primary model failed, trying fallback {fallback}...")
                    res = query_hf_api(fallback, payload, api_key)

            if "error" in res:
                return f"Error: {res['error']}. Details: {res.get('details', '')}"

            if isinstance(res, list) and len(res) > 0:
                gen_text = res[0].get("generated_text", "")
                # Clean prompt prepending if model does it
                if gen_text.startswith(text):
                    gen_text = gen_text[len(text):].strip()
                return gen_text
            elif isinstance(res, dict) and "generated_text" in res:
                return res["generated_text"]
            return str(res)

        elif task == "summarization":
            if not text:
                return "Error: Parameter 'text' is required for summarization."
            model_id = model or "facebook/bart-large-cnn"
            payload = {"inputs": text}
            res = query_hf_api(model_id, payload, api_key)
            if "error" in res:
                return f"Error: {res['error']}. Details: {res.get('details', '')}"

            if isinstance(res, list) and len(res) > 0:
                return res[0].get("summary_text", "")
            return str(res)

        elif task == "sentiment_analysis":
            if not text:
                return "Error: Parameter 'text' is required for sentiment_analysis."
            model_id = model or "distilbert-base-uncased-finetuned-sst-2-english"
            payload = {"inputs": text}
            res = query_hf_api(model_id, payload, api_key)
            if "error" in res:
                return f"Error: {res['error']}. Details: {res.get('details', '')}"

            if isinstance(res, list) and len(res) > 0:
                scores = res[0]
                if isinstance(scores, list):
                    formatted = []
                    for item in scores:
                        lbl = item.get("label", "Unknown")
                        sc = item.get("score", 0.0)
                        formatted.append(f"{lbl}: {sc:.2%}")
                    return ", ".join(formatted)
            return str(res)

        elif task == "image_captioning":
            if not image_path:
                return "Error: Parameter 'image_path' is required for image_captioning."
            model_id = model or "Salesforce/blip-image-captioning-base"
            
            try:
                img_bytes = get_image_bytes(image_path)
            except Exception as e:
                return f"Error loading image '{image_path}': {e}"

            res = query_hf_api(model_id, img_bytes, api_key, is_binary=True)
            if "error" in res:
                return f"Error: {res['error']}. Details: {res.get('details', '')}"

            if isinstance(res, list) and len(res) > 0:
                return res[0].get("generated_text", "")
            return str(res)

        else:
            return f"Error: Unsupported task '{task}'."

    except Exception as e:
        return f"Error executing Hugging Face tool: {e}"
