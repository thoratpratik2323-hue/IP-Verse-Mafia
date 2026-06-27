"""
computer_control.py — Low-level OS controller wrapper simulating clicks, hotkeys, and cursor movements.

This is a standard action module for the IP Prime personal assistant suite.
"""

#computer_control.py
import io
import json
import re
import string
import subprocess
import sys
import time
import random
from pathlib import Path

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE    = 0.05
    _PYAUTOGUI = True
except ImportError:
    _PYAUTOGUI = False

try:
    import pyperclip
    _PYPERCLIP = True
except ImportError:
    _PYPERCLIP = False

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


_BASE         = _base_dir()
_CONFIG_PATH  = _BASE / "config" / "api_keys.json"
_MEMORY_PATH  = _BASE / "memory" / "long_term.json"

def _load_config() -> dict:
    try:
        return json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get_os() -> str:
    return _load_config().get("os_system", "windows").lower()


def _get_api_key() -> str:
    return _load_config().get("gemini_api_key", "")

_SAFE_SCREENSHOT_ROOTS = (
    Path.home(),
)

def _safe_screenshot_path(requested: str | None) -> Path:
    fallback = Path.home() / "Desktop" / "ipprime_screenshot.png"
    if not requested:
        return fallback
    try:
        p = Path(requested).expanduser().resolve()
        for root in _SAFE_SCREENSHOT_ROOTS:
            if p.is_relative_to(root.resolve()):
                p.parent.mkdir(parents=True, exist_ok=True)
                return p
    except Exception:
        pass
    return fallback

def _require_pyautogui():
    if not _PYAUTOGUI:
        raise RuntimeError("PyAutoGUI not installed. Run: pip install pyautogui")

_FIRST_NAMES = [
    "Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Drew", "Quinn",
    "Avery", "Blake", "Cameron", "Dakota", "Emerson", "Finley", "Harper",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Wilson", "Moore", "Taylor", "Anderson", "Thomas", "Jackson",
]
_DOMAINS = ["gmail.com", "yahoo.com", "outlook.com", "proton.me", "mail.com"]


def _random_data(data_type: str) -> str:
    dt = data_type.lower().strip()

    if dt == "first_name":
        return random.choice(_FIRST_NAMES)

    if dt == "last_name":
        return random.choice(_LAST_NAMES)

    if dt == "name":
        return f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES)}"

    if dt == "email":
        first = random.choice(_FIRST_NAMES).lower()
        last  = random.choice(_LAST_NAMES).lower()
        num   = random.randint(10, 999)
        return f"{first}.{last}{num}@{random.choice(_DOMAINS)}"

    if dt == "username":
        return f"{random.choice(_FIRST_NAMES).lower()}{random.randint(100, 9999)}"

    if dt == "password":
        chars = string.ascii_letters + string.digits + "!@#$%"
        raw   = (
            random.choice(string.ascii_uppercase)
            + random.choice(string.digits)
            + random.choice("!@#$%")
            + "".join(random.choices(chars, k=9))
        )
        return "".join(random.sample(raw, len(raw)))

    if dt == "phone":
        return f"+1{random.randint(200,999)}{random.randint(1_000_000, 9_999_999)}"

    if dt == "birthday":
        y = random.randint(1980, 2000)
        m = random.randint(1, 12)
        d = random.randint(1, 28)
        return f"{m:02d}/{d:02d}/{y}"

    if dt == "address":
        num    = random.randint(100, 9999)
        street = random.choice(["Main St", "Oak Ave", "Park Blvd", "Elm St", "Cedar Ln"])
        return f"{num} {street}"

    if dt == "zip_code":
        return str(random.randint(10000, 99999))

    if dt == "city":
        return random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix"])

    return f"random_{data_type}_{random.randint(1000, 9999)}"

def _user_profile() -> dict:
    """Read identity fields from long-term memory."""
    try:
        if _MEMORY_PATH.exists():
            data     = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
            identity = data.get("identity", {})
            return {k: v.get("value", "") for k, v in identity.items()}
    except Exception:
        pass
    return {}

