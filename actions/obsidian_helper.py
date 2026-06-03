"""
obsidian_helper.py — Manages Obsidian vaults, logs markdown pages, and appends task notes.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import json
from pathlib import Path
from actions.semantic_store import _get_gemini_client, index_file, init_db

BASE_DIR = Path(__file__).resolve().parent.parent
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"

def get_obsidian_vault_path() -> str | None:
    try:
        if API_KEYS_PATH.exists():
            with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return cfg.get("obsidian_vault_path")
    except Exception as e:
        print(f"[Obsidian RAG] Error loading config: {e}")
    return None

def index_obsidian_vault() -> str:
    """Walks the configured Obsidian Vault directory and indexes markdown notes semantically."""
    vault_path_str = get_obsidian_vault_path()
    if not vault_path_str:
        return "Error: Obsidian vault path is not configured. Please specify 'obsidian_vault_path' in your settings."
        
    vault_path = Path(vault_path_str).resolve()
    if not vault_path.exists() or not vault_path.is_dir():
        return f"Error: Obsidian vault directory '{vault_path_str}' does not exist or is not a folder."
        
    init_db()
    try:
        client = _get_gemini_client()
    except Exception as e:
        return f"Authentication Error: {e}"
        
    indexed_count = 0
    skipped_count = 0
    total_files = 0
    
    # Ignored folders inside Obsidian (like configuration/trash folders)
    ignored_folders = {".obsidian", ".trash", ".git", "node_modules"}
    
    for root, dirs, files in os.walk(vault_path):
        # Prune ignored folders
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() == ".md":
                total_files += 1
                if index_file(client, file_path):
                    indexed_count += 1
                else:
                    skipped_count += 1
                    
    return f"Obsidian Vault RAG Sync completed. Indexed {indexed_count} new/updated notes, skipped {skipped_count} unchanged notes (Total markdown notes: {total_files})."

def search_obsidian_notes(query: str, limit: int = 5) -> str:
    """Performs semantic search across the indexed notes but narrows/filters specifically for Obsidian files."""
    init_db()
    try:
        client = _get_gemini_client()
        from actions.semantic_store import get_embedding
        query_emb = get_embedding(client, query)
    except Exception as e:
        return f"Error: {e}"
        
    try:
        db = init_db()
        tbl = db.open_table("documents")
        # Native LanceDB semantic vector search
        rows = tbl.search(query_emb).limit(limit * 3).to_list()
    except Exception as e:
        return f"No notes indexed in Obsidian Vault or LanceDB error: {e}. Please run index_obsidian_vault first."
        
    if not rows:
        return "No notes indexed in Obsidian Vault. Please run index_obsidian_vault first."
        
    vault_path_str = get_obsidian_vault_path()
    
    results = []
    for row in rows:
        path = row.get("file_path", "")
        chunk = row.get("content_chunk", "")
        dist = row.get("_distance", 0.0)
        similarity = 1.0 / (1.0 + dist)
        
        is_obsidian = False
        if vault_path_str:
            is_obsidian = vault_path_str.lower() in path.lower() or os.path.isabs(path)
        else:
            is_obsidian = path.endswith(".md")
            
        if not is_obsidian:
            continue
            
        results.append((path, chunk, similarity))
            
    if not results:
        return "No matches found in your Obsidian notes."
        
    results.sort(key=lambda x: x[2], reverse=True)
    top_matches = results[:limit]
    
    formatted = [f"### 🔍 Obsidian Semantic Notes for: '{query}'\n"]
    for i, (path, chunk, score) in enumerate(top_matches, 1):
        preview = chunk.strip().replace("\n", " \n> ")
        path_url = path.replace('\\', '/')
        formatted.append(
            f"**{i}. [{Path(path).name}](file:///{path_url})** *(Similarity: {score:.3f})*\n"
            f"> {preview}\n"
        )
    return "\n".join(formatted)

def obsidian_rag_query(query: str, player=None) -> str:
    """
    Performs a semantic search on Obsidian notes, extracts the top matches,
    and feeds them as context into Gemini to compile a highly-polished, Hinglish RAG answer.
    """
    # Retrieve semantic matches
    matches_text = search_obsidian_notes(query, limit=4)
    if "No notes indexed" in matches_text or "No matches found" in matches_text or "Error" in matches_text:
        return matches_text
        
    try:
        from actions.prime_utils import UnifiedModelClient
        client = UnifiedModelClient(category="coding")
        
        prompt = f"""You are the Premium Second Brain RAG Cognitive Engine for IP Prime.
