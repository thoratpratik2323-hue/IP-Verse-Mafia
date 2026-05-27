from pycaw.pycaw import AudioUtilities, ISimpleAudioVolume

def list_active_audio_sessions() -> str:
    """Lists all active application audio sessions and their volume levels."""
    try:
        sessions = AudioUtilities.GetAllSessions()
        active_sessions = []
        
        for session in sessions:
            if session.Process:
                name = session.Process.name()
                volume_ctrl = session._ctl.QueryInterface(ISimpleAudioVolume)
                vol = int(volume_ctrl.GetMasterVolume() * 100)
                muted = "Muted 🔇" if volume_ctrl.GetMute() else "Active 🔊"
                active_sessions.append(f"- **{name}**: {vol}% volume ({muted})")
                
        if not active_sessions:
            return "### 🔊 Application Audio Mixer\nNo active application audio sessions detected."
            
        return "### 🔊 Active Application Audio Sessions\n" + "\n".join(active_sessions)
    except Exception as e:
        return f"Error listing audio sessions: {e}"

def set_application_volume(app_name: str, volume_level: int) -> str:
    """Sets the volume level (0-100) of a specific application process."""
    try:
        vol_float = max(0.0, min(1.0, float(volume_level) / 100.0))
        sessions = AudioUtilities.GetAllSessions()
        found = False
        
        app_name_clean = app_name.lower().strip()
        if not app_name_clean.endswith(".exe") and app_name_clean not in ["system sounds", "idle"]:
            # Add .exe fallback check
            app_exe = f"{app_name_clean}.exe"
        else:
            app_exe = app_name_clean
            
        for session in sessions:
            if session.Process:
                p_name = session.Process.name().lower()
                if app_name_clean in p_name or app_exe in p_name:
                    volume_ctrl = session._ctl.QueryInterface(ISimpleAudioVolume)
                    volume_ctrl.SetMasterVolume(vol_float, None)
                    found = True
                    
        if found:
            return f"Successfully set volume of **{app_name}** to **{volume_level}%**."
        else:
            return f"Application process matching '{app_name}' was not found among active audio sessions."
    except Exception as e:
        return f"Error setting volume for {app_name}: {e}"

def mute_application(app_name: str, mute_state: bool) -> str:
    """Mutes or unmutes a specific application process."""
    try:
        sessions = AudioUtilities.GetAllSessions()
        found = False
        
        app_name_clean = app_name.lower().strip()
        if not app_name_clean.endswith(".exe"):
            app_exe = f"{app_name_clean}.exe"
        else:
            app_exe = app_name_clean
            
        for session in sessions:
            if session.Process:
                p_name = session.Process.name().lower()
                if app_name_clean in p_name or app_exe in p_name:
                    volume_ctrl = session._ctl.QueryInterface(ISimpleAudioVolume)
                    volume_ctrl.SetMute(1 if mute_state else 0, None)
                    found = True
                    
        state_str = "MUTED 🔇" if mute_state else "UNMUTED 🔊"
        if found:
            return f"Successfully **{state_str}** application **{app_name}**."
        else:
            return f"Application process matching '{app_name}' was not found among active audio sessions."
    except Exception as e:
        return f"Error setting mute state for {app_name}: {e}"