def _type(text: str, interval: float = 0.03) -> str:
    _require_pyautogui()
    time.sleep(0.3)
    pyautogui.typewrite(text, interval=interval)
    return f"Typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def _smart_type(text: str, clear_first: bool = True) -> str:
    _require_pyautogui()
    if clear_first:
        _clear_field()
        time.sleep(0.1)

    if len(text) > 20 and _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey("ctrl", "v")
        return f"Smart-typed (clipboard): {text[:60]}{'…' if len(text) > 60 else ''}"

    pyautogui.typewrite(text, interval=0.04)
    return f"Smart-typed: {text[:60]}{'…' if len(text) > 60 else ''}"


def phantom_type(prompt: str) -> str:
    """God-Mode inline typing. Uses Gemini to generate text from a prompt and simulates keyboard typing or clipboard pasting."""
    api_key = _get_api_key()
    if not api_key:
        return "Phantom failed: Gemini API key not found in config."
        
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        system_instruction = "You are Phantom, an inline code/text generator. Output ONLY the raw text or code requested. NO markdown formatting blocks like ```python. NO conversational text. Just the exact string."
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Request: {prompt}",
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        
        text = response.text or ""
        if not text:
            return "Phantom failed: Empty response from AI."
            
        return _smart_type(text, clear_first=False)
    except Exception as e:
        return f"Phantom failed: {e}"


def _click(x=None, y=None, button: str = "left", clicks: int = 1) -> str:
    _require_pyautogui()
    if x is not None and y is not None:
        pyautogui.click(x, y, button=button, clicks=clicks)
        return f"{'Double-c' if clicks == 2 else 'C'}licked ({x}, {y}) [{button}]"
    pyautogui.click(button=button, clicks=clicks)
    return f"Clicked at current position [{button}]"


def _hotkey(*keys) -> str:
    _require_pyautogui()
    pyautogui.hotkey(*keys)
    return f"Hotkey: {'+'.join(keys)}"


def _press(key: str) -> str:
    _require_pyautogui()
    pyautogui.press(key)
    return f"Pressed: {key}"


def _scroll(direction: str = "down", amount: int = 3) -> str:
    _require_pyautogui()
    vertical   = direction in ("up", "down")
    clicks     = amount if direction in ("up", "right") else -amount
    pyautogui.scroll(clicks) if vertical else pyautogui.hscroll(clicks)
    return f"Scrolled {direction} ×{amount}"


def _move(x: int, y: int, duration: float = 0.3) -> str:
    _require_pyautogui()
    pyautogui.moveTo(x, y, duration=duration)
    return f"Mouse → ({x}, {y})"


def _drag(x1: int, y1: int, x2: int, y2: int, duration: float = 0.5) -> str:
    _require_pyautogui()
    pyautogui.moveTo(x1, y1, duration=0.2)
    pyautogui.dragTo(x2, y2, duration=duration, button="left")
    return f"Dragged ({x1},{y1}) → ({x2},{y2})"


def _clipboard_get() -> str:
    if _PYPERCLIP:
        return pyperclip.paste()
    _hotkey("ctrl", "c")
    time.sleep(0.2)
    return "(copied — pyperclip unavailable for read)"


def _clipboard_paste(text: str) -> str:
    if _PYPERCLIP:
        pyperclip.copy(text)
        time.sleep(0.1)
        _require_pyautogui()
        pyautogui.hotkey("ctrl", "v")
        return f"Pasted: {text[:60]}{'…' if len(text) > 60 else ''}"
    return "pyperclip not available"


def _screenshot(save_path: str | None = None) -> str:
    _require_pyautogui()
    path = _safe_screenshot_path(save_path)
    img  = pyautogui.screenshot()
    img.save(str(path))
    return f"Screenshot saved: {path}"


def _clear_field() -> str:
    _require_pyautogui()
    pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    pyautogui.press("delete")
    return "Field cleared"

