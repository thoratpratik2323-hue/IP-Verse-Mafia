"""
actions/linkedin_agent.py -- Personalized LinkedIn Connection Assistant.
"""
import webbrowser
from google import genai
import os

def generate_invite_note(name: str, bio: str, context: str | None = None) -> str:
    """Generates a personalized, under 300 character invitation note for LinkedIn."""
    prompt = (
        f"Create a professional, highly personalized LinkedIn connection request note for a person named {name}. "
        f"Their headline/bio is: '{bio}'. "
    )
    if context:
        prompt += f"Specific context for connecting: '{context}'. "
    prompt += (
        "Strict Constraint: The note MUST be under 300 characters (LinkedIn's limit) and feel completely natural and human, "
        "written in first person. Do not include placeholders like [My Name] or [Your Name]. Just output the exact invite text."
    )
    
    try:
        # Check if api key is present, otherwise fallback
        if not os.getenv("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY not set")
            
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        note = response.text.strip()
        # Clean quotes
        if note.startswith('"') and note.endswith('"'):
            note = note[1:-1]
        # Ensure it fits
        if len(note) > 300:
            note = note[:297] + "..."
        return note
    except Exception:
        # Fallback note
        return f"Hi {name}, saw your profile and work in {bio[:40]}. Would love to connect and keep in touch!"

def linkedin_agent(
    action: str = "connect",
    profile_url: str | None = None,
    name: str | None = None,
    bio: str | None = None,
    context: str | None = None
) -> str:
    """Personalized LinkedIn connection automation helper."""
    if action == "generate_note":
        if not name or not bio:
            return "Bhai, note generate karne ke liye 'name' aur 'bio' parameters hona zaroori hai!"
        note = generate_invite_note(name, bio, context)
        return (
            f"📝 **Personalized LinkedIn Invite Note for {name} ({len(note)}/300 chars):**\n\n"
            f"\"{note}\""
        )
        
    if action == "connect":
        if not profile_url:
            return "Bhai, connect karne ke liye 'profile_url' parameter hona zaroori hai!"
            
        # Open in default browser
        try:
            webbrowser.open(profile_url)
            note_msg = ""
            if name and bio:
                note = generate_invite_note(name, bio, context)
                note_msg = (
                    f"\n\nHere is a personalized invite note to use when clicking Connect:\n"
                    f"👉 *\"{note}\"*"
                )
            return (
                f"🚀 [LinkedIn Agent] Opened profile in browser: {profile_url}{note_msg}\n"
                f"Please click 'Connect' on the browser page to complete the connection!"
            )
        except Exception as e:
            return f"❌ [LinkedIn Agent] Failed to open browser: {e}"
            
    return "Unknown action. Supported actions are: 'connect', 'generate_note'."
