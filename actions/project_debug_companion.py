"""
project_debug_companion.py — Scans workspace tracebacks and suggests programmatic code fixes.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/project_debug_companion.py
import os
import sys
import re
import json
import time
import subprocess
import shutil
from pathlib import Path
from actions.prime_utils import get_api_key, get_base_dir

def _get_gemini_client():
    """Returns a google-genai client using the central API key."""
    try:
        from google import genai
        api_key = get_api_key()
        if api_key:
            return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[Project/Debug Companion] Client init failed: {e}")
    return None

# ==========================================
# 1. Project Start Automation
# ==========================================
def project_start_automation(folder_path: str = "", dev_url: str = "http://localhost:3000", player=None) -> str:
    """Launches VS Code, opens terminal shell, and starts browser to dev port in one command."""
    target = folder_path if folder_path else str(get_base_dir())
    path = Path(target)
    
    if not path.exists():
        return f"Specified folder exist nahi karta, sir: {target}"
        
    logs = [f"### 🚀 Project Start Automation for `{path.name}`"]
    
    # 1. Open in VS Code
    if shutil.which("code"):
        try:
            subprocess.Popen(["code", str(path)], shell=True)
            logs.append("- [OK] VS Code opened successfully.")
        except Exception as e:
            logs.append(f"- [FAIL] VS Code open error: {e}")
    else:
        logs.append("- [WARN] VS Code executable ('code') missing from PATH.")
        
    # 2. Launch local terminal/shell window
    try:
        if sys.platform == "win32":
            subprocess.Popen(["start", "cmd", "/k", f"cd /d {path}"], shell=True)
            logs.append("- [OK] Windows CMD session launched.")
        else:
            subprocess.Popen(["x-terminal-emulator", "--working-directory", str(path)], shell=True)
            logs.append("- [OK] Terminal session launched.")
    except Exception as e:
        logs.append(f"- [FAIL] Terminal launch error: {e}")
        
    # 3. Launch Web Browser
    try:
        import webbrowser
        webbrowser.open(dev_url)
        logs.append(f"- [OK] Browser launched targeting dev URL: `{dev_url}`")
    except Exception as e:
        logs.append(f"- [FAIL] Browser open error: {e}")
        
    logs.append("\n✅ **Start automation triggered successfully, sir!** Happy coding!")
    return "\n".join(logs)

# ==========================================
# 2. Codebase Onboarder
# ==========================================
def codebase_onboarder(folder_path: str = "", player=None) -> str:
    """Traverses codebase directory and builds a beautiful, comprehensive 5-minute developer onboarding guide."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API configure nahi hai, sir."
        
    target = folder_path if folder_path else str(get_base_dir())
    path = Path(target)
    
    if not path.exists():
        return "Directory missing, sir."
        
    if player:
        player.write_thought(f"Traversing {path.name} to compile onboarding info...")
        
    # Gather workspace file statistics
    file_types = {}
    total_size = 0
    file_count = 0
    structure = []
    
    for root, dirs, files in os.walk(str(path)):
        # Skip ignore folders
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "env", "dist", "build"}]
        
        level = Path(root).relative_to(path).parts
        indent = "  " * len(level)
        if len(level) < 3: # Keep tree visual shallow
            structure.append(f"{indent}📁 {Path(root).name}/")
            
        for f in files:
            fp = Path(root) / f
            file_count += 1
            suffix = fp.suffix or "No Extension"
            file_types[suffix] = file_types.get(suffix, 0) + 1
            try:
                total_size += fp.stat().st_size
                if len(level) < 2:
                    structure.append(f"{indent}  📄 {f}")
            except Exception:
                pass
                
    # Try reading package.json, requirements.txt, readme.md for context
    context_str = ""
    for name in ["readme.md", "package.json", "requirements.txt", "main.py", "app.py"]:
        fp = path / name
        if fp.exists():
            try:
                context_str += f"\n=== {name} Contents (Excerpt) ===\n{fp.read_text(encoding='utf-8', errors='ignore')[:1500]}\n"
            except Exception:
                pass
                
    try:
        from google.genai import types
        system_instruction = (
            "You are a Lead Solutions Architect onboarding a senior developer to a new project. "
            "Analyze the codebase structure, dependency listings, file counts, and README excerpts provided. "
            "Generate a highly professional, beautifully structured '5-Minute Developer Onboarding Guide'. "
            "Include sections: 📦 Project Type/Stack, 📁 Repository Architecture Overview, "
            "🔌 Standard Setup & Dependencies, ⚙️ Entry points & Run commands, and 💡 High-Level Architecture Insights. "
            "Write in a friendly, conversational Hinglish style for Pratik Sir."
        )
        prompt = (
            f"Project Directory Name: {path.name}\n"
            f"Total Files: {file_count} | Total Directory Size: {total_size / (1024*1024):.2f} MB\n"
            f"File Type Stats: {file_types}\n\n"
            f"Shallow Directory Tree:\n" + "\n".join(structure[:30]) + "\n\n"
            f"Context Excerpts:\n{context_str}\n\nPlease build the 5-Minute Developer Onboarding Guide, sir."
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        return f"Onboarding guide generation failed: {e}, sir."

# ==========================================
# 3. Codebase RAG
# ==========================================
def codebase_rag(query: str, folder_path: str = "", player=None) -> str:
    """Performs an efficient search across codebase files to locate specific keywords and features."""
    target = folder_path if folder_path else str(get_base_dir())
    path = Path(target)
    
    if not path.exists() or not query:
        return "Missing directory or query, sir."
        
    matches = []
    # Search for files containing keyword
    for root, dirs, files in os.walk(str(path)):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "env", "dist", "build"}]
        for f in files:
            fp = Path(root) / f
            # Skip binary and very large files
            if fp.suffix in {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".md", ".txt", ".sql"}:
                try:
                    if fp.stat().st_size < 300000: # < 300kb
                        content = fp.read_text(encoding="utf-8", errors="ignore")
                        if query.lower() in content.lower():
                            # Find matching lines
                            lines = content.splitlines()
                            for idx, line in enumerate(lines, 1):
                                if query.lower() in line.lower():
                                    matches.append((fp.relative_to(path), idx, line.strip()))
                except Exception:
                    pass
                    
    if not matches:
        return f"🔍 **Codebase RAG Search:** Keyword `{query}` pure project codebase mein kahin nahi mila, sir."
        
    lines = [f"### 🔍 Codebase RAG Search Results for `{query}`:"]
    lines.append(f"Found {len(matches)} occurrences, sir:\n")
    
    # Cap matches at 30 for output cleanliness
    for rel_path, line_no, content in matches[:30]:
        # Truncate overly long lines
        if len(content) > 100:
            content = content[:97] + "..."
        lines.append(f"- **{rel_path}:{line_no}** → `{content}`")
        
    if len(matches) > 30:
        lines.append(f"\n*... aur {len(matches) - 30} occurrences hain, brief ke liye top 30 show kiye hain, sir.*")
        
    return "\n".join(lines)