def _focus_window(title: str) -> str:
    import platform
    os_name = _get_os()

    if os_name == "windows":
        if not title or title.strip() in ["", "None"]:
            return "Which application should I switch to, Sir?"
        name_l = title.lower().strip()
        PROCESS_NAMES = {
            "chrome": "chrome",
            "browser": "chrome",
            "firefox": "firefox",
            "notepad": "notepad",
            "vs code": "code",
            "code": "code",
            "spotify": "spotify",
            "calculator": "calculator",
            "calc": "calculator",
            "paint": "mspaint",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
        }
        proc_name = PROCESS_NAMES.get(name_l, name_l)
        try:
            ps_script = (
                "add-type -TypeDefinition 'using System; using System.Runtime.InteropServices; "
                "public class Win32 { [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(IntPtr hWnd); "
                "[DllImport(\"user32.dll\")] public static extern bool ShowWindowAsync(IntPtr hWnd, int nCmdShow); }';"
                f"$proc = Get-Process | Where-Object {{ $_.ProcessName -eq '{proc_name}' -or $_.MainWindowTitle -like '*{name_l}*' -or $_.ProcessName -like '*{name_l}*' }} | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1;"
                "if ($proc) { [Win32]::ShowWindowAsync($proc.MainWindowHandle, 9) | Out-Null; [Win32]::SetForegroundWindow($proc.MainWindowHandle) | Out-Null; Write-Output 'Success' } else { Write-Output 'NotFound' }"
            )
            res = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            print(f"[SWITCH APP TELEMETRY] Target: {proc_name} -> {res.stdout.strip()}")
            time.sleep(0.3)
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (Windows) failed: {e}"

    if os_name == "mac":
        script = (
            f'tell application "System Events" to '
            f'set frontmost of (first process whose name contains "{title}") to true'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except Exception as e:
            return f"focus_window (macOS) failed: {e}"

    if os_name == "linux":
        try:
            result = subprocess.run(
                ["wmctrl", "-a", title],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                time.sleep(0.3)
                return f"Focused window: {title}"
        except FileNotFoundError:
            pass
        try:
            result = subprocess.run(
                ["xdotool", "search", "--name", title, "windowactivate"],
                capture_output=True, timeout=5,
            )
            time.sleep(0.3)
            return f"Focused window: {title}"
        except FileNotFoundError:
            return "focus_window (Linux) requires wmctrl or xdotool"
        except Exception as e:
            return f"focus_window (Linux) failed: {e}"

    return f"focus_window: unknown OS '{os_name}'"

def _find_element_on_screen(description: str, api_key: str) -> tuple[int, int] | None:
    """
    Advanced 2-Stage Visual Grounding Locator for ultra-precise screen targeting:
    - Stage 1: Calls Gemini 2.5 Flash with the full screenshot to obtain the target bounding box
               in normalized coordinates [ymin, xmin, ymax, xmax] (scale 0-1000).
    - Stage 2: Crops a 300x300 area around the Stage 1 center and performs a zoomed-in precision call
               to pinpoint the exact click coordinates relative to the crop.
    - Robust parsing and fallback strategies ensure pixel-perfect accuracy with safe fallbacks.
    """
    try:
        from google import genai
        from google.genai import types as gtypes

        _require_pyautogui()
        w, h = pyautogui.size()
        img = pyautogui.screenshot()
        phys_w, phys_h = img.width, img.height
        
        # Calculate DPI scale factors dynamically
        scale_x = (phys_w / w) if w > 0 else 1.0
        scale_y = (phys_h / h) if h > 0 else 1.0
        
        # --- Stage 1: Coarse Grounding using Normalized Bounding Box ---
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        full_image_bytes = buf.getvalue()

        client = genai.Client(api_key=api_key)
        
        stage1_prompt = (
            f"You are a high-precision screen coordinate locator. Locate the UI element described as: '{description}'.\n"
            f"Return the exact 2D bounding box of the element as standard normalized coordinates in the form [ymin, xmin, ymax, xmax] on a scale of 0 to 1000 "
            f"(where ymin, xmin, ymax, xmax represent the percentage of height and width from the top-left corner, multiplied by 1000).\n"
            f"Reply with ONLY the coordinates in the format [ymin, xmin, ymax, xmax]. If not found, reply NOT_FOUND."
        )

        print(f"[PrecisionLocator] 🔍 Stage 1: Locating element '{description}' on full logical {w}x{h} (physical {phys_w}x{phys_h}) screen...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                gtypes.Part.from_bytes(data=full_image_bytes, mime_type="image/png"),
                stage1_prompt,
            ],
        )

        text = (response.text or "").strip()
        print(f"[PrecisionLocator] Stage 1 raw response: '{text}'")

        if "NOT_FOUND" in text.upper():
            print("[PrecisionLocator] Element reported as NOT_FOUND in Stage 1")
            return None

        # Parse coordinates using robust regex
        # 1. Bbox check [ymin, xmin, ymax, xmax]
        bbox_match = re.search(r"[\[\(]\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*[\]\)]", text)
        phys_cx, phys_cy = None, None
        
        if bbox_match:
            ymin = int(bbox_match.group(1))
            xmin = int(bbox_match.group(2))
            ymax = int(bbox_match.group(3))
            xmax = int(bbox_match.group(4))
            
            # Check if normalized (usually scale 0-1000)
            if ymin > 1000 or xmin > 1000 or ymax > 1000 or xmax > 1000:
                # Absolute pixel coordinates
                raw_cx = int((xmin + xmax) / 2)
                raw_cy = int((ymin + ymax) / 2)
                if raw_cx > w or raw_cy > h:
                    phys_cx = raw_cx
                    phys_cy = raw_cy
                else:
                    phys_cx = int(raw_cx * scale_x)
                    phys_cy = int(raw_cy * scale_y)
                print(f"[PrecisionLocator] Stage 1 parsed absolute bbox -> Physical Coarse Center: ({phys_cx}, {phys_cy})")
            else:
                # Normalized coordinates map directly to physical pixels
                phys_cx = int(((xmin + xmax) / 2.0) / 1000.0 * phys_w)
                phys_cy = int(((ymin + ymax) / 2.0) / 1000.0 * phys_h)
                print(f"[PrecisionLocator] Stage 1 parsed normalized bbox [{ymin}, {xmin}, {ymax}, {xmax}] -> Physical Coarse Center: ({phys_cx}, {phys_cy})")
        else:
            # 2. X,Y coordinates check
            xy_match = re.search(r"(\d+)\s*,\s*(\d+)", text)
            if xy_match:
                raw_cx = int(xy_match.group(1))
                raw_cy = int(xy_match.group(2))
                if raw_cx > w or raw_cy > h:
                    phys_cx = raw_cx
                    phys_cy = raw_cy
                else:
                    phys_cx = int(raw_cx * scale_x)
                    phys_cy = int(raw_cy * scale_y)
                print(f"[PrecisionLocator] Stage 1 parsed raw xy coordinates -> Physical Coarse Center: ({phys_cx}, {phys_cy})")

        if phys_cx is None or phys_cy is None:
            print("[PrecisionLocator] ⚠️ Stage 1 could not extract coordinates from output.")
            return None

        # Ensure physical coordinates are within physical screen boundaries
        phys_cx = max(0, min(phys_w - 1, phys_cx))
        phys_cy = max(0, min(phys_h - 1, phys_cy))

        # --- Stage 2: Precision Zoom (Fine Grounding on 300x300 crop in physical space) ---
        phys_crop_size = 300
        phys_half_crop = phys_crop_size // 2
        
        phys_left = max(0, phys_cx - phys_half_crop)
        phys_top = max(0, phys_cy - phys_half_crop)
        phys_right = min(phys_w, phys_cx + phys_half_crop)
        phys_bottom = min(phys_h, phys_cy + phys_half_crop)
        
        phys_crop_w = phys_right - phys_left
        phys_crop_h = phys_bottom - phys_top
        
        if phys_crop_w > 50 and phys_crop_h > 50:
            print(f"[PrecisionLocator] 🔍 Stage 2: Zooming in. Cropping {phys_crop_w}x{phys_crop_h} centered at physical ({phys_cx}, {phys_cy})...")
            # Crop physical image
            cropped_img = img.crop((phys_left, phys_top, phys_right, phys_bottom))
            crop_buf = io.BytesIO()
            cropped_img.save(crop_buf, format="PNG")
            crop_image_bytes = crop_buf.getvalue()

            stage2_prompt = (
                f"This is a zoomed-in, close-up crop of a screen, centered near the UI element: '{description}'.\n"
                f"The crop dimensions are {phys_crop_w}×{phys_crop_h} pixels.\n"
                f"Your goal is to find the EXACT pixel coordinates within this crop to click the element.\n"
                f"Please locate the precise center of the element and reply with ONLY its coordinates in the format: crop_x,crop_y\n"
                f"where crop_x is between 0 and {phys_crop_w}, and crop_y is between 0 and {phys_crop_h}.\n"
                f"If the target element '{description}' is not visible or identifiable in this crop, reply: NOT_FOUND."
            )

            try:
                response2 = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        gtypes.Part.from_bytes(data=crop_image_bytes, mime_type="image/png"),
                        stage2_prompt,
                    ],
                )
                text2 = (response2.text or "").strip()
                print(f"[PrecisionLocator] Stage 2 raw response: '{text2}'")

                if "NOT_FOUND" not in text2.upper():
                    crop_match = re.search(r"(\d+)\s*,\s*(\d+)", text2)
                    if crop_match:
                        crop_x = int(crop_match.group(1))
                        crop_y = int(crop_match.group(2))
                        
                        # Validate that the model-returned point is within crop bounds
                        if 0 <= crop_x <= phys_crop_w and 0 <= crop_y <= phys_crop_h:
                            # Exact coordinate in physical screen space
                            phys_exact_x = phys_left + crop_x
                            phys_exact_y = phys_top + crop_y
                            
                            # Convert physical screen space coordinate to logical space for PyAutoGUI
                            exact_x = int(phys_exact_x / scale_x)
                            exact_y = int(phys_exact_y / scale_y)
                            print(f"[PrecisionLocator] ✨ Stage 2 Precision Match! Crop relative: ({crop_x}, {crop_y}) -> Physical Screen: ({phys_exact_x}, {phys_exact_y}) -> Logical Screen: ({exact_x}, {exact_y})")
                            return exact_x, exact_y
            except Exception as e2:
                print(f"[PrecisionLocator] ⚠️ Stage 2 Zoom failed: {e2}. Falling back to Stage 1 coarse center.")

        # Fallback to Stage 1 Coarse center mapped to logical space
        logical_cx = int(phys_cx / scale_x)
        logical_cy = int(phys_cy / scale_y)
        print(f"[PrecisionLocator] ℹ️ Falling back to Stage 1 Coarse Center in logical space: ({logical_cx}, {logical_cy})")
        return logical_cx, logical_cy

    except Exception as e:
        print(f"[PrecisionLocator] ❌ Advanced visual locator failed: {e}")
        return None

