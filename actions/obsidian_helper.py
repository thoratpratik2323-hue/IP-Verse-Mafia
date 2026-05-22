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
        from actions.semantic_store import get_embedding, compute_cosine_similarity
        query_emb = get_embedding(client, query)
    except Exception as e:
        return f"Error: {e}"
        
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, content_chunk, embedding FROM documents")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "No notes indexed in Obsidian Vault. Please run index_obsidian_vault first."
        
    vault_path_str = get_obsidian_vault_path()
    
    results = []
    for path, chunk, emb_str in rows:
        is_obsidian = False
        if vault_path_str:
            is_obsidian = vault_path_str.lower() in path.lower() or os.path.isabs(path)
        else:
            is_obsidian = path.endswith(".md")
            
        if not is_obsidian:
            continue
            
        try:
            emb = json.loads(emb_str)
            similarity = compute_cosine_similarity(query_emb, emb)
            results.append((path, chunk, similarity))
        except Exception:
            continue
            
    if not results:
        return "No matches found in your Obsidian notes."
        
    results.sort(key=lambda x: x[2], reverse=True)
    top_matches = results[:limit]
    
    formatted = [f"### 🔍 Obsidian Semantic Notes for: '{query}'\n"]
    for i, (path, chunk, score) in enumerate(top_matches, 1):
        preview = chunk.strip().replace("\n", " \n> ")
        path_url = path.replace('\\', '/')
        formatted.append(
            f"**{i}. [{Path(path).name}](file:///{path_url})** *(Score: {score:.3f})*\n"
            f"> {preview}\n"
        )
    return "\n".join(formatted)