# ==========================================
# 4. Tech Debt Tracker
# ==========================================
def tech_debt_tracker(folder_path: str = "", player=None) -> str:
    """Scans all project files for TODO, FIXME, HACK comments and aggregates them into a Markdown report."""
    target = folder_path if folder_path else str(get_base_dir())
    path = Path(target)
    
    if not path.exists():
        return "Directory does not exist, sir."
        
    markers = ["TODO", "FIXME", "HACK", "BUG", "TEMP"]
    debt_items = []
    
    for root, dirs, files in os.walk(str(path)):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "env", "dist", "build"}]
        for f in files:
            fp = Path(root) / f
            if fp.suffix in {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".md", ".txt"}:
                try:
                    lines = fp.read_text(encoding="utf-8", errors="ignore").splitlines()
                    for idx, line in enumerate(lines, 1):
                        for marker in markers:
                            if f"# {marker}" in line or f"// {marker}" in line or f"/* {marker}" in line or (marker in line and ("comment" in line.lower() or "note" in line.lower() or "fix" in line.lower())):
                                debt_items.append((fp.relative_to(path), idx, marker, line.strip()))
                except Exception:
                    pass
                    
    if not debt_items:
        return "🎉 **Mubarak ho, sir!** pure project codebase mein koi TODO, FIXME, ya HACK comments nahi mile. Zero visible technical debt!"
        
    lines = ["### 🛠️ Technical Debt Tracker (TODOs & FIXMEs)\n"]
    lines.append(f"Aapke project mein total **{len(debt_items)} outstanding tech debt points** mile hain, sir:\n")
    lines.append("| File Path | Line | Type | Comment / Instruction |")
    lines.append("| :--- | :--- | :--- | :--- |")
    
    for rel_path, line_no, marker, comment in debt_items[:40]:
        # Clean comment prefix slightly
        clean_comment = re.sub(r"^(?:\s*#\s*|//\s*|/\*\s*|;\s*)", "", comment)
        # Cap length
        if len(clean_comment) > 80:
            clean_comment = clean_comment[:77] + "..."
        lines.append(f"| `{rel_path}` | {line_no} | `{marker}` | {clean_comment} |")
        
    if len(debt_items) > 40:
        lines.append(f"\n*... aur {len(debt_items) - 40} tech debt pointers hain.*")
        
    return "\n".join(lines)

