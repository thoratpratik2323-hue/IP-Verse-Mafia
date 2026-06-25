import os
import subprocess
from pathlib import Path

PROJECTS_DIR = Path.home() / "Downloads" / "sat output" / "SaturdayProjects"

def project_setup(parameters: dict, player=None) -> str:
    p_type = parameters.get("project_type", "Flask").lower().strip()
    p_name = parameters.get("project_name", "my_project").strip()
    
    # Sanitize project folder name
    p_name = "".join(c for c in p_name if c.isalnum() or c in ("-", "_")).strip()
    if not p_name:
        p_name = "my_project"
        
    target_dir = PROJECTS_DIR / p_name
    if target_dir.exists():
        return f"Project directory '{p_name}' already exists in SaturdayProjects, sir."
        
    target_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        if p_type == "flask":
            app_code = (
                "from flask import Flask, jsonify\n\n"
                "app = Flask(__name__)\n\n"
                "@app.route('/')\n"
                "def home():\n"
                "    return jsonify(message='Hello from Saturday Project Setup!', status='active')\n\n"
                "if __name__ == '__main__':\n"
                "    app.run(debug=True, port=5000)\n"
            )
            (target_dir / "app.py").write_text(app_code, encoding="utf-8")
            (target_dir / "requirements.txt").write_text("flask\n", encoding="utf-8")
            
            # Install flask locally
            subprocess.run([os.sys.executable, "-m", "pip", "install", "flask"], timeout=30, capture_output=True)
            
        elif p_type == "fastapi":
            app_code = (
                "from fastapi import FastAPI\n\n"
                "app = FastAPI()\n\n"
                "@app.get('/')\n"
                "def read_root():\n"
                "    return {'message': 'Hello from FastAPI Saturday setup!'}\n"
            )
            (target_dir / "main.py").write_text(app_code, encoding="utf-8")
            (target_dir / "requirements.txt").write_text("fastapi\nuvicorn\n", encoding="utf-8")
            
            subprocess.run([os.sys.executable, "-m", "pip", "install", "fastapi", "uvicorn"], timeout=30, capture_output=True)
            
        else: # Default HTML/JS project
            html_code = (
                "<!DOCTYPE html>\n<html>\n<head>\n    <title>Saturday Project</title>\n"
                "    <style>\n"
                "        body { background: #00060a; color: #00d4ff; font-family: 'Courier New', monospace; \n"
                "               display: flex; flex-direction: column; justify-content: center; align-items: center; \n"
                "               height: 100vh; margin: 0; }\n"
                "        h1 { border: 1px solid #0d3347; padding: 20px; border-radius: 8px; background: #010d14; }\n"
                "    </style>\n"
                "</head>\n<body>\n    <h1>Project Setup Completed by Saturday AI!</h1>\n</body>\n</html>"
            )
            (target_dir / "index.html").write_text(html_code, encoding="utf-8")
            
        # Launch VS Code in folder
        subprocess.run(["code", str(target_dir)], shell=True, capture_output=True, text=True, timeout=10)
        
        return f"Successfully provisioned your new '{p_type}' project inside SaturdayProjects/{p_name} and opened VS Code, sir!"
        
    except Exception as e:
        return f"Failed to set up project workspace: {e}, sir."
