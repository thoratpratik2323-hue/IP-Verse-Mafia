import subprocess

def _run_adb(args: list) -> tuple[int, str, str]:
    """Runs an adb command and returns exit_code, stdout, stderr."""
    try:
        cmd = ["adb"] + args
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def adb_check_device() -> bool:
    """Checks if an Android device is connected and authorized."""
    code, out, err = _run_adb(["devices"])
    if code != 0:
        print("[Telekinesis] ADB not found or failed.")
        return False
        
    lines = out.splitlines()
    for line in lines[1:]:
        if "device" in line and "unauthorized" not in line and "offline" not in line:
            return True
            
    print("[Telekinesis] No authorized Android device connected.")
    return False

def adb_push_file(pc_path: str, phone_path: str = "/sdcard/Download/") -> str:
    """Pushes a file from the PC to the connected Android device."""
    if not adb_check_device():
        return "Failed: No Android device connected."
        
    code, out, err = _run_adb(["push", pc_path, phone_path])
    if code == 0:
        return f"Successfully pushed '{pc_path}' to '{phone_path}'."
    return f"Push failed: {err or out}"

def adb_pull_file(phone_path: str, pc_path: str) -> str:
    """Pulls a file from the connected Android device to the PC."""
    if not adb_check_device():
        return "Failed: No Android device connected."
        
    code, out, err = _run_adb(["pull", phone_path, pc_path])
    if code == 0:
        return f"Successfully pulled '{phone_path}' to '{pc_path}'."
    return f"Pull failed: {err or out}"

def adb_tap_screen(x: int, y: int) -> str:
    """Simulates a tap on the Android device's screen at the specified coordinates."""
    if not adb_check_device():
        return "Failed: No Android device connected."
        
    code, out, err = _run_adb(["shell", "input", "tap", str(x), str(y)])
    if code == 0:
        return f"Tapped screen at ({x}, {y})."
    return f"Tap failed: {err or out}"

def adb_get_battery() -> str:
    """Retrieves the battery telemetry from the Android device."""
    if not adb_check_device():
        return "Failed: No Android device connected."
        
    code, out, err = _run_adb(["shell", "dumpsys", "battery"])
    if code == 0:
        # Extract percentage
        for line in out.splitlines():
            if "level" in line:
                val = line.split(":")[1].strip()
                return f"Mobile Battery is at {val}%"
        return "Battery info extracted but couldn't parse level."
    return f"Battery check failed: {err or out}"

import shutil
_scrcpy_process = None

def adb_start_mirror(player=None) -> str:
    """Launches scrcpy screen mirroring in a background process."""
    global _scrcpy_process
    
    if _scrcpy_process and _scrcpy_process.poll() is None:
        return "Phone mirroring is already active, sir."
        
    scrcpy_path = shutil.which("scrcpy")
    if not scrcpy_path:
        return "scrcpy is not installed or not in system PATH, sir. Please install it to enable screen mirroring."
        
    if not adb_check_device():
        return "Failed: No authorized Android device connected, sir."
        
    try:
        if player:
            player.write_thought("Starting scrcpy mirror stream at 30 FPS...")
        cmd = ["scrcpy", "--max-fps", "30", "--bit-rate", "4M"]
        _scrcpy_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return "Phone screen mirroring started successfully, sir! A new scrcpy window has been opened."
    except Exception as e:
        return f"Error launching scrcpy mirror: {e}, sir."

def adb_stop_mirror(player=None) -> str:
    """Kills the active scrcpy process."""
    global _scrcpy_process
    
    if not _scrcpy_process or _scrcpy_process.poll() is not None:
        return "Mirroring screen active nahi hai, sir."
        
    try:
        _scrcpy_process.terminate()
        _scrcpy_process.wait(timeout=3)
        _scrcpy_process = None
        return "Phone screen mirroring successfully stopped, sir."
    except Exception as e:
        try:
            _scrcpy_process.kill()
            _scrcpy_process = None
            return "Phone mirroring killed successfully, sir."
        except Exception:
            return f"Error stopping mirroring process: {e}, sir."

def adb_install_apk(apk_path: str, player=None) -> str:
    """Installs an APK file from the PC to the device."""
    if not adb_check_device():
        return "Failed: No Android device connected, sir."
        
    if not os.path.exists(apk_path):
        return f"Apk file '{apk_path}' nahi mila, sir."
        
    if player:
        player.write_thought(f"Installing APK: '{Path(apk_path).name}'...")
        
    code, out, err = _run_adb(["install", apk_path])
    if code == 0:
        return f"Apk '{Path(apk_path).name}' successfully installed on your phone, sir!"
    return f"APK installation failed: {err or out}, sir."

