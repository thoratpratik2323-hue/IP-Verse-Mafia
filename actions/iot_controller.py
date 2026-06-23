import os

# Initial IoT state representing smart grid integration
iot_state = {
    "study_lights": {"enabled": True, "brightness": 80, "color": "#00f2ff"},
    "ambient_shield": {"enabled": False, "color": "#8b5cf6"},
    "secure_gate": {"enabled": True}
}

def get_iot_state():
    """Retrieve the current state of all connected smart home/IoT devices."""
    return iot_state

def toggle_iot(device: str) -> dict:
    """Toggle the enabled status of a specific IoT device and generate a corresponding verbal confirmation."""
    global iot_state
    if device in iot_state:
        iot_state[device]["enabled"] = not iot_state[device]["enabled"]
        state_str = "activated" if iot_state[device]["enabled"] else "deactivated"
        
        if device == "study_lights":
            reply = f"Initiating smart grid sync. Study lights {state_str}, Sir."
        elif device == "ambient_shield":
            reply = f"Ambient glow shield {state_str}, Sir."
        elif device == "secure_gate":
            reply = f"Security gate bypass {state_str}, Sir."
        else:
            reply = f"IoT device sync complete."
            
        audio_url = None
        # Try generating speech using the edge-tts helper
        try:
            from actions.edge_tts_helper import generate_speech
            import time
            t_id = int(time.time() * 1000)
            filename = f"voice_{t_id}.mp3"
            
            static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
            os.makedirs(static_dir, exist_ok=True)
            filepath = os.path.join(static_dir, filename)
            
            if generate_speech(reply, "en-GB-RyanNeural", filepath):
                audio_url = f"/static/{filename}"
        except Exception as e:
            print(f"[IoT SPEECH ERR] {e}")
            
        return {
            "status": "ok",
            "state": iot_state,
            "reply": reply,
            "audioUrl": audio_url
        }
    return {"status": "error", "message": f"Unknown device: {device}"}