# ==========================================
# 5. Dependency Auditor
# ==========================================
def dependency_auditor(folder_path: str = "", player=None) -> str:
    """Parses requirements.txt or package.json to highlight outdated or insecure packages."""
    target = folder_path if folder_path else str(get_base_dir())
    path = Path(target)
    
    requirements_file = path / "requirements.txt"
    package_json = path / "package.json"
    
    dependencies = []
    dep_source = ""
    
    if requirements_file.exists():
        dep_source = "requirements.txt"
        for line in requirements_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                dependencies.append(line)
    elif package_json.exists():
        dep_source = "package.json"
        try:
            data = json.loads(package_json.read_text(encoding="utf-8"))
            deps = data.get("dependencies", {})
            dev_deps = data.get("devDependencies", {})
            for k, v in deps.items():
                dependencies.append(f"{k}: {v}")
            for k, v in dev_deps.items():
                dependencies.append(f"{k} (Dev): {v}")
        except Exception:
            pass
            
    if not dependencies:
        return "Aapke project root mein requirements.txt ya package.json nahi mila, sir."
        
    client = _get_gemini_client()
    if not client:
        return f"### Dependencies in {dep_source}:\n\n" + "\n".join([f"- {d}" for d in dependencies])
        
    try:
        from google.genai import types
        system_instruction = (
            "You are a DevSecOps Auditor. Review the list of project dependencies and versions. "
            "List any dependencies that have known critical vulnerabilities, are significantly outdated, "
            "or have better modern alternatives. Give recommendations in a clear markdown report "
            "addressed to Pratik Sir in Hinglish."
        )
        prompt = f"Dependencies Source: {dep_source}\nDependencies List:\n" + "\n".join(dependencies)
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        return f"Dependency audit failed: {e}, sir."

