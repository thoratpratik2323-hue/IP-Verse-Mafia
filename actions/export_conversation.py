import time
from datetime import datetime
from pathlib import Path
from PyQt6.QtGui import QPdfWriter, QTextDocument, QPageLayout, QPageSize
from PyQt6.QtCore import QSizeF

def export_conversation(parameters: dict, player=None, speak=None) -> str:
    """
    Exports the current session's conversation log to TXT or PDF.
    Parameters:
      format (str): 'txt' or 'pdf' (default: 'txt')
      file_path (str): Optional custom filepath
    """
    fmt = parameters.get("format", "txt").lower().strip()
    custom_path = parameters.get("file_path", "").strip()
    
    if not player or not hasattr(player, "_win") or not player._win:
        return "UI context not available, cannot export conversation, sir."
        
    # Retrieve plain text from the log widget
    try:
        log_widget = player._win._log
        full_text = log_widget.toPlainText()
    except Exception as e:
        return f"Failed to retrieve conversation logs: {e}, sir."
        
    if not full_text.strip():
        return "The conversation history is empty, sir."
        
    # Determine export path
    if custom_path:
        export_path = Path(custom_path)
    else:
        downloads_dir = Path.home() / "Downloads"
        filename = f"saturday_conversation_{int(time.time())}.{fmt}"
        export_path = downloads_dir / filename
        
    try:
        export_path.parent.mkdir(parents=True, exist_ok=True)
        
        if fmt == "pdf":
            # Render using QPdfWriter and QTextDocument for a native zero-dependency PDF
            writer = QPdfWriter(str(export_path))
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            
            # Simple styling for the document
            doc = QTextDocument()
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: monospace; font-size: 10pt; line-height: 1.4; color: #333333; }}
                    h1 {{ color: #007ACC; border-bottom: 2px solid #007ACC; padding-bottom: 5px; }}
                    .meta {{ color: #777777; margin-bottom: 20px; }}
                    pre {{ background-color: #F4F4F4; padding: 10px; border-radius: 4px; white-space: pre-wrap; }}
                </style>
            </head>
            <body>
                <h1>S.A.T.U.R.D.A.Y — Conversation History</h1>
                <div class="meta">Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>
                <pre>{full_text}</pre>
            </body>
            </html>
            """
            doc.setHtml(html_content)
            doc.print(writer)
        else:
            # Save as plain text
            export_path.write_text(full_text, encoding="utf-8")
            
        msg = f"Successfully exported conversation history to {export_path.resolve()}, sir."
        if speak:
            speak(f"सर, मैंने बातचीत का इतिहास {fmt} फ़ॉर्मेट में सेव कर दिया है।")
        if player:
            player.write_log(f"SATURDAY: {msg}")
        return msg
    except Exception as e:
        err_msg = f"Failed to export conversation history: {e}, sir."
        if player:
            player.write_log(f"SYS ERR: {err_msg}")
        return err_msg
