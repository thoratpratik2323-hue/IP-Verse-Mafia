import subprocess
import platform
import logging

logger = logging.getLogger("saturday.core.hardware_optimizer")

def detect_gpu_hardware() -> dict:
    """Detects the name and type of graphics hardware on the user's system."""
    gpu_name = "Unknown Graphics Device"
    gpu_type = "cpu"  # cpu, nvidia, amd, intel, apple_silicon
    
    system = platform.system()
    if system == "Windows":
        try:
            # Query GPU Name using PowerShell (fast and standard)
            cmd = "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"
            out = subprocess.check_output(["powershell", "-Command", cmd], text=True, stderr=subprocess.DEVNULL)
            gpu_name = out.strip()
            
            gpu_name_lower = gpu_name.lower()
            if "nvidia" in gpu_name_lower or "geforce" in gpu_name_lower:
                gpu_type = "nvidia"
            elif "amd" in gpu_name_lower or "radeon" in gpu_name_lower:
                gpu_type = "amd"
            elif "intel" in gpu_name_lower:
                gpu_type = "intel"
        except Exception as e:
            logger.debug("Failed to detect GPU on Windows: %s", e)
            
    elif system == "Darwin":  # macOS
        try:
            # Check for Apple Silicon vs Intel
            out = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True)
            gpu_name = out.strip()
            if "Apple" in gpu_name:
                gpu_type = "apple_silicon"
            else:
                gpu_type = "intel"
        except Exception as e:
            logger.debug("Failed to detect hardware on macOS: %s", e)
            
    elif system == "Linux":
        try:
            # Try lspci
            out = subprocess.check_output("lspci | grep -i vga", shell=True, text=True)
            gpu_name = out.strip()
            gpu_name_lower = gpu_name.lower()
            if "nvidia" in gpu_name_lower:
                gpu_type = "nvidia"
            elif "amd" in gpu_name_lower or "ati" in gpu_name_lower:
                gpu_type = "amd"
            elif "intel" in gpu_name_lower:
                gpu_type = "intel"
        except Exception as e:
            logger.debug("Failed to detect GPU on Linux: %s", e)
            
    return {
        "gpu_name": gpu_name,
        "gpu_type": gpu_type
    }

def get_hardware_recommendations() -> dict:
    """Returns recommended local model parameters based on detected GPU."""
    hardware = detect_gpu_hardware()
    gpu_type = hardware["gpu_type"]
    gpu_name = hardware["gpu_name"]
    
    if gpu_type in ("nvidia", "apple_silicon"):
        rec_model = "mistral"
        rec_embed = "nomic-embed-text"
        rec_text = "Recommend 7B/8B models (e.g. Llama 3, Mistral)"
    elif gpu_type == "amd":
        rec_model = "mistral"
        rec_embed = "nomic-embed-text"
        rec_text = "Recommend 7B/8B models (ROCm supported)"
    elif gpu_type == "intel":
        rec_model = "qwen2.5:3b"
        rec_embed = "all-minilm"
        rec_text = "Recommend 1B/3B models (e.g. Qwen 3B, Llama 3.2 3B)"
    else:
        rec_model = "qwen2.5:1.5b"
        rec_embed = "all-minilm"
        rec_text = "Recommend 1B/3B lightweight models"
        
    return {
        "gpu_name": gpu_name,
        "gpu_type": gpu_type,
        "recommended_model": rec_model,
        "recommended_embed": rec_embed,
        "recommendation_text": rec_text
    }
