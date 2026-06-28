import time
from pathlib import Path
from typing import Optional, Any
from google import genai

VAULT_DIR = Path.home() / "Documents" / "SecondBrain"
NOTES_DIR = VAULT_DIR / "00 Notes"

def save_voice_note(content: str, player: Optional[Any] = None) -> str:
    """Transcribes, structures, and saves a voice note to the SecondBrain vault."""
    if not content or content.isspace():
        return "Note content is empty, sir."
        
    try:
        NOTES_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"Failed to create notes folder: {e}"

    # Generate AI Title
    title = "Voice Note"
    try:
        from main import _get_api_key
        client = genai.Client(api_key=_get_api_key())
        
        prompt = (
            f"Given the following transcription of a voice note, generate a short, "
            f"descriptive title for it (maximum 4 words, clean English). "
            f"Return ONLY the title itself without any quotes or extra text.\n\n"
            f"Transcription:\n{content}"
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        title = response.text.strip().replace('"', '').replace("'", "")
        # Clean up illegal path characters
        for char in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>']:
            title = title.replace(char, '')
    except Exception as e:
        print(f"[VoiceNotes] AI Title generation failed: {e}")

    timestamp = time.strftime("%Y-%m-%d-%H-%M")
    filename = f"{timestamp}-{title.lower().replace(' ', '_')}.md"
    filepath = NOTES_DIR / filename

    formatted_time = time.strftime("%Y-%m-%d %I:%M %p")
    note_content = (
        f"# {title}\n"
        f"Date: {formatted_time}\n"
        f"Type: Voice Note\n"
        f"---\n\n"
        f"{content.strip()}\n"
    )

    try:
        filepath.write_text(note_content, encoding="utf-8")
        msg = f"Note saved, bhai! Saved as '{title}' in your Second Brain notes."
        if player and hasattr(player, "write_log"):
            player.write_log(f"🧠 SECONDBRAIN: Note saved successfully: {filename}")
        if player and hasattr(player, "_win") and hasattr(player._win, "ip_ray") and player._win.ip_ray:
            player._win.ip_ray.speak(f"Note saved, bhai! Title is: {title}")
        return msg
    except Exception as e:
        return f"Failed to write note file: {e}"

def voice_notes(parameters: dict, player=None) -> str:
    """Dispatcher for voice notes action."""
    content = parameters.get("content", "")
    return save_voice_note(content, player)