# ==========================================
# 6. Stack Trace Explainer
# ==========================================
def stack_trace_explainer(stack_trace: str, player=None) -> str:
    """Explains a complex python/JS traceback error in plain Hinglish and lists fixing commands."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API configure nahi hai, sir."
    try:
        from google.genai import types
        system_instruction = (
            "You are a master of Python, C++, and Javascript runtimes. "
            "Interpret the provided traceback/error output. Detail in extremely simple, delightful Hinglish: "
            "1. Why the crash happened in plain terms. "
            "2. The exact file and line number triggering the exception. "
            "3. Step-by-step terminal commands or code modifications to resolve it. "
            "Address Pratik Sir respectfully."
        )
        prompt = f"Crash Traceback error logs:\n\n{stack_trace}"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        return response.text
    except Exception as e:
        return f"Stack trace explanation error: {e}"

# ==========================================
# 7. Live Log Analyzer
# ==========================================
def live_log_analyzer(log_file_path: str, lines_to_read: int = 50, player=None) -> str:
    """Tails/reads a log file, parses warnings/errors, and returns a clean AI summary report."""
    path = Path(log_file_path)
    if not path.exists():
        return f"Log file exist nahi karti, sir: {log_file_path}"
        
    try:
        log_lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        recent_logs = "\n".join(log_lines[-lines_to_read:])
    except Exception as e:
        return f"Log file load error: {e}"
        
    client = _get_gemini_client()
    if not client:
        return f"### Recent log lines:\n\n```\n{recent_logs}\n```"
        
    try:
        from google.genai import types
        system_instruction = (
            "You are a SysOps Log Expert. Review the provided log excerpt. "
            "Summarize any active system warnings, error loops, exceptions, or connection failures. "
            "Provide helpful resolution tips for Pratik Sir in Hinglish."
        )
        prompt = f"Recent Log Snippet:\n\n{recent_logs}"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        return f"Log analysis error: {e}"

# ==========================================
# 8. Memory Leak Detector
# ==========================================
def memory_leak_detector(process_name_or_pid: str = "", interval_seconds: int = 5, iterations: int = 3, player=None) -> str:
    """Uses psutil to monitor target or system process RAM footprint over time to check for leaks."""
    try:
        import psutil
    except ImportError:
        return "psutil package install nahi hai, memory check fail."
        
    reports = ["### 🧠 Memory Leak Detector Report\n"]
    
    # Identify target process
    target_proc = None
    if process_name_or_pid:
        try:
            pid = int(process_name_or_pid)
            if psutil.pid_exists(pid):
                target_proc = psutil.Process(pid)
        except ValueError:
            # Match by name
            for proc in psutil.process_iter(["pid", "name"]):
                if process_name_or_pid.lower() in proc.info["name"].lower():
                    target_proc = proc
                    break
    if not target_proc:
        # Fallback: Current Python process
        target_proc = psutil.Process(os.getpid())
        
    reports.append(f"**Target Process:** `{target_proc.name()}` (PID: {target_proc.pid})\n")
    reports.append("| Iteration | Time | RAM Usage (MB) | Virtual Memory (MB) |")
    reports.append("| :--- | :--- | :--- | :--- |")
    
    usages = []
    for i in range(1, iterations + 1):
        try:
            mem_info = target_proc.memory_info()
            rss_mb = mem_info.rss / (1024 * 1024)
            vms_mb = mem_info.vms / (1024 * 1024)
            reports.append(f"| #{i} | {time.strftime('%H:%M:%S')} | {rss_mb:.2f} MB | {vms_mb:.2f} MB |")
            usages.append(rss_mb)
            if i < iterations:
                time.sleep(interval_seconds)
        except Exception as e:
            reports.append(f"| #{i} | Error fetching metrics: {e} | - | - |")
            
    # Simple growth check
    if len(usages) >= 2:
        growth = usages[-1] - usages[0]
        if growth > 5.0:  # Grew more than 5MB in short duration
            reports.append(f"\n⚠️ **Warning:** Memory grew by **{growth:.2f} MB** during the monitoring window. Check for circular references or unclosed handles, sir.")
        else:
            reports.append(f"\n🟢 **Status:** Memory is stable (Growth: {growth:.2f} MB). No critical leak signs detected, sir.")
            
    return "\n".join(reports)

# ==========================================
# 9. Auto README Generator
# ==========================================
def auto_readme_generator(folder_path: str = "", player=None) -> str:
    """Generates an aesthetic, production-ready README.md file using codebase insights."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API config error."
        
    target = folder_path if folder_path else str(get_base_dir())
    path = Path(target)
    
    # Gather workspace information
    files_list = []
    for root, dirs, files in os.walk(str(path)):
        dirs[:] = [d for d in dirs if d not in {".git", "__pycache__", "node_modules", ".venv", "env"}]
        for f in files[:20]: # Expose up to 20 files
            files_list.append(str(Path(root).relative_to(path) / f))
            
    try:
        from google.genai import types
        system_instruction = (
            "You are a professional documentation specialist. Write a beautiful, comprehensive, "
            "and premium README.md document for the provided project directory. "
            "Include sections: Title, Tagline, Features, Project Architecture tree, Quick Setup, "
            "CLI commands, and License. Format as markdown code."
        )
        prompt = (
            f"Project Name: {path.name}\n"
            f"Sample Files Structure:\n" + "\n".join(files_list) + "\n\n"
            "Please generate an outstanding README.md, sir."
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
        )
        
        # Save README
        readme_path = path / "README.md"
        readme_content = response.text
        if "```" in readme_content:
            code_blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", readme_content, re.DOTALL)
            if code_blocks:
                readme_content = code_blocks[0]
                
        readme_path.write_text(readme_content, encoding="utf-8")
        return f"✅ **README.md has been generated and saved successfully, sir!** Written directly to `{readme_path}`."
    except Exception as e:
        return f"README generator error: {e}"