def _screen_find(description: str) -> tuple[int, int] | None:
    api_key = _get_api_key()
    if not api_key:
        print("[ComputerControl] ⚠️ No API key for screen_find")
        return None
    return _find_element_on_screen(description, api_key)

def _execute_ui_tars_agent(goal: str, player=None) -> str:
    """
    UI-TARS Vision Desktop Automation Agent loop (max 12 steps).
    Takes desktop screenshots, sends them to Gemini 2.5 Flash with the goal
    and executed action history, parses the single exact coordinate action,
    executes it via PyAutoGUI, and loops until completion.
    """
    _require_pyautogui()
    
    api_key = _get_api_key()
    if not api_key:
        msg = "UI-TARS Agent error: No Gemini API Key in config."
        if player:
            player.write_log(msg)
        return msg

    from google import genai
    from google.genai import types as gtypes

    try:
        w, h = pyautogui.size()
    except Exception as e:
        return f"Failed to get screen size: {e}"

    action_history = []
    max_steps = 12
    
    if player:
        player.write_log(f"🤖 UI-TARS Visual Agent Started: '{goal}'")
        if hasattr(player, "write_thought"):
            player.write_thought(f"UI-TARS visual agent initialised for goal: {goal[:60]}")
    print(f"[UI-TARS] Goal: {goal}")

    for step in range(max_steps):
        if player:
            player.write_log(f"UI-TARS Loop: Step {step + 1}/{max_steps}...")
            if hasattr(player, "write_thought"):
                player.write_thought(f"Visual desktop screenshot analysis — step {step + 1} of {max_steps}")

        # 1. Capture screen and compress to memory-mapped JPEG
        try:
            img = pyautogui.screenshot()
            if img.mode != 'RGB':
                img = img.convert('RGB')
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80)
            image_bytes = buf.getvalue()
        except Exception as e:
            err_msg = f"Screenshot capture failed: {e}"
            if player:
                player.write_log(f"⚠️ {err_msg}")
            return err_msg

        # 2. Formulate grounding system prompt
        history_str = "\n".join(f"- Step {i+1}: {act}" for i, act in enumerate(action_history)) if action_history else "No actions performed yet."
        
        prompt = f"""You are a Vision-based Desktop Automation Agent (UI-TARS Mode).
Your goal is to achieve this task: "{goal}"

Current Screen Dimensions: {w}x{h} pixels.

Action History:
{history_str}

Your task:
Analyze the screenshot and the Action History.
If the goal is fully achieved, output exactly: finish("Reason why it is successfully finished")
If not, determine the SINGLE next exact GUI action to perform. You MUST output ONLY the action in one of the following exact formats. Do NOT add any surrounding markdown, explanation, or extra code. Just output the single function call.

Available formats:
- click(x, y)
- double_click(x, y)
- right_click(x, y)
- type("text to type")
- press("key_name")  (e.g., "enter", "backspace", "tab", "esc", "win")
- scroll("up" or "down", amount_integer)
- drag(x1, y1, x2, y2)
- wait(seconds_float)
- finish("explanation")

Coordinates MUST be absolute integer values matching the current {w}x{h} screen resolution.
Keep mouse movements natural and select elements accurately.
"""

        # 3. Query Gemini
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    gtypes.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    prompt,
                ],
            )
            response_text = (response.text or "").strip()
        except Exception as api_err:
            err_msg = f"Gemini API request failed: {api_err}"
            if player:
                player.write_log(f"⚠️ {err_msg}")
            return err_msg

        print(f"[UI-TARS] Step {step + 1} model suggestion: {response_text}")
        if player and hasattr(player, "write_thought"):
            player.write_thought(f"UI-TARS action decoded: {response_text[:80]}")

        # 4. Parse the action
        parsed = None
        
        # Try finish
        m = re.search(r'finish\(\s*["\'](.*?)["\']\s*\)', response_text, re.IGNORECASE)
        if m:
            parsed = {"action": "finish", "reason": m.group(1)}
        else:
            # Try double_click
            m = re.search(r'double_click\(\s*(\d+)\s*,\s*(\d+)\s*\)', response_text, re.IGNORECASE)
            if m:
                parsed = {"action": "double_click", "x": int(m.group(1)), "y": int(m.group(2))}
            else:
                # Try right_click
                m = re.search(r'right_click\(\s*(\d+)\s*,\s*(\d+)\s*\)', response_text, re.IGNORECASE)
                if m:
                    parsed = {"action": "right_click", "x": int(m.group(1)), "y": int(m.group(2))}
                else:
                    # Try click
                    m = re.search(r'click\(\s*(\d+)\s*,\s*(\d+)\s*\)', response_text, re.IGNORECASE)
                    if m:
                        parsed = {"action": "click", "x": int(m.group(1)), "y": int(m.group(2))}
                    else:
                        # Try drag
                        m = re.search(r'drag\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)', response_text, re.IGNORECASE)
                        if m:
                            parsed = {"action": "drag", "x1": int(m.group(1)), "y1": int(m.group(2)), "x2": int(m.group(3)), "y2": int(m.group(4))}
                        else:
                            # Try type
                            m = re.search(r'type\(\s*["\'](.*?)["\']\s*\)', response_text, re.IGNORECASE)
                            if m:
                                parsed = {"action": "type", "text": m.group(1)}
                            else:
                                # Try press
                                m = re.search(r'press\(\s*["\'](.*?)["\']\s*\)', response_text, re.IGNORECASE)
                                if m:
                                    parsed = {"action": "press", "key": m.group(1)}
                                else:
                                    # Try scroll
                                    m = re.search(r'scroll\(\s*["\'](up|down)["\']\s*,\s*(\d+)\s*\)', response_text, re.IGNORECASE)
                                    if m:
                                        parsed = {"action": "scroll", "direction": m.group(1), "amount": int(m.group(2))}
                                    else:
                                        # Try wait
                                        m = re.search(r'wait\(\s*([\d\.]+)\s*\)', response_text, re.IGNORECASE)
                                        if m:
                                            parsed = {"action": "wait", "seconds": float(m.group(1))}

        if not parsed:
            # Fallback parsing for text if it doesn't strictly match the parentheses format
            m = re.search(r'(click|double_click|right_click).*?(\d+)\s*,\s*(\d+)', response_text, re.IGNORECASE)
            if m:
                act_type = m.group(1).lower()
                parsed = {"action": act_type, "x": int(m.group(2)), "y": int(m.group(3))}
            else:
                err_msg = f"Failed to parse model response: '{response_text}'"
                if player:
                    player.write_log(f"⚠️ {err_msg}")
                action_history.append(f"Error parsing model suggestion: '{response_text}'")
                time.sleep(2)
                continue

        # 5. Execute parsed action with failsafe catches
        action_name = parsed["action"]
        action_desc = response_text
        
        try:
            if action_name == "finish":
                success_msg = f"UI-TARS Goal Achieved! Reason: {parsed.get('reason', 'completed')}"
                if player:
                    player.write_log(f"🎉 {success_msg}")
                return success_msg
                
            elif action_name == "click":
                _click(parsed["x"], parsed["y"])
                action_desc = f"click({parsed['x']}, {parsed['y']})"
                
            elif action_name == "double_click":
                _click(parsed["x"], parsed["y"], clicks=2)
                action_desc = f"double_click({parsed['x']}, {parsed['y']})"
                
            elif action_name == "right_click":
                _click(parsed["x"], parsed["y"], button="right")
                action_desc = f"right_click({parsed['x']}, {parsed['y']})"
                
            elif action_name == "type":
                _smart_type(parsed["text"])
                action_desc = f"type('{parsed['text']}')"
                
            elif action_name == "press":
                _press(parsed["key"])
                action_desc = f"press('{parsed['key']}')"
                
            elif action_name == "scroll":
                _scroll(parsed["direction"], parsed["amount"])
                action_desc = f"scroll('{parsed['direction']}', {parsed['amount']})"
                
            elif action_name == "drag":
                _drag(parsed["x1"], parsed["y1"], parsed["x2"], parsed["y2"])
                action_desc = f"drag({parsed['x1']}, {parsed['y1']} to {parsed['x2']}, {parsed['y2']})"
                
            elif action_name == "wait":
                time.sleep(parsed["seconds"])
                action_desc = f"wait({parsed['seconds']}s)"
                
            if player:
                player.write_log(f"GUI: Executed {action_desc}")
            action_history.append(action_desc)
            
            # Buffer sleep to let GUI update
            time.sleep(1.5)
            
        except pyautogui.FailSafeException:
            fail_msg = "UI-TARS Agent halted: PyAutoGUI Failsafe triggered by moving mouse to screen corner."
            if player:
                player.write_log(fail_msg)
            return fail_msg
        except Exception as exec_err:
            err_msg = f"Action execution failed: {exec_err}"
            if player:
                player.write_log(f"⚠️ {err_msg}")
            action_history.append(f"Failed to execute: {action_desc} ({exec_err})")
            time.sleep(2)

    timeout_msg = f"UI-TARS Agent finished: Max step limit ({max_steps}) reached."
    if player:
        player.write_log(timeout_msg)
    return timeout_msg


