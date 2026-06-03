import uuid
import chromadb
from pathlib import Path
from pypdf import PdfReader

class RAGEngine:
    """
    Retrieval-Augmented Generation (RAG) Engine for IP Prime.
    Allows IP Prime to read, store, and semantically search through documents.
    """
    def __init__(self):
        # Initialize local persistent vector DB
        home_dir = Path.home() / ".ipprime" / "vector_db"
        home_dir.mkdir(parents=True, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(path=str(home_dir))
        
        # Create or get a default collection
        # Uses default sentence-transformers model under the hood
        self.collection = self.chroma_client.get_or_create_collection(name="ipprime_knowledge")
        print("[RAGEngine] \U0001f4da Vector Database Online. Ready for semantic search.")

    def ingest_text(self, text: str, source_metadata: dict = None):
        """Chunks and stores raw text into the vector DB."""
        if not source_metadata:
            source_metadata = {"source": "direct_input"}
            
        # Basic chunking (e.g. by paragraphs or fixed length)
        # For simplicity, chunk by 1000 characters
        chunk_size = 1000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        ids = [str(uuid.uuid4()) for _ in chunks]
        metadatas = [source_metadata for _ in chunks]
        
        self.collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        return len(chunks)

    def ingest_pdf(self, file_path: str):
        """Reads a PDF and ingests its text."""
        try:
            reader = PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
            
            chunks_added = self.ingest_text(full_text, source_metadata={"source": file_path, "type": "pdf"})
            return f"Successfully ingested {file_path} ({chunks_added} chunks)."
        except Exception as e:
            return f"Error reading PDF: {str(e)}"

    def query_knowledge(self, query: str, n_results: int = 3):
        """Searches the vector DB for context matching the query."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            if not results['documents'] or not results['documents'][0]:
                return ""
                
            # Combine the top results into a single context string
            context_string = "\n---\n".join(results['documents'][0])
            return context_string
        except Exception as e:
            print(f"[RAGEngine] Query error: {e}")
            return ""

if __name__ == "__main__":
    # Simple test
    rag = RAGEngine()
    rag.ingest_text("IP Prime was upgraded to use a 6-layer brain architecture with SQLite memory on May 28, 2026.")
    res = rag.query_knowledge("What brain architecture does IP Prime use?")
    print(f"RAG Result: {res}")
