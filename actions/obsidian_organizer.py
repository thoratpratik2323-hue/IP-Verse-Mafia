import logging
import os
import re
from pathlib import Path
from datetime import datetime
from google import genai
from config import get_config

DEFAULT_VAULT = Path.home() / "Documents" / "SecondBrain"

def obsidian_action(parameters: dict, player=None, session_memory=None) -> str:
    """
    Obsidian Vault Sync & Auto-Organizer tool router.
    Supported actions: 'index', 'categorize', 'summarize'
    """
    act = parameters.get("action", "index").lower().strip()
    vault_str = parameters.get("vault_path", "").strip()
    
    if vault_str:
        vault_path = Path(vault_str)
    else:
        vault_path = DEFAULT_VAULT

    # Ensure the vault directory exists
    try:
        vault_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"Could not open or create Obsidian vault path: {vault_path}. Error: {e}"

    if act == "index":
        return run_index(vault_path)
    elif act == "categorize":
        return run_categorize(vault_path, parameters)
    elif act == "summarize":
        return run_summarize(vault_path, parameters)
    else:
        return f"Unknown Obsidian action: '{act}', sir."

def run_index(vault_path: Path) -> str:
    """Scan the vault and return a list of markdown notes and their meta-information."""
    md_files = list(vault_path.glob("**/*.md"))
    if not md_files:
        return f"No markdown notes found in Obsidian vault at '{vault_path}', sir."

    summary_lines = [f"Obsidian Vault Index for '{vault_path.name}':", f"Found {len(md_files)} markdown note(s)."]
    for idx, f in enumerate(md_files[:30]):  # Limit to 30 to avoid blowing context limit
        rel_path = f.relative_to(vault_path)
        size = f.stat().st_size
        # Extract headers and tags
        content = ""
        try:
            content = f.read_text(encoding="utf-8")
        except Exception as _exc:  # noqa: BLE001
            logging.debug("[%s] Suppressed: %s", __name__, _exc)
            
        tags = re.findall(r"#\w+", content)
        headers = [line.strip("# ") for line in content.splitlines() if line.startswith("# ")]
        
        tag_str = f", Tags: {', '.join(tags)}" if tags else ""
        hdr_str = f", Headers: {', '.join(headers[:3])}" if headers else ""
        summary_lines.append(f"{idx+1}. [[{f.stem}]] (Path: {rel_path}, Size: {size} bytes{tag_str}{hdr_str})")

    if len(md_files) > 30:
        summary_lines.append(f"... and {len(md_files) - 30} more notes.")

    return "\n".join(summary_lines)

def run_categorize(vault_path: Path, parameters: dict) -> str:
    """Auto-categorize notes into folders based on tags or simple heuristic search."""
    note_name = parameters.get("note_name", "").strip()
    if not note_name:
        return "Please specify the 'note_name' to categorize, sir."

    # Look for the file in the vault
    target_file = None
    note_stem = Path(note_name).stem
    for f in vault_path.glob("**/*.md"):
        if f.stem.lower() == note_stem.lower():
            target_file = f
            break

    if not target_file:
        return f"Could not find note '{note_name}' in the vault, sir."

    try:
        content = target_file.read_text(encoding="utf-8")
    except Exception as e:
        return f"Failed to read note '{note_name}': {e}"

    # Determine category based on tags or manual override
    category = parameters.get("category", "").strip().capitalize()
    if not category:
        # Simple rule-based tag scanner
        tags = [t.lower() for t in re.findall(r"#\w+", content)]
        if any(t in tags for t in ["#work", "#job", "#office", "#meeting"]):
            category = "Work"
        elif any(t in tags for t in ["#personal", "#diary", "#journal", "#todo"]):
            category = "Personal"
        elif any(t in tags for t in ["#research", "#study", "#paper", "#learn"]):
            category = "Research"
        elif any(t in tags for t in ["#project", "#dev", "#code", "#sat"]):
            category = "Projects"
        else:
            category = "Inbox"

    dest_dir = vault_path / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / target_file.name

    if target_file == dest_file:
        return f"Note [[{target_file.stem}]] is already in category folder '{category}', sir."

    try:
        # Move the note
        target_file.rename(dest_file)
        return f"Successfully organized [[{dest_file.stem}]] into folder '{category}', sir."
    except Exception as e:
        return f"Failed to move note [[{target_file.stem}]] to '{category}': {e}"

def run_summarize(vault_path: Path, parameters: dict) -> str:
    """Generate a daily or weekly summary of vault content or git activities."""
    note_name = parameters.get("note_name", "").strip()
    
    # If a specific note name is specified, summarize that note
    if note_name:
        target_file = None
        note_stem = Path(note_name).stem
        for f in vault_path.glob("**/*.md"):
            if f.stem.lower() == note_stem.lower():
                target_file = f
                break
        if not target_file:
            return f"Could not find note '{note_name}' to summarize, sir."
            
        try:
            content = target_file.read_text(encoding="utf-8")
        except Exception as e:
            return f"Failed to read note: {e}"
            
        # Run LLM summary
        api_key = get_config().get("gemini_api_key", "")
        if not api_key:
            return "Gemini API key is not configured, sir."
            
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Summarize this note in 3 bullet points, using wiki-links [[note]] where relevant:\n\n{content}"
            )
            summary = response.text.strip()
            return f"Summary of [[{target_file.stem}]]:\n\n{summary}"
        except Exception as e:
            return f"Summarization failed: {e}"

    # Generate a Daily Summary Note of all notes modified today
    today_str = datetime.now().strftime("%Y-%m-%d")
    daily_note_path = vault_path / f"Daily_Summary_{today_str}.md"
    
    md_files = list(vault_path.glob("**/*.md"))
    modified_today = []
    for f in md_files:
        if f.name.startswith("Daily_Summary_"):
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
        if mtime == today_str:
            modified_today.append(f)
            
    if not modified_today:
        return f"No notes modified today ({today_str}) in vault to summarize, sir."

    summary_content = [
        f"# Daily Summary - {today_str}",
        f"Generated automatically by S.A.T.U.R.D.A.Y at {datetime.now().strftime('%H:%M:%S')}.",
        "",
        "## Modified Notes Today:",
        ""
    ]
    
    for f in modified_today:
        summary_content.append(f"- [[{f.stem}]] (Folder: {f.parent.name})")
        
    summary_content_str = "\n".join(summary_content)
    
    try:
        daily_note_path.write_text(summary_content_str, encoding="utf-8")
        return f"Daily summary note [[Daily_Summary_{today_str}]] created successfully with {len(modified_today)} linked notes, sir."
    except Exception as e:
        return f"Failed to write daily summary note: {e}"
