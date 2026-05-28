"""
semantic_store.py — Stores and retrieves context vectors locally.

This is a standard action module for the IP Prime personal assistant suite.
"""

import os
import json
from pathlib import Path
from google import genai
import lancedb
import pyarrow as pa

class RateLimitError(Exception):
    """Custom exception raised when Gemini API key hits a 429 Resource Exhausted / Quota limit."""
    pass

# Setup database path
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "memory" / "lancedb_store"
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
    """Initializes LanceDB database with proper schemas."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = lancedb.connect(str(DB_PATH))
    
    if "documents" not in db.table_names():
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("file_path", pa.string()),
            pa.field("content_chunk", pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), 3072)),
            pa.field("last_modified", pa.float64())
        ])
        db.create_table("documents", schema=schema)
        
    if "conversations" not in db.table_names():
        conv_schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("role", pa.string()),
            pa.field("content", pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), 3072)),
            pa.field("timestamp", pa.float64())
        ])
        db.create_table("conversations", schema=conv_schema)
        
    if "code_reviews" not in db.table_names():
        rev_schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("file_path", pa.string()),
            pa.field("review_content", pa.string()),
            pa.field("grade", pa.string()),
            pa.field("embedding", pa.list_(pa.float32(), 3072)),
            pa.field("timestamp", pa.float64())
        ])
        db.create_table("code_reviews", schema=rev_schema)
        
    return db

def compute_cosine_similarity(vec1, vec2):
    """Fallback cosine similarity - not needed for LanceDB directly but kept for compatibility."""
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
    """Generates embedding for a given text using Gemini's embedding model."""
    try:
        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text
        )
        return response.embeddings[0].values
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
            raise RateLimitError(f"Gemini API Rate Limit Exceeded (429): {err_msg}")
        print(f"[Semantic Store] Gemini Embedding API error: {e}")
        raise

def index_file(client: genai.Client, file_path: Path) -> bool:
    """Chunks a file, embeds chunks, and indexes it incrementally in LanceDB."""
    try:
        # Resolve relative path for portability
        try:
            rel_path = file_path.relative_to(BASE_DIR)
        except ValueError:
            rel_path = file_path
        
        path_str = str(rel_path)
        mtime = file_path.stat().st_mtime
        
        db = init_db()
        tbl = db.open_table("documents")
        
        # Check database to see if file modified time is identical
        try:
            # Check if any chunk for this file exists with the same mtime
            existing = tbl.search().where(f"file_path = '{path_str}'").limit(1).to_list()
            if existing and existing[0]:
                if abs(existing[0]['last_modified'] - mtime) < 0.1:
                    # Unchanged, skip indexing!
                    return False
            # If modified, remove old chunks
            tbl.delete(f"file_path = '{path_str}'")
        except Exception:
            pass # ignore errors if filtering fails initially
            
        # Read file contents safely
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception:
            return False
            
        if not content.strip():
            return False

        chunks = chunk_text(content)
        data = []
        
        for idx, chunk in enumerate(chunks):
            chunk_id = f"{path_str}##{idx}"
            # Embed chunk
            emb = get_embedding(client, chunk)
            data.append({
                "id": chunk_id,
                "file_path": path_str,
                "content_chunk": chunk,
                "embedding": emb,
                "last_modified": mtime
            })
            
        if data:
            tbl.add(data)
        return True
    except RateLimitError:
        raise
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
        
    ignored_folders = {
        ".git", "__pycache__", ".venv", "node_modules", "build", "dist", "assets",
        "browser_profiles", "browser_data", ".ruff_cache", "logs", "brain", ".gemini"
    }
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
    """Embeds query, performs vector search using LanceDB, and returns formatted matches."""
    db = init_db()
    try:
        client = _get_gemini_client()
    except Exception as e:
        return f"Authentication Error: {e}"
        
    try:
        query_emb = get_embedding(client, query)
    except Exception as e:
        return f"Error embedding search query: {e}"
        
    try:
        tbl = db.open_table("documents")
        # Native LanceDB vector search! Fast and scalable!
        results = tbl.search(query_emb).limit(limit).to_list()
    except Exception as e:
        return f"No documents indexed or LanceDB error: {e}. Please index your workspace or documents first."
    
    if not results:
        return "No documents indexed. Please index your workspace or documents first."
        
    formatted_output = [f"### 🔍 Semantic Search Results for: '{query}'\n"]
    for i, res in enumerate(results, 1):
        path = res["file_path"]
        chunk = res["content_chunk"]
        # LanceDB distance is L2 by default, so we can display that or a converted score
        # L2 distance is smaller = better
        score = res.get("_distance", 0.0)
        
        # Truncate content preview cleanly
        preview = chunk.strip().replace("\\n", " \\n> ")
        formatted_output.append(
            f"**{i}. [{path}](file:///{BASE_DIR / path})** *(Distance: {score:.3f})*\\n"
            f"> {preview}\\n"
        )
        
    return "\\n".join(formatted_output)

