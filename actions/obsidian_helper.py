"""
obsidian_helper.py — Manages Obsidian vaults, logs markdown pages, and appends task notes.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import json
import sqlite3
from pathlib import Path
from actions.semantic_store import _get_gemini_client, index_file, init_db, DB_PATH

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
