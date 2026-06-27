import time
from actions.semantic_store import init_db, safe_get_embedding

def add_semantic_memory(text: str, file_path: str = "generic_input") -> bool:
    """
    Adds a text chunk to Saturday's LanceDB documents table for semantic search/RAG.
    Resolves ModuleNotFoundError for memory.semantic.
    """
    if not text or not text.strip():
        return False
    try:
        db = init_db()
        tbl = db.open_table("documents")
        
        emb = safe_get_embedding(text)
        ts = time.time()
        chunk_id = f"{file_path}##{ts}##{hash(text)}"
        
        tbl.add([{
            "id": chunk_id,
            "file_path": file_path,
            "content_chunk": text,
            "embedding": emb,
            "last_modified": ts
        }])
        return True
    except Exception as e:
        print(f"[Semantic Memory] Error adding semantic memory: {e}")
        return False