You have been provided with relevant context retrieved from Pratik Sir's personal Obsidian notes, along with his query.

Pratik Sir's Query: "{query}"

Retrieved Context from Notes:
\"\"\"
{matches_text}
\"\"\"

Please generate a comprehensive, highly-polished response to Pratik Sir.
Your response should:
1. Synthesize the facts directly from the retrieved notes to answer his query.
2. Maintain a direct, friendly, and premium Hinglish tone where appropriate.
3. If the retrieved notes do not contain the answer, state that honestly but provide helpful general guidance based on what *is* in his notes.

Use standard clean markdown. Keep it high-value and concise (150-300 words)."""

        response = client.models.generate_content(model=None, contents=prompt)
        answer = response.text.strip()
        
        return (
            f"### 🧠 [IP PRIME RAG] Second Brain Synthesis\n"
            f"{answer}\n\n"
            f"*(Context retrieved from your personal Obsidian notes deck, sir)*"
        )
    except Exception as e:
        return (
            f"### [IP PRIME] Semantic Retrieval Fallback\n"
            f"*(RAG generation failed: {e})*\n\n"
            f"{matches_text}"
        )


def auto_organize_notes(player=None) -> str:
    """
    Scans the Obsidian Vault for new or modified notes, extracts topics using Gemini,
    and appends semantic double-bracket [[Topic]] links to them.
    """
    import re
    import time
    
    vault_path_str = get_obsidian_vault_path()
    if not vault_path_str:
        return "Error: Obsidian vault path is not configured, sir. Please set 'obsidian_vault_path' in settings."
        
    vault_path = Path(vault_path_str).resolve()
    if not vault_path.exists() or not vault_path.is_dir():
        return f"Error: Obsidian vault directory '{vault_path_str}' does not exist or is not a folder."
        
    # Ensure cache folder & file
    cache_dir = BASE_DIR / "data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "obsidian_organizer_cache.json"
    
    cache = {}
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}
            
    try:
        from actions.prime_utils import UnifiedModelClient
        client = UnifiedModelClient(category="coding")
    except Exception as e:
        return f"Authentication Error: {e}"
        
    scanned_count = 0
    updated_count = 0
    ignored_folders = {".obsidian", ".trash", ".git", "node_modules", "Daily Digests"}
    
    for root, dirs, files in os.walk(vault_path):
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        for file in files:
            if not file.endswith(".md"):
                continue
                
            file_path = Path(root) / file
            scanned_count += 1
            
            mtime = os.path.getmtime(file_path)
            cached_mtime = cache.get(str(file_path), 0.0)
            
            if mtime > cached_mtime:
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    if not content.strip():
                        continue
                        
                    prompt = f"""You are the Advanced Second Brain Note Auto-Organizer.
