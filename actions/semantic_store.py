import os
import json
import sqlite3
import time
from pathlib import Path
from google import genai

# Setup database path
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "memory" / "semantic_store.db"
API_KEYS_PATH = BASE_DIR / "config" / "api_keys.json"

# Ensure memory folder exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def _get_gemini_client() -> genai.Client:
    """Loads API key and returns a Gemini Client."""
    try:
        with open(API_KEYS_PATH, "r", encoding="utf-8") as f:
            api_key = json.load(f)["gemini_api_key"]
        return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[Semantic Store] Error getting API key: {e}")
        raise ValueError("Gemini API key not configured properly in config/api_keys.json")

def init_db():
    """Initializes the SQLite database with proper schema."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            file_path TEXT,
            content_chunk TEXT,
            embedding TEXT,
            last_modified REAL
        )
    """)
    conn.commit()
    conn.close()

def compute_cosine_similarity(vec1, vec2):
    """Computes the dot product of two normalized vectors (Cosine Similarity)."""
    # Gemini embeddings returned by text-embedding-004 are normalized (magnitude is 1.0)
    # Therefore, dot product is exactly equal to cosine similarity.
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    return dot_product

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list:
    """Splits text into overlapping chunks cleanly."""
    chunks = []
    if not text:
        return chunks
    
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += (chunk_size - overlap)
    return chunks

def get_embedding(client: genai.Client, text: str) -> list:
    """Generates embedding for a given text using Gemini's text-embedding-004 model."""
    try:
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"[Semantic Store] Gemini Embedding API error: {e}")
        raise

def index_file(client: genai.Client, file_path: Path) -> bool:
    """Chunks a file, embeds chunks, and indexes it incrementally in SQLite."""
    try:
        # Resolve relative path for portability
        try:
            rel_path = file_path.relative_to(BASE_DIR)
        except ValueError:
            rel_path = file_path
        
        path_str = str(rel_path)
        mtime = file_path.stat().st_mtime
        
        # Check database to see if file modified time is identical
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT last_modified FROM documents WHERE file_path = ?", (path_str,))
        row = cursor.fetchone()
        
        if row and abs(row[0] - mtime) < 0.1:
            # Unchanged, skip indexing!
            conn.close()
            return False

        # If modified, remove old chunks
        cursor.execute("DELETE FROM documents WHERE file_path = ?", (path_str,))
        
        # Read file contents safely
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            conn.close()
            return False
            
        if not content.strip():
            conn.commit()
            conn.close()
            return False

        chunks = chunk_text(content)
        
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{path_str}##{idx}"
            # Embed chunk
            emb = get_embedding(client, chunk)
            cursor.execute(
                "INSERT OR REPLACE INTO documents (id, file_path, content_chunk, embedding, last_modified) VALUES (?, ?, ?, ?, ?)",
                (chunk_id, path_str, chunk, json.dumps(emb), mtime)
            )
            
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[Semantic Store] Error indexing file {file_path}: {e}")
        return False

def index_directory(dir_path_str: str) -> str:
    """Walks the directory and indexes new or modified text/source files."""
    init_db()
    client = _get_gemini_client()
    
    dir_path = Path(dir_path_str).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        return f"Error: Directory '{dir_path_str}' does not exist or is not a folder."
        
    ignored_folders = {".git", "__pycache__", ".venv", "node_modules", "build", "dist", "assets"}
    allowed_extensions = {".py", ".txt", ".md", ".json", ".html", ".css", ".js", ".ts", ".c", ".cpp", ".h"}
    
    indexed_count = 0
    skipped_count = 0
    total_files = 0
    
    for root, dirs, files in os.walk(dir_path):
        # In-place modification of dirs to prune ignored folders
        dirs[:] = [d for d in dirs if d not in ignored_folders]
        
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in allowed_extensions:
                total_files += 1
                if index_file(client, file_path):
                    indexed_count += 1
                else:
                    skipped_count += 1
                    
    return f"Indexed {indexed_count} new/updated files, skipped {skipped_count} unchanged files (Total processed: {total_files})."

def semantic_search(query: str, limit: int = 5) -> str:
    """Embeds query, performs cosine similarity against all database entries, and returns formatted matches."""
    init_db()
    try:
        client = _get_gemini_client()
    except Exception as e:
        return f"Authentication Error: {e}"
        
    try:
        query_emb = get_embedding(client, query)
    except Exception as e:
        return f"Error embedding search query: {e}"
        
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT file_path, content_chunk, embedding FROM documents")
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "No documents indexed. Please index your workspace or documents first."
        
    results = []
    for path, chunk, emb_str in rows:
        try:
            emb = json.loads(emb_str)
            similarity = compute_cosine_similarity(query_emb, emb)
            results.append((path, chunk, similarity))
        except Exception:
            continue
            
    # Sort by similarity descending
    results.sort(key=lambda x: x[2], reverse=True)
    top_matches = results[:limit]
    
    formatted_output = [f"### 🔍 Semantic Search Results for: '{query}'\n"]
    for i, (path, chunk, score) in enumerate(top_matches, 1):
        # Truncate content preview cleanly
        preview = chunk.strip().replace("\n", " \n> ")
        formatted_output.append(
            f"**{i}. [{path}](file:///{BASE_DIR / path})** *(Score: {score:.3f})*\n"
            f"> {preview}\n"
        )
        
    return "\n".join(formatted_output)
