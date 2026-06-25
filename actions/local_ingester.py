import os
import logging
from pathlib import Path
from memory.semantic import add_semantic_memory

logger = logging.getLogger("saturday.actions.local_ingester")

def local_ingester(parameters: dict, player=None, speak=None, **kwargs) -> str:
    """
    Ingests all files (PDF, Markdown, Text, code files) from a local folder path,
    extracts text chunks, generates semantic embeddings, and stores them in Saturday's RAG memory.
    """
    folder_path = parameters.get("folder_path", "").strip()
    if not folder_path:
        return "Please specify a folder_path parameter."
        
    folder = Path(folder_path).resolve()
    if not folder.exists():
        return f"The folder path '{folder_path}' does not exist, sir."
    if not folder.is_dir():
        return f"The path '{folder_path}' is not a directory, sir."

    custom_extensions = parameters.get("extensions")
    if custom_extensions:
        # Normalize extensions to include dot (e.g. "pdf" -> ".pdf")
        extensions = [ext.strip().lower() if ext.startswith(".") else f".{ext.strip().lower()}" for ext in custom_extensions]
    else:
        # Default supported extensions
        extensions = [".txt", ".md", ".py", ".json", ".csv", ".js", ".ts", ".html", ".css", ".pdf", ".yaml", ".yml", ".ini"]

    # Exclude common bloated directories
    exclude_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".idea", ".vscode"}

    files_processed = 0
    total_chunks = 0
    errors = []

    # Simple recursive directory traversal
    for root, dirs, files in os.walk(folder):
        # In-place modify dirs to skip excluded folders recursively
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            file_path = Path(root) / file
            ext = file_path.suffix.lower()
            if ext not in extensions:
                continue

            try:
                content = ""
                # Parse PDF
                if ext == ".pdf":
                    try:
                        import pypdf
                        reader = pypdf.PdfReader(file_path)
                        pages_text = []
                        for idx, page in enumerate(reader.pages):
                            page_text = page.extract_text()
                            if page_text:
                                pages_text.append((idx + 1, page_text))
                        
                        # Process chunks by page to keep metadata accurate
                        for page_num, text in pages_text:
                            text_chunks = chunk_text(text)
                            for chunk in text_chunks:
                                chunk_with_meta = f"[File: {file_path.name} | Page: {page_num}] {chunk.strip()}"
                                add_semantic_memory(chunk_with_meta)
                                total_chunks += 1
                        files_processed += 1
                        continue
                    except ImportError:
                        errors.append(f"{file_path.name}: pypdf library is missing. Cannot parse PDF.")
                        continue
                    except Exception as pdf_err:
                        errors.append(f"{file_path.name}: PDF read error: {pdf_err}")
                        continue
                
                # Parse standard text files
                else:
                    # Try UTF-8 first, fallback to cp1252 / latin-1
                    try:
                        content = file_path.read_text(encoding="utf-8")
                    except UnicodeDecodeError:
                        content = file_path.read_text(encoding="latin-1")
                
                if not content.strip():
                    continue

                text_chunks = chunk_text(content)
                for chunk in text_chunks:
                    chunk_with_meta = f"[File: {file_path.name}] {chunk.strip()}"
                    add_semantic_memory(chunk_with_meta)
                    total_chunks += 1
                files_processed += 1

            except Exception as e:
                errors.append(f"{file_path.name}: {e}")

    summary = f"Successfully ingested {files_processed} files from '{folder.name}'. Generated {total_chunks} chunks in local RAG memory."
    if errors:
        summary += f"\nNote: Encountered {len(errors)} issues:\n" + "\n".join(errors[:5])
        if len(errors) > 5:
            summary += f"\n...and {len(errors) - 5} more errors."
    
    return summary

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Helper to split text into chunks with overlap."""
    if len(text) <= chunk_size:
        return [text]
        
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
        
    return chunks