def safe_get_embedding(text: str) -> list:
    """Generates embedding using Gemini, falls back to Ollama or a mock zero vector on error."""
    # 1. Try Gemini
    try:
        client = _get_gemini_client()
        return get_embedding(client, text)
    except Exception as e:
        print(f"[Semantic Store] Gemini Embedding failed: {e}. Trying local fallback...")
        
    # 2. Try Ollama local embeddings
    try:
        import requests
        # Load local url
        ollama_url = "http://127.0.0.1:11434"
        feat_path = BASE_DIR / "config" / "prime_features.json"
        if feat_path.exists():
            with open(feat_path, "r", encoding="utf-8") as f:
                feats = json.load(f)
            ollama_url = feats.get("local_first", {}).get("ollama_url", ollama_url)
        
        payload = {
            "model": "nomic-embed-text",
            "prompt": text
        }
        resp = requests.post(f"{ollama_url.rstrip('/')}/api/embeddings", json=payload, timeout=2)
        if resp.status_code == 200:
            emb = resp.json().get("embedding", [])
            if len(emb) == 3072:
                return emb
            elif len(emb) > 0:
                # Pad or truncate to 3072
                if len(emb) < 3072:
                    return emb + [0.0] * (3072 - len(emb))
                else:
                    return emb[:3072]
    except Exception as local_e:
        print(f"[Semantic Store] Ollama Embedding failed: {local_e}")
        
    # 3. Fallback to mock zeros vector (length 3072) to prevent crash
    return [0.0] * 3072

def index_conversation_turn(role: str, content: str, session_id: str = "default") -> bool:
    """Indexes a single turn of conversation (user or assistant) in LanceDB conversations table."""
    if not content or not content.strip():
        return False
    try:
        import time
        db = init_db()
        tbl = db.open_table("conversations")
        
        emb = safe_get_embedding(content)
        ts = time.time()
        turn_id = f"{session_id}##{ts}##{role}"
        
        tbl.add([{
            "id": turn_id,
            "role": role,
            "content": content,
            "embedding": emb,
            "timestamp": ts
        }])
        return True
    except Exception as e:
        print(f"[Semantic Store] Error indexing conversation turn: {e}")
        return False

def index_code_review(file_path: str, review_content: str, grade: str) -> bool:
    """Indexes a completed code review in LanceDB code_reviews table."""
    if not review_content or not review_content.strip():
        return False
    try:
        import time
        db = init_db()
        tbl = db.open_table("code_reviews")
        
        emb = safe_get_embedding(review_content)
        ts = time.time()
        review_id = f"{file_path}##{ts}"
        
        tbl.add([{
            "id": review_id,
            "file_path": str(file_path),
            "review_content": review_content,
            "grade": str(grade),
            "embedding": emb,
            "timestamp": ts
        }])
        return True
    except Exception as e:
        print(f"[Semantic Store] Error indexing code review: {e}")
        return False

def search_history_semantic(query: str, limit: int = 5) -> str:
    """Searches across conversation turns, code reviews, and indexed documents semantically."""
    if not query or not query.strip():
        return "Query is empty, sir."
        
    db = init_db()
    emb = safe_get_embedding(query)
    
    output = [f"### [SEARCH] Extended Semantic Memory Search for: '{query}'\n"]
    
    # 1. Search conversations
    try:
        tbl_conv = db.open_table("conversations")
        conv_res = tbl_conv.search(emb).limit(limit).to_list()
        if conv_res:
            output.append("#### [CONVERSATIONS] Past Conversations:")
            for i, res in enumerate(conv_res, 1):
                role_label = "Pratik Sir" if res["role"] == "user" else "IP Prime"
                score = res.get("_distance", 0.0)
                import datetime
                ts_str = datetime.datetime.fromtimestamp(res["timestamp"]).strftime('%Y-%m-%d %H:%M')
                output.append(f"{i}. **[{ts_str}] {role_label}**: {res['content'].strip()[:300]}... *(Distance: {score:.3f})*")
            output.append("")
    except Exception as e:
        print(f"[Semantic Search] Conversations query failed: {e}")
        
    # 2. Search code reviews
    try:
        tbl_rev = db.open_table("code_reviews")
        rev_res = tbl_rev.search(emb).limit(limit).to_list()
        if rev_res:
            output.append("#### [CODE REVIEWS] Past Code Reviews:")
            for i, res in enumerate(rev_res, 1):
                score = res.get("_distance", 0.0)
                import datetime
                ts_str = datetime.datetime.fromtimestamp(res["timestamp"]).strftime('%Y-%m-%d %H:%M')
                fname = Path(res["file_path"]).name
                output.append(
                    f"{i}. **[{ts_str}] `{fname}` (Grade: {res['grade']})**\n"
                    f"   > {res['review_content'].strip()[:250]}... *(Distance: {score:.3f})*"
                )
            output.append("")
    except Exception as e:
        print(f"[Semantic Search] Code reviews query failed: {e}")

    # 3. Search document store chunks
    try:
        tbl_doc = db.open_table("documents")
        doc_res = tbl_doc.search(emb).limit(limit).to_list()
        if doc_res:
            output.append("#### [DOCUMENTS] Project Documents & Chunks:")
            for i, res in enumerate(doc_res, 1):
                score = res.get("_distance", 0.0)
                output.append(
                    f"{i}. **[{res['file_path']}](file:///{BASE_DIR / res['file_path']})** *(Distance: {score:.3f})*\n"
                    f"   > {res['content_chunk'].strip()[:200]}..."
                )
            output.append("")
    except Exception as e:
        print(f"[Semantic Search] Documents query failed: {e}")
        
    total_lines = len(output)
    if total_lines <= 1:
        return f"No semantic matches found for '{query}' in conversation history, code reviews, or documents, sir."
        
    return "\n".join(output)

