import ctypes
import ctypes.wintypes
import logging

# Windows APIs
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

SW_HIDE = 0
SW_SHOW = 5
GWL_EXSTYLE = -20
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_APPWINDOW = 0x00040000

# Cache HWNDs to restore them later
_cached_tray_hwnds = []

def hide_windows_taskbar():
    """Find and hide all Windows taskbars (primary and secondary)."""
    global _cached_tray_hwnds
    _cached_tray_hwnds.clear()
    
    # Hide primary taskbar
    hwnd_primary = user32.FindWindowW("Shell_TrayWnd", None)
    if hwnd_primary:
        user32.ShowWindow(hwnd_primary, SW_HIDE)
        _cached_tray_hwnds.append(hwnd_primary)
        
    # Hide secondary taskbars (multi-monitor)
    def enum_windows_callback(hwnd, lParam):
        class_name = ctypes.create_unicode_buffer(257)
        user32.GetClassNameW(hwnd, class_name, 256)
        if class_name.value == "Shell_SecondaryTrayWnd":
            user32.ShowWindow(hwnd, SW_HIDE)
            _cached_tray_hwnds.append(hwnd)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
    user32.EnumWindows(WNDENUMPROC(enum_windows_callback), 0)
    
    # Hide Windows Start button (often needed in older Windows 10/7 builds, less so on Win 11 but doesn't hurt)
    hwnd_start = user32.FindWindowW("Button", "Start")
    if hwnd_start:
        user32.ShowWindow(hwnd_start, SW_HIDE)
        _cached_tray_hwnds.append(hwnd_start)
        
    logging.info(f"OS Shell: Hid {len(_cached_tray_hwnds)} taskbar/shell HWNDs.")

def show_windows_taskbar():
    """Restore all Windows taskbars and shell elements hidden by hide_windows_taskbar()."""
    global _cached_tray_hwnds
    for hwnd in _cached_tray_hwnds:
        try:
            if user32.IsWindow(hwnd):
                user32.ShowWindow(hwnd, SW_SHOW)
        except Exception as e:
            logging.error(f"Failed to restore HWND {hwnd}: {e}")
            
    # Fallback to make sure primary is shown anyway
    hwnd_primary = user32.FindWindowW("Shell_TrayWnd", None)
    if hwnd_primary:
        user32.ShowWindow(hwnd_primary, SW_SHOW)
        
    hwnd_secondary = user32.FindWindowW("Shell_SecondaryTrayWnd", None)
    if hwnd_secondary:
        user32.ShowWindow(hwnd_secondary, SW_SHOW)

    hwnd_start = user32.FindWindowW("Button", "Start")
    if hwnd_start:
        user32.ShowWindow(hwnd_start, SW_SHOW)
        
    logging.info("OS Shell: Windows taskbar/shell restored.")

def make_window_transparent_to_input(hwnd):
    """Make a window click-through (useful for transparent overlays)."""
    current_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    # WS_EX_TRANSPARENT (0x20) makes it click-through
    # WS_EX_LAYERED (0x80000) is required for transparent window behavior
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, current_style | 0x20 | 0x80000)

def set_window_always_at_bottom(hwnd):
    """Set window below all other windows (perfect for a desktop background)."""
    # HWND_BOTTOM = 1
    # SWP_NOSIZE = 1, SWP_NOMOVE = 2, SWP_NOACTIVATE = 16
    user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 1 | 2 | 16)
