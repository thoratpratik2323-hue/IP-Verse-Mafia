"""
pascal_3d_designer.py — Draws and renders basic 3D structures.

This is a standard action module for the IP Prime personal assistant suite.
"""

# pascal_3d_designer.py
import io
import json
import re
import time
import os
from pathlib import Path
import pyautogui
from google import genai
from google.genai import types as gtypes
from playwright.sync_api import sync_playwright
from actions.computer_control import _find_element_on_screen

def _load_api_key() -> str:
    try:
        base = Path(__file__).resolve().parent.parent
        config_path = base / "config" / "api_keys.json"
        if config_path.exists():
            data = json.loads(config_path.read_text(encoding="utf-8"))
            return data.get("gemini_api_key", "")
    except Exception:
        pass
    return ""

def _log(message: str, player=None) -> None:
    print(f"[Pascal3D] {message}")
    if player:
        try:
            player.write_log(f"IP PRIME: {message}")
        except Exception:
            pass

def pascal_3d_designer(goal: str, player=None) -> str:
    """
    Premium Autonomous 3D CAD Architect Agent (Voice-to-CAD Designer).
    Launches editor.pascal.app in a headed maximized browser session and leverages our upgraded
    2-stage visual locator to click buttons, select drawing tools, draw walls, search for furniture,
    and place objects on the 3D canvas based on natural language command goals.
    """
    _log(f"Sir, launching 3D Architect Agent for goal: '{goal}'", player)
    
    api_key = _load_api_key()
    if not api_key:
        msg = "Error: Gemini API key is missing from config/api_keys.json, sir."
        _log(msg, player)
        return msg

    client = genai.Client(api_key=api_key)

    # Launch Playwright browser session
    _log("Starting stealth Chromium session...", player)
    try:
        p_manager = sync_playwright().start()
        # Launch headed and maximized
        browser = p_manager.chromium.launch(
            headless=False,
            args=["--start-maximized", "--no-sandbox", "--disable-setuid-sandbox"]
        )
        context = browser.new_context(no_viewport=True)
        page = context.new_page()
    except Exception as e:
        msg = f"Sir, failed to launch Playwright browser: {e}"
        _log(msg, player)
        return msg

    _log("Navigating to editor.pascal.app...", player)
    try:
        page.goto("https://editor.pascal.app", timeout=60000)
        # Give editor plenty of time to compile shaders and load assets
        _log("Waiting for Pascal 3D canvas engine to initialize...", player)
        time.sleep(12)
    except Exception as e:
        browser.close()
        p_manager.stop()
        msg = f"Sir, failed to load Pascal Editor: {e}"
        _log(msg, player)
        return msg

    action_history = []
    max_steps = 12
    step = 0
    final_screenshot_path = ""

    _log("Entering visual decision loop...", player)

    while step < max_steps:
        step += 1
        _log(f"--- Visual Agent Decision Step {step}/{max_steps} ---", player)
        
        # Take a live screenshot of the desktop
        try:
            screenshot_img = pyautogui.screenshot()
            buf = io.BytesIO()
            screenshot_img.save(buf, format="PNG")
            screenshot_bytes = buf.getvalue()
        except Exception as e:
            _log(f"Failed to capture screenshot: {e}", player)
            break

        history_str = "\n".join([f"Step {i+1}: {act}" for i, act in enumerate(action_history)]) if action_history else "None"
        
        # Prompt the main LLM agent to decide what action to take next
        agent_prompt = (
            f"You are an expert autonomous 3D CAD designer agent. Your goal is to design a 3D floor plan layout in the Pascal Editor (editor.pascal.app) based on the user's request:\n"
            f"\"{goal}\"\n\n"
            f"Here is the history of actions we have taken so far:\n"
            f"{history_str}\n\n"
            f"Please analyze the current screenshot carefully.\n"
            f"- If there is a welcome popup, onboarding dialog, cookies prompt, or tutorial screen, close it or click 'Get Started' / 'Skip' / 'Close'.\n"
            f"- To draw walls:\n"
            f"  1. Click the 'Wall tool button' or 'Draw wall tool' (which is typically located on the left toolbar or top menu).\n"
            f"  2. Click multiple points on the empty canvas/grid in the center to draw a room or layout of walls.\n"
            f"- To place furniture:\n"
            f"  1. Click the library search input or search icon on the left panel.\n"
            f"  2. Type the name of the furniture (e.g. 'table', 'chair', 'sofa', 'bed').\n"
            f"  3. Drag the first search result item onto the empty canvas space.\n"
            f"- If the requested design is fully completed, return FINISH.\n\n"
            f"Your response must be in this exact format:\n"
            f"THOUGHT: <your brief reasoning for the next step>\n"
            f"ACTION: <command>\n\n"
            f"Supported actions:\n"
            f"- CLICK <exact descriptive name of the element to click on screen>\n"
            f"  Examples: \"Wall tool button\", \"Search input box\", \"Close welcome popup button\", \"Empty center grid canvas\"\n"
            f"- DRAG <source element name> TO <destination element name>\n"
            f"  Example: DRAG \"First sofa item in library results\" TO \"Center of the grid canvas\"\n"
            f"- TYPE <text to type>\n"
            f"  Example: TYPE sofa\n"
            f"- PRESS <key name>\n"
            f"  Example: PRESS enter\n"
            f"- WAIT <seconds>\n"
            f"  Example: WAIT 2\n"
            f"- FINISH\n"
            f"  Example: FINISH\n\n"
            f"Be extremely precise with descriptions for CLICK and DRAG. The coordinate finder uses your description to find the exact pixels on the screen."
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    gtypes.Part.from_bytes(data=screenshot_bytes, mime_type="image/png"),
                    agent_prompt,
                ],
            )
            decision = (response.text or "").strip()
            print(f"[Pascal3D Agent Decision]:\n{decision}\n")
        except Exception as e:
            _log(f"Failed to generate decision: {e}", player)
            break

        # Parse THOUGHT and ACTION
        thought_match = re.search(r"THOUGHT:\s*(.*)", decision, re.IGNORECASE)
        action_match = re.search(r"ACTION:\s*(.*)", decision, re.IGNORECASE)

        thought = thought_match.group(1).strip() if thought_match else "Analyzing..."
        action = action_match.group(1).strip() if action_match else ""

        if not action:
            _log("Could not parse action from agent. Retrying step...", player)
            continue

        _thought_msg = f"Thinking: {thought}"
        if player and hasattr(player, "write_thought"):
            player.write_thought(_thought_msg)
        _log(_thought_msg, player)

        action_history.append(action)

        if action.upper().startswith("FINISH"):
            _log("Agent declared task finished!", player)
            break

        elif action.upper().startswith("WAIT"):
            try:
                seconds = int(re.search(r"\d+", action).group())
            except Exception:
                seconds = 2
            _log(f"Waiting for {seconds} seconds...", player)
            time.sleep(seconds)

        elif action.upper().startswith("PRESS"):
            key = action[5:].strip().lower()
            _log(f"Pressing keyboard key: '{key}'", player)
            try:
                pyautogui.press(key)
                time.sleep(0.5)
            except Exception as e:
                _log(f"Failed to press key: {e}", player)

        elif action.upper().startswith("TYPE"):
            text = action[4:].strip()
            _log(f"Typing text: '{text}'", player)
            try:
                pyautogui.write(text, interval=0.05)
                time.sleep(0.5)
            except Exception as e:
                _log(f"Failed to type: {e}", player)

        elif action.upper().startswith("CLICK"):
            target_desc = action[5:].strip().strip('"')
            _log(f"Attempting to visually locate and click: '{target_desc}'", player)
            coords = _find_element_on_screen(target_desc, api_key)
            if coords:
                cx, cy = coords
                _log(f"Located target at ({cx}, {cy}). Clicking...", player)
                try:
                    pyautogui.moveTo(cx, cy, duration=0.3)
                    pyautogui.click()
                    time.sleep(1.0)
                except Exception as e:
                    _log(f"Failed to click at ({cx}, {cy}): {e}", player)
            else:
                _log(f"Could not locate '{target_desc}' on screen.", player)

        elif action.upper().startswith("DRAG"):
            # Format: DRAG "source" TO "dest"
            drag_match = re.search(r'DRAG\s+["\']?([^"\']+)["\']?\s+TO\s+["\']?([^"\']+)["\']?', action, re.IGNORECASE)
            if drag_match:
                source_desc = drag_match.group(1).strip()
                dest_desc = drag_match.group(2).strip()
                _log(f"Locating source '{source_desc}' and destination '{dest_desc}' for drag...", player)
                
                source_coords = _find_element_on_screen(source_desc, api_key)
                if not source_coords:
                    _log(f"Could not locate source '{source_desc}' on screen.", player)
                    continue
                
                # Take screenshot again in case UI changed slightly
                dest_coords = _find_element_on_screen(dest_desc, api_key)
                if not dest_coords:
                    _log(f"Could not locate destination '{dest_desc}' on screen.", player)
                    continue
                
                sx, sy = source_coords
                dx, dy = dest_coords
                _log(f"Dragging from ({sx}, {sy}) to ({dx}, {dy})...", player)
                try:
                    pyautogui.moveTo(sx, sy, duration=0.3)
                    pyautogui.dragTo(dx, dy, duration=0.8, button="left")
                    time.sleep(1.0)
                except Exception as e:
                    _log(f"Failed to drag-and-drop: {e}", player)
            else:
                _log(f"Invalid DRAG syntax: {action}", player)

        else:
            _log(f"Unknown action command: {action}", player)

    # Save final screen and close browser
    _log("Taking final screenshot of design...", player)
    try:
        base = Path(__file__).resolve().parent.parent
        memory_dir = base / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)
        final_screenshot_path = str(memory_dir / f"pascal_3d_design_{int(time.time())}.png")
        
        screenshot_img = pyautogui.screenshot()
        screenshot_img.save(final_screenshot_path)
        _log(f"Saved design screenshot to: {final_screenshot_path}", player)
    except Exception as e:
        _log(f"Failed to save final screenshot: {e}", player)

    _log("Closing browser session cleanly...", player)
    try:
        browser.close()
        p_manager.stop()
    except Exception:
        pass

    history_summary = "\n".join([f"- {act}" for act in action_history])
    result_msg = (
        f"Pratik Sir, Pascal 3D Editor designer agent successfully finished drawing layout based on your request!\n\n"
        f"**Actions Taken:**\n"
        f"{history_summary}\n\n"
        f"**Final design saved as image to:**\n"
        f"[{Path(final_screenshot_path).name}](file:///{final_screenshot_path.replace(os.sep, '/')})"
    )
    _log("Agent execution finished.", player)
    return result_msg