def computer_control(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Dispatch table for all computer control actions.

    parameters keys (all optional unless noted):
      action        : (required) one of the actions listed below
      text          : text to type or paste
      x, y          : screen coordinates
      button        : 'left' | 'right' (default: left)
      keys          : hotkey string, e.g. 'ctrl+c'
      key           : single key name, e.g. 'enter'
      direction     : 'up' | 'down' | 'left' | 'right'
      amount        : scroll amount (default: 3)
      seconds       : wait duration
      title         : window title fragment for focus_window
      description   : natural-language element description for screen_find/click
      type          : data type for random_data
      field         : memory field name for user_data
      clear_first   : bool, clear field before typing (default: true)
      path          : save path for screenshot (must be inside home dir)

    Actions:
      type          — type text at cursor
      smart_type    — clear field + type (clipboard-backed)
      click         — left click
      double_click  — double left click
      right_click   — right click
      move          — move mouse
      drag          — click-drag between two points
      hotkey        — key combination
      press         — single key
      scroll        — scroll the wheel
      copy          — read clipboard
      paste         — write + paste clipboard
      screenshot    — capture screen (safe path only)
      wait          — sleep N seconds
      clear_field   — select-all + delete
      focus_window  — bring window to foreground
      screen_find   — AI element finder (returns x,y)
      screen_click  — AI element finder + click
      random_data   — generate fake form data
      user_data     — pull real data from memory
    """
    params = parameters or {}
    action = params.get("action", "").lower().strip()

    if not action:
        return "No action specified for computer_control."

    if player:
        player.write_log(f"[Computer] {action}")

    print(f"[ComputerControl] ▶ {action}  {params}")

    try:

        if action == "type":
            return _type(params.get("text", ""))

        if action == "smart_type":
            return _smart_type(
                params.get("text", ""),
                clear_first=params.get("clear_first", True),
            )

        if action in ("click", "left_click"):
            return _click(params.get("x"), params.get("y"), "left", 1)

        if action == "double_click":
            return _click(params.get("x"), params.get("y"), "left", 2)

        if action == "right_click":
            return _click(params.get("x"), params.get("y"), "right", 1)

        if action == "move":
            return _move(int(params.get("x", 0)), int(params.get("y", 0)))

        if action == "drag":
            return _drag(
                int(params.get("x1", 0)), int(params.get("y1", 0)),
                int(params.get("x2", 0)), int(params.get("y2", 0)),
            )

        if action == "hotkey":
            raw  = params.get("keys", "")
            keys = [k.strip() for k in raw.split("+")] if isinstance(raw, str) else raw
            return _hotkey(*keys)

        if action == "press":
            return _press(params.get("key", "enter"))

        if action == "scroll":
            return _scroll(
                direction=params.get("direction", "down"),
                amount=int(params.get("amount", 3)),
            )

        if action == "copy":
            return _clipboard_get()

        if action == "paste":
            return _clipboard_paste(params.get("text", ""))

        if action == "screenshot":
            return _screenshot(params.get("path"))

        if action == "screen_find":
            coords = _screen_find(params.get("description", ""))
            return f"{coords[0]},{coords[1]}" if coords else "NOT_FOUND"

        if action == "screen_click":
            desc   = params.get("description", "")
            coords = _screen_find(desc)
            if coords:
                time.sleep(0.2)
                _click(x=coords[0], y=coords[1])
                return f"Clicked '{desc}' at {coords}"
            return f"Element not found on screen: '{desc}'"

        if action == "wait":
            secs = float(params.get("seconds", 1.0))
            secs = min(secs, 30.0)
            time.sleep(secs)
            return f"Waited {secs}s"

        if action == "clear_field":
            return _clear_field()

        if action == "focus_window":
            return _focus_window(params.get("title", ""))

        if action == "random_data":
            dt     = params.get("type", "name")
            result = _random_data(dt)
            print(f"[ComputerControl] 🎲 random {dt} → {result}")
            return result

        if action == "user_data":
            field   = params.get("field", "name")
            profile = _user_profile()
            value   = profile.get(field, "")
            if not value:
                value = _random_data(field)
                print(f"[ComputerControl] ⚠️ No '{field}' in memory, using random: {value}")
            return value

        if action == "ui_tars_agent":
            goal = params.get("goal", params.get("text", ""))
            if not goal:
                return "ui_tars_agent: 'goal' or 'text' parameter is required."
            from actions.prime_utils import confirm_dangerous_action
            if not confirm_dangerous_action("UI-TARS Automation Agent Loop", f"Goal: {goal}", player):
                return "UI-TARS agent execution aborted by user confirmation reject."
            return _execute_ui_tars_agent(goal, player)

        return f"Unknown action: '{action}'"

    except Exception as e:
        print(f"[ComputerControl] ❌ {action}: {e}")
        return f"computer_control '{action}' failed: {e}"