Analyze the following markdown note.
1. Extract 3 to 5 core topics or key phrases from the content.
2. For each topic, check if it is already present in the note as a double-bracket link, i.e., `[[Topic]]` (case-insensitive).
3. Generate a related links list for the topics that are NOT already linked in the file.
Return a strict JSON response:
{{
  "topics": ["Topic1", "Topic2"],
  "needs_update": true/false,
  "new_links_markdown": "\\n\\n### Related Topics\\n- [[Topic1]]\\n- [[Topic2]]"
}}
Return only the raw JSON. No markdown code fences, no comments."""

                    response = client.models.generate_content(
                        model=None,
                        contents=prompt + f"\n\nNote Content:\n\"\"\"\n{content}\n\"\"\""
                    )
                    
                    res_text = response.text.strip()
                    res_text = re.sub(r"```json\s*", "", res_text)
                    res_text = re.sub(r"```\s*", "", res_text)
                    res_text = res_text.strip()
                    
                    json_match = re.search(r'\{.*?\}', res_text, re.DOTALL)
                    if json_match:
                        res_text = json_match.group(0)
                        
                    data = json.loads(res_text)
                    if data.get("needs_update") and data.get("new_links_markdown"):
                        links_block = data["new_links_markdown"]
                        # Append to note
                        updated_content = content.rstrip() + "\n" + links_block.strip() + "\n"
                        file_path.write_text(updated_content, encoding="utf-8")
                        updated_count += 1
                        
                    # Update cache with post-write mtime to avoid infinite loops
                    cache[str(file_path)] = os.path.getmtime(file_path)
                except Exception as e:
                    print(f"[ObsidianOrganizer] Error processing {file}: {e}")
                    
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4)
        
    return f"Successfully auto-organized Obsidian notes! Scanned {scanned_count} notes, semantically updated {updated_count} notes with new bracket links, sir."


def generate_vault_digest(digest_type: str = "daily", player=None) -> str:
    """
    Generates a daily or weekly markdown productivity and task digest, saving it
    directly into the 'Daily Digests/' directory in the Obsidian Vault.
    """
    from datetime import datetime
    
    vault_path_str = get_obsidian_vault_path()
    if not vault_path_str:
        return "Error: Obsidian vault path is not configured, sir. Please set 'obsidian_vault_path' in settings."
        
    vault_path = Path(vault_path_str).resolve()
    if not vault_path.exists() or not vault_path.is_dir():
        return f"Error: Obsidian vault directory '{vault_path_str}' does not exist or is not a folder."
        
    # Ensure Digests directory exists
    digests_dir = vault_path / "Daily Digests"
    digests_dir.mkdir(parents=True, exist_ok=True)
    
    # Read tasks data
    tasks_file = Path.home() / ".ipprime" / "tasks.json"
    tasks_list = []
    if tasks_file.exists():
        try:
            with open(tasks_file, "r", encoding="utf-8") as f:
                tasks_data = json.load(f)
                tasks_list = tasks_data.get("tasks", [])
        except Exception:
            pass
            
    completed_tasks = [t for t in tasks_list if t.get("status") == "done"]
    pending_tasks = [t for t in tasks_list if t.get("status") == "pending"]
    
    # Read screen time data
    screen_time_file = BASE_DIR / "data" / "screen_time.json"
    screen_time_data = {}
    if screen_time_file.exists():
        try:
            with open(screen_time_file, "r", encoding="utf-8") as f:
                screen_time_data = json.load(f)
        except Exception:
            pass
            
    # Format screen time summary
    apps_usage = screen_time_data.get("apps", {})
    screen_report = []
    for app, seconds in apps_usage.items():
        screen_report.append(f"- {app.upper()}: {seconds // 60} minutes")
    screen_report_str = "\n".join(screen_report) if screen_report else "No screen time logged today, sir."
    
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Create compilation details
    completed_str = "\n".join([f"- [x] {t.get('title')} ({t.get('priority', 'medium')})" for t in completed_tasks]) or "No completed tasks, sir."
    pending_str = "\n".join([f"- [ ] {t.get('title')} (Priority: {t.get('priority', 'medium')}, Deadline: {t.get('deadline', 'none')})" for t in pending_tasks]) or "No pending tasks, sir."
    
    # Ask Gemini to compile a premium digest
    try:
        from actions.prime_utils import UnifiedModelClient
        client = UnifiedModelClient(category="coding")
        
        prompt = f"""You are the Premium Second Brain Digest Compiler for IP Prime.
Compile a highly polished, professional {digest_type} productivity and activity digest for Pratik Sir.
Use a direct, helpful, and premium Hinglish tone where appropriate.

Use the following input details:
Date: {today_str}
Digest Type: {digest_type.capitalize()}

Completed Tasks:
{completed_str}

Pending Tasks:
{pending_str}

Screen Time App Durations:
{screen_report_str}

The digest must be formatted as beautiful markdown. Include:
1. An executive summary/performance rating.
2. Sabash message for completed milestones.
3. Priority reminders for pending work.
4. App screen usage breakdown and advice.
Use clean markdown headers, bolding, and custom lists."""

        response = client.models.generate_content(
            model=None,
            contents=prompt
        )
        digest_content = response.text.strip()
    except Exception as e:
        digest_content = f"""# {digest_type.capitalize()} Productivity Digest - {today_str}

Generated with fallback due to API error: {e}

## Completed Tasks
{completed_str}

## Pending Tasks
{pending_str}

## Screen Time Info
{screen_report_str}
"""
    
    # Save the file to Daily Digests/ folder in Obsidian Vault
    filename = f"Digest-{today_str}.md" if digest_type == "daily" else f"Weekly-Digest-{today_str}.md"
    target_file = digests_dir / filename
    
    try:
        target_file.write_text(digest_content, encoding="utf-8")
        file_url = str(target_file).replace('\\', '/')
        return (
            f"### 📋 [{digest_type.upper()} DIGEST] Saved to Obsidian Vault\n"
            f"Productivity report compiled successfully, sir!\n"
            f"Saved to: [{filename}](file:///{file_url})\n\n"
            f"Preview:\n{digest_content[:400]}..."
        )
    except Exception as e:
        return f"Error writing digest file: {e}"
