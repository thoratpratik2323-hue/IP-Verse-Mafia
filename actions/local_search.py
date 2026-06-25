import os
import json
import math
import hashlib
from pathlib import Path
from typing import Any, Optional
from google import genai as new_genai

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
INDEX_FILE = DATA_DIR / "rag_index.json"

def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump({"files": {}}, f, indent=4)

def _load_index() -> dict:
    _ensure_data_dir()
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"files": {}}

def _save_index(index: dict):
    _ensure_data_dir()
    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=4)
    except Exception as e:
        print(f"[LocalSearch] ⚠️ Failed to save index: {e}")

def get_file_hash(path: Path) -> str:
    try:
        return hashlib.md5(path.read_bytes()).hexdigest()
    except Exception:
        return ""

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return chunks

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_prod = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(a * a for a in v2))
    if mag1 == 0.0 or mag2 == 0.0:
        return 0.0
    return dot_prod / (mag1 * mag2)

def generate_gemini_embedding(text: str, client: new_genai.Client) -> list[float]:
    try:
        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text
        )
        if response and response.embeddings:
            return response.embeddings[0].values
    except Exception as e:
        print(f"[LocalSearch] ⚠️ Embedding error: {e}")
    return []

def scan_and_index_directory(target_dir: Path, client: new_genai.Client) -> tuple[int, int]:
    """Walks the directory, chunks and indexes txt, md, py files using incremental hashing."""
    index = _load_index()
    files_indexed = 0
    chunks_created = 0
    
    # Exclude list to prevent virtual env or git indexing
    exclude_dirs = {".git", ".venv", "__pycache__", "node_modules", "dist", "build", "data"}
    
    for root, dirs, files in os.walk(target_dir):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            suffix = file_path.suffix.lower()
            if suffix not in {".txt", ".md", ".py", ".json", ".ini", ".conf"}:
                continue
                
            try:
                # Check file size to avoid loading huge log files
                if file_path.stat().st_size > 1024 * 1024: # > 1MB
                    continue
                
                curr_hash = get_file_hash(file_path)
                rel_path = str(file_path.relative_to(target_dir))
                
                # Check if file has changed or is new
                existing = index["files"].get(rel_path)
                if existing and existing.get("hash") == curr_hash:
                    continue
                    
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                chunks = chunk_text(text)
                
                chunk_entries = []
                for idx, chunk in enumerate(chunks):
                    emb = generate_gemini_embedding(chunk, client)
                    if emb:
                        chunk_entries.append({
                            "text": chunk,
                            "embedding": emb,
                            "index": idx
                        })
                        chunks_created += 1
                
                index["files"][rel_path] = {
                    "hash": curr_hash,
                    "chunks": chunk_entries
                }
                files_indexed += 1
                
            except Exception as e:
                print(f"[LocalSearch] ⚠️ Error indexing {file_path.name}: {e}")
                
    if files_indexed > 0:
        _save_index(index)
        
    return files_indexed, chunks_created

def local_search(parameters: dict[str, Any], player=None, speak=None) -> str:
    """Answers user queries by performing a semantic hybrid search over local workspace files."""
    query = parameters.get("query", "").strip()
    path_str = parameters.get("path", "").strip()
    
    if not query:
        return "Search query cannot be empty, sir."
        
    if path_str:
        target_dir = Path(path_str).resolve()
    else:
        # Default to current saturday workspace
        target_dir = Path(__file__).resolve().parent.parent

    if not target_dir.exists():
        return f"Specified directory '{path_str}' does not exist, sir."

    try:
        from main import _get_api_key
        api_key = _get_api_key()
        if not api_key:
            return "Failed to fetch API key, sir."
        
        client = new_genai.Client(api_key=api_key)
        
        if speak:
            speak("Scanning and indexing files in your workspace, sir.")
            
        # Index new/modified files
        indexed_files, indexed_chunks = scan_and_index_directory(target_dir, client)
        if player and indexed_files > 0:
            player.write_log(f"SYS [RAG Indexer]: Indexed {indexed_files} modified files ({indexed_chunks} chunks).")
            
        # Embed the search query
        query_emb = generate_gemini_embedding(query, client)
        if not query_emb:
            return "Failed to generate embedding for the search query, sir."

        # Fetch index and calculate cosine similarities
        index = _load_index()
        results = []
        
        for rel_path, file_data in index.get("files", {}).items():
            for chunk in file_data.get("chunks", []):
                similarity = cosine_similarity(query_emb, chunk.get("embedding", []))
                results.append({
                    "path": rel_path,
                    "text": chunk.get("text", ""),
                    "score": similarity
                })
                
        # Sort by similarity score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        top_matches = results[:5]
        
        if not top_matches or top_matches[0]["score"] < 0.25:
            return f"Aapki local files mein query '{query}' se match karta hua relevant context nahi mila, sir."
            
        # Prepare context for LLM
        context_str = ""
        for idx, match in enumerate(top_matches, 1):
            context_str += f"\n--- Context Source: {match['path']} (Score: {match['score']:.2f}) ---\n{match['text']}\n"
            
        if speak:
            speak("Generating answer based on local context, sir.")
            
        # Generate final answer using Gemini
        prompt = (
            f"You are Saturday, answering a user query using the retrieved local workspace context.\n"
            f"Provide a clear, helpful, and grounded answer in Hinglish. "
            f"State which files you found the information in.\n\n"
            f"User Query: {query}\n\n"
            f"Retrieved Local Context:\n{context_str}"
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        return f"Error executing local search: {e}"