def adb_take_screenshot(save_path: str = '', player=None) -> str:
    """Takes a phone screenshot and pulls it to the PC."""
    if not adb_check_device():
        return "Failed: No Android device connected, sir."
        
    dest = save_path
    if not dest:
        # Default destination: Downloads
        dest_dir = Path(r"C:\Users\thora\Downloads")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = str(dest_dir / f"phone_screenshot_{int(time.time())}.png")
        
    if player:
        player.write_thought("Capturing screen on mobile device...")
        
    # Screencap to SDCard
    code, out, err = _run_adb(["shell", "screencap", "-p", "/sdcard/screen.png"])
    if code != 0:
        return f"Screencap failed: {err or out}, sir."
        
    # Pull to PC
    code2, out2, err2 = _run_adb(["pull", "/sdcard/screen.png", dest])
    if code2 == 0:
        # Clean up SDCard
        _run_adb(["shell", "rm", "/sdcard/screen.png"])
        return f"Phone screenshot successfully saved to PC at `{dest}`, sir!"
    return f"Failed to pull screenshot from phone: {err2 or out2}, sir."

def adb_send_text(text: str, player=None) -> str:
    """Types text on the Android device."""
    if not adb_check_device():
        return "Failed: No Android device connected, sir."
        
    if not text:
        return "Text to send cannot be empty, sir."
        
    # Escape spaces with %s for adb shell input text compatibility
    escaped_text = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
    code, out, err = _run_adb(["shell", "input", "text", escaped_text])
    if code == 0:
        return f"Successfully typed text '{text}' on your phone, sir."
    return f"Failed to send text: {err or out}, sir."

def adb_home_button(player=None) -> str:
    """Simulates pressing the Home button."""
    if not adb_check_device():
        return "Failed: No Android device connected, sir."
        
    code, out, err = _run_adb(["shell", "input", "keyevent", "3"])
    if code == 0:
        return "Pressed mobile Home button, sir."
    return f"Failed to press Home button: {err or out}, sir."

def adb_back_button(player=None) -> str:
    """Simulates pressing the Back button."""
    if not adb_check_device():
        return "Failed: No Android device connected, sir."
        
    code, out, err = _run_adb(["shell", "input", "keyevent", "4"])
    if code == 0:
        return "Pressed mobile Back button, sir."
    return f"Failed to press Back button: {err or out}, sir."

def adb_volume_up(steps: int = 1, player=None) -> str:
    """Increases device volume by specified steps."""
    if not adb_check_device():
        return "Failed: No Android device connected, sir."
        
    for _ in range(steps):
        code, out, err = _run_adb(["shell", "input", "keyevent", "24"])
        if code != 0:
            return f"Failed to increase volume: {err or out}, sir."
    return f"Increased mobile volume by {steps} steps, sir."

def adb_volume_down(steps: int = 1, player=None) -> str:
    """Decreases device volume by specified steps."""
    if not adb_check_device():
        return "Failed: No Android device connected, sir."
        
    for _ in range(steps):
        code, out, err = _run_adb(["shell", "input", "keyevent", "25"])
        if code != 0:
            return f"Failed to decrease volume: {err or out}, sir."
    return f"Decreased mobile volume by {steps} steps, sir."

def mobile_telekinesis(parameters: dict, player=None) -> str:
    """Dispatcher for premium Mobile Telekinesis actions."""
    action = parameters.get("action", "battery").lower().strip()
    pc_path = parameters.get("pc_path", "")
    phone_path = parameters.get("phone_path", "")
    x = parameters.get("x")
    y = parameters.get("y")
    text = parameters.get("text", "")
    steps = int(parameters.get("steps", 1))
    save_path = parameters.get("save_path", "")
    apk_path = parameters.get("apk_path", "")
    
    if action == "battery":
        return adb_get_battery()
    elif action == "push":
        return adb_push_file(pc_path, phone_path)
    elif action == "pull":
        return adb_pull_file(phone_path, pc_path)
    elif action == "tap":
        try:
            return adb_tap_screen(int(x), int(y))
        except Exception:
            return "Invalid coordinate arguments for tap action, sir."
    elif action == "mirror":
        return adb_start_mirror(player)
    elif action == "stop_mirror":
        return adb_stop_mirror(player)
    elif action == "install":
        return adb_install_apk(apk_path or pc_path, player)
    elif action == "screenshot":
        return adb_take_screenshot(save_path, player)
    elif action == "type":
        return adb_send_text(text, player)
    elif action == "home":
        return adb_home_button(player)
    elif action == "back":
        return adb_back_button(player)
    elif action == "volume_up":
        return adb_volume_up(steps, player)
    elif action == "volume_down":
        return adb_volume_down(steps, player)
    else:
        return f"Unknown action '{action}' for Mobile Telekinesis, sir."