# ==========================================
# 10. Learning & Growth: Interview Prep, Tech Suggester, Daily Challenge
# ==========================================
def interview_prep_mode(topic: str = "Algorithms", difficulty: str = "Medium", player=None) -> str:
    """Presents LeetCode-style algorithms/DS problem with space to type solution."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API load fail, sir."
    try:
        from google.genai import types
        system_instruction = (
            "You are a technical interviewer at a top tier company. Generate a single highly engaging "
            "technical question (like LeetCode or system design problem) based on the topic and difficulty. "
            "Give the problem description, constraints, and a coding interface template. "
            "Ask Pratik Sir to write the code solution. Add a supportive, inspiring Hinglish note."
        )
        prompt = f"Generate a {difficulty} coding problem on {topic}, sir."
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        return response.text
    except Exception as e:
        return f"Interview Prep failed: {e}"

def technology_suggester(project_description: str, player=None) -> str:
    """Recommends a best-fitting modern stack (languages, frameworks, DB, tools) for a project idea."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API error, sir."
    try:
        from google.genai import types
        system_instruction = (
            "You are a Senior technology consultant. Take the user's project description and suggest "
            "the optimal, modern stack (language, backend, frontend, database, hosting, hosting tiers, APIs). "
            "Highlight why this stack fits perfectly, list key technical challenges to expect, and provide a rapid "
            "onboarding project initial folder structure layout. Write in a premium Hinglish style for Pratik Sir."
        )
        prompt = f"Project description:\n{project_description}\n\nSuggest optimal stack, sir."
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.4
            )
        )
        return response.text
    except Exception as e:
        return f"Tech suggester error: {e}"

def daily_coding_challenge(player=None) -> str:
    """Presents a daily short code puzzle/bug to keep coding sharp!"""
    client = _get_gemini_client()
    if not client:
        return "Gemini key missing."
    try:
        from google.genai import types
        system_instruction = (
            "You are a daily coding challenge bot. Generate a short, fun coding puzzle, a code block with a subtle bug, "
            "or a logic riddle. Challenge Pratik Sir to find the bug or solve the riddle. "
            "Provide the answer hidden inside a collapsible details html tag (<details><summary>Click to view solution</summary>...</details>). "
            "Write in an inspiring Hinglish tone."
        )
        prompt = "Provide today's challenge, sir."
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        return response.text
    except Exception as e:
        return f"Daily challenge generator error: {e}"

# ==========================================
# Main Dispatcher
# ==========================================
def project_debug_companion(parameters: dict, player=None) -> str:
    """Main dispatcher for Project & Debug Companion module."""
    action = parameters.get("action", "onboard")
    folder_path = parameters.get("folder_path", "")
    
    if action == "project_start":
        dev_url = parameters.get("dev_url", "http://localhost:3000")
        return project_start_automation(folder_path, dev_url, player)
    elif action == "onboard":
        return codebase_onboarder(folder_path, player)
    elif action == "rag":
        q = parameters.get("query", "")
        if not q:
            return "Please provide 'query' keyword parameter, sir."
        return codebase_rag(q, folder_path, player)
    elif action == "tech_debt":
        return tech_debt_tracker(folder_path, player)
    elif action == "audit_deps":
        return dependency_auditor(folder_path, player)
    elif action == "explain_trace":
        trace = parameters.get("stack_trace", "")
        if not trace:
            return "Please provide 'stack_trace' parameter, sir."
        return stack_trace_explainer(trace, player)
    elif action == "analyze_logs":
        log_f = parameters.get("log_file_path", "")
        lines = int(parameters.get("lines_to_read", 50))
        if not log_f:
            return "Please provide 'log_file_path' parameter, sir."
        return live_log_analyzer(log_f, lines, player)
    elif action == "detect_leak":
        proc = parameters.get("process_name_or_pid", "")
        interval = int(parameters.get("interval_seconds", 5))
        iters = int(parameters.get("iterations", 3))
        return memory_leak_detector(proc, interval, iters, player)
    elif action == "gen_readme":
        return auto_readme_generator(folder_path, player)
    elif action == "interview_prep":
        topic = parameters.get("topic", "Algorithms")
        diff = parameters.get("difficulty", "Medium")
        return interview_prep_mode(topic, diff, player)
    elif action == "tech_suggest":
        desc = parameters.get("project_description", "")
        if not desc:
            return "Please provide 'project_description' parameter, sir."
        return technology_suggester(desc, player)
    elif action == "daily_challenge":
        return daily_coding_challenge(player)
        
    return f"Invalid Project/Debug Companion action: '{action}', sir."
