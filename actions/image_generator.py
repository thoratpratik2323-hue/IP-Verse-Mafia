"""
image_generator.py — Premium AI Image & Art Generation engine for IP Prime.

Supports:
1. Ideogram API (v4 / v2)
2. Replicate API (Flux / SDXL)
3. Pollinations.ai (100% Free out-of-the-box fallback, zero API keys required!)

Saves generated artwork to CODING PROJECTS/exports/ and automatically opens it.
"""

from __future__ import annotations

import os
import sys
import json
import time
import urllib.parse
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ip_prime.image_generator")

def _get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = _get_base_dir()
API_KEY_PATH = BASE_DIR / "config" / "api_keys.json"
EXPORTS_DIR = BASE_DIR / "CODING PROJECTS" / "exports"

def _load_keys() -> dict[str, str]:
    try:
        if API_KEY_PATH.exists():
            with open(API_KEY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "ideogram": data.get("ideogram_api_key", "").strip(),
                "replicate": data.get("replicate_api_key", "").strip()
            }
    except Exception as e:
        logger.error(f"Failed to load image generation API keys: {e}")
    return {"ideogram": "", "replicate": ""}

def _generate_pollinations(prompt: str, aspect_ratio: str) -> Optional[bytes]:
    """Generates an image via Pollinations.ai free API (Flux/Stable Diffusion)."""
    logger.info(f"[ImageGen] Routing to Pollinations (Free Tier). Prompt: {prompt}")
    
    # Map aspect ratio to resolution
    ratio_map = {
        "1:1": (1024, 1024),
        "16:9": (1280, 720),
        "9:16": (720, 1280),
        "4:3": (1024, 768),
        "3:4": (768, 1024)
    }
    width, height = ratio_map.get(aspect_ratio, (1024, 1024))
    
    # Clean and encode prompt
    safe_prompt = urllib.parse.quote(prompt.strip())
    seed = int(time.time())
    
    # We use the Flux model on Pollinations
    url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width={width}&height={height}&seed={seed}&nologo=true&private=true&enhance=true"
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.error(f"[ImageGen] Pollinations generation failed: {e}")
    return None

def _generate_replicate(prompt: str, aspect_ratio: str, api_key: str) -> Optional[bytes]:
    """Generates an image via Replicate API using black-forest-labs/flux-schnell."""
    logger.info(f"[ImageGen] Routing to Replicate. Prompt: {prompt}")
    
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    
    # Create prediction
    payload = {
        "input": {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "disable_safety_checker": True
        }
    }
    
    # Using Replicate's flux-schnell model deployment endpoint
    model_url = "https://api.replicate.com/v1/models/black-forest-labs/flux-schnell/predictions"
    
    try:
        resp = requests.post(model_url, json=payload, headers=headers, timeout=20)
        resp.raise_for_status()
        pred = resp.json()
        
        get_url = pred.get("urls", {}).get("get")
        if not get_url:
            return None
            
        # Poll prediction status
        for _ in range(30): # max 30 seconds
            status_resp = requests.get(get_url, headers=headers, timeout=10)
            status_resp.raise_for_status()
            status_data = status_resp.json()
            
            status = status_data.get("status")
            if status == "succeeded":
                output = status_data.get("output")
                img_url = output[0] if isinstance(output, list) else output
                if img_url:
                    img_resp = requests.get(img_url, timeout=20)
                    img_resp.raise_for_status()
                    return img_resp.content
                break
            elif status in ["failed", "canceled"]:
                logger.error(f"[ImageGen] Replicate prediction {status}.")
                break
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"[ImageGen] Replicate generation failed: {e}")
    return None

def _generate_ideogram(prompt: str, aspect_ratio: str, api_key: str) -> Optional[bytes]:
    """Generates an image via Ideogram API."""
    logger.info(f"[ImageGen] Routing to Ideogram. Prompt: {prompt}")
    
    url = "https://api.ideogram.ai/v1/generate"
    headers = {
        "Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Map ratio
    ratio_str = f"ASPECT_{aspect_ratio.replace(':', '_')}"
    
    payload = {
        "image_request": {
            "prompt": prompt,
            "aspect_ratio": ratio_str,
            "model": "V_2",
            "magic_prompt": "AUTO"
        }
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # Ideogram returns direct output URLs inside image_request output
        images = data.get("data", [])
        if images:
            img_url = images[0].get("url")
            if img_url:
                img_resp = requests.get(img_url, timeout=20)
                img_resp.raise_for_status()
                return img_resp.content
    except Exception as e:
        logger.error(f"[ImageGen] Ideogram generation failed: {e}")
    return None

def generate_image(prompt: str, aspect_ratio: str = "1:1", provider: str = "auto") -> str:
    """Core image generation coordinator."""
    if not prompt:
        return "Prompt empty hai bro! Please provide a prompt to generate an image."
        
    keys = _load_keys()
    img_data = None
    selected_prov = "pollinations"
    
    # Standardize parameters
    provider = provider.lower().strip()
    aspect_ratio = aspect_ratio.strip()
    
    # 1. Routing Strategy
    if provider == "ideogram" and keys["ideogram"]:
        img_data = _generate_ideogram(prompt, aspect_ratio, keys["ideogram"])
        selected_prov = "ideogram"
    elif provider == "replicate" and keys["replicate"]:
        img_data = _generate_replicate(prompt, aspect_ratio, keys["replicate"])
        selected_prov = "replicate"
    elif provider == "pollinations":
        img_data = _generate_pollinations(prompt, aspect_ratio)
        selected_prov = "pollinations"
    else:
        # Auto-selection cascade
        if keys["ideogram"]:
            img_data = _generate_ideogram(prompt, aspect_ratio, keys["ideogram"])
            selected_prov = "ideogram"
        
        if not img_data and keys["replicate"]:
            img_data = _generate_replicate(prompt, aspect_ratio, keys["replicate"])
            selected_prov = "replicate"
            
        if not img_data:
            img_data = _generate_pollinations(prompt, aspect_ratio)
            selected_prov = "pollinations"

    if not img_data:
        return "Afsos, image generate nahi ho payi, sir. Ek baar details aur API keys check kar lijiye."

    # 2. Save image to disk
    try:
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"art_{timestamp}.png"
        full_path = EXPORTS_DIR / filename
        
        with open(full_path, "wb") as f:
            f.write(img_data)
            
        # 3. Open image automatically on system
        try:
            if sys.platform == "win32":
                os.startfile(full_path)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.run(["open", str(full_path)])
            else:
                import subprocess
                subprocess.run(["xdg-open", str(full_path)])
        except Exception as oe:
            logger.warning(f"Could not open image file automatically: {oe}")
            
        rel_path = f"CODING PROJECTS/exports/{filename}"
        return (
            f"✅ **Image generate ho gayi hai, sir!**\n\n"
            f"* **Prompt:** \"{prompt}\"\n"
            f"* **Provider:** {selected_prov.upper()}\n"
            f"* **Saved to:** `{rel_path}`\n\n"
            f"Maine image aapke system par open kar di hai!"
        )
    except Exception as se:
        logger.error(f"Error saving generated image file: {se}")
        return f"Image generate to ho gayi thi par file save karne mein error aaya: {se}"

def image_generator(parameters: dict[str, Any], player: Optional[Any] = None) -> str:
    """Main tool entry point for IP Prime image generator."""
    prompt = parameters.get("prompt", "")
    aspect_ratio = parameters.get("aspect_ratio", "1:1")
    provider = parameters.get("provider", "auto")
    
    return generate_image(prompt, aspect_ratio, provider)
