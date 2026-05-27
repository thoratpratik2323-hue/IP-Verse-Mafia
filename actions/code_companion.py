"""
code_companion.py — Interactive pair-programmer assistant providing real-time code explanations.

This is a standard action module for the IP Prime personal assistant suite.
"""

# actions/code_companion.py
import os
import ast
import re
import json
import time
from pathlib import Path
from actions.prime_utils import get_api_key, get_base_dir

# Initialize directories
SNIPPETS_DIR = Path.home() / ".ipprime"
SNIPPETS_FILE = SNIPPETS_DIR / "snippets.json"

def _get_gemini_client():
    """Returns a google-genai client using the central API key."""
    try:
        from google import genai
        api_key = get_api_key()
        if api_key:
            return genai.Client(api_key=api_key)
    except Exception as e:
        print(f"[Code Companion] Client init failed: {e}")
    return None

# ==========================================
# 1. Live Code Explainer
# ==========================================
def live_code_explainer(code_str: str = "", file_path: str = "", player=None) -> str:
    """Explains a given code string, file, or extracts code from a screen screenshot and explains it."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API key properly configure nahi hai, sir."
        
    code_to_explain = code_str
    source_info = "provided snippet"
    
    if not code_to_explain and file_path:
        path = Path(file_path)
        if path.exists():
            try:
                code_to_explain = path.read_text(encoding="utf-8")
                source_info = f"file: {path.name}"
            except Exception as e:
                return f"File read karne mein issue hua, sir: {e}"
        else:
            return f"Specified file exist nahi karti, sir: {file_path}"
            
    # Screen screenshot fallback if no code is provided
    if not code_to_explain:
        source_info = "active screen screenshot"
        if player:
            player.write_thought("Screen capture karke code extract kar raha hoon...")
        try:
            import mss
            from PIL import Image
            import io
            import base64
            
            with mss.mss() as sct:
                monitor = sct.monitors[1]  # primary monitor
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                
                # Compress image to keep token count low
                img.thumbnail((1280, 720))
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG', quality=80)
                img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                
            from google.genai import types
            image_part = types.Part.from_bytes(
                data=base64.b64decode(img_base64),
                mime_type="image/jpeg"
            )
            
            prompt = (
                "Identify any source code visible in this screenshot. Extract that code exactly, "
                "then write a premium architectural explanation of how it works, what it accomplishes, "
                "and explain its flow in clean developer terms. If multiple files/code blocks are present, "
                "organize them clearly. Write in a helpful Hinglish tone addressed to Pratik Sir."
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[image_part, prompt],
            )
            return response.text
        except Exception as e:
            return f"Screen capture ya code extraction failed, sir: {e}. Please provide code string or file_path."

    # Standard code string explanation
    try:
        from google.genai import types
        system_instruction = (
            "You are a staff software architect. Explain the provided code comprehensively, "
            "highlighting design patterns, component relationships, data flow, and complexity. "
            "Make it elegant and direct. Address Pratik Sir in a respectful, highly technical Hinglish tone."
        )
        prompt = f"Please explain this code from {source_info}, sir:\n\n```\n{code_to_explain}\n```"
        
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
        return f"Code explain karne mein error aaya, sir: {e}"

# ==========================================
# 2. Auto Bug Detector
# ==========================================
def auto_bug_detector(code_str: str = "", file_path: str = "", player=None) -> str:
    """Scans code for logic errors, structural faults, syntax flaws, or security vulnerabilities."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API key configure nahi hai, sir."
        
    code_to_scan = code_str
    if not code_to_scan and file_path:
        path = Path(file_path)
        if path.exists():
            try:
                code_to_scan = path.read_text(encoding="utf-8")
            except Exception as e:
                return f"File load error, sir: {e}"
                
    if not code_to_scan:
        return "Scan karne ke liye code ya file provide kijiye, sir!"
        
    try:
        from google.genai import types
        system_instruction = (
            "You are a Senior Principal QA and Security Engineer. Analyze the given code structure carefully "
            "for structural bugs, syntax problems, logical flaws, edge case failures, performance bottlenecks, and security issues. "
            "Return a beautiful markdown list of findings. For each bug, show: Bug name, Severity (Low/Medium/High), Code snippet, "
            "and a clear explanation on how to fix it. Write in a helpful Hinglish style for Pratik Sir."
        )
        prompt = f"Identify all potential bugs, sir:\n\n```\n{code_to_scan}\n```"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1
            )
        )
        return response.text
    except Exception as e:
        return f"Bug detection error: {e}, sir."

# ==========================================
# 3. Code Roaster
# ==========================================
def code_roaster(code_str: str = "", file_path: str = "", player=None) -> str:
    """Provides an extremely funny, sarcastic, and honest roast of the code style, variables, and logic."""
    client = _get_gemini_client()
    if not client:
        return "Gemini key missing hai, sir!"
        
    code_to_roast = code_str
    if not code_to_roast and file_path:
        path = Path(file_path)
        if path.exists():
            code_to_roast = path.read_text(encoding="utf-8")
            
    if not code_to_roast:
        return "Kuch code toh do roast karne ke liye, sir! Empty text ko kaise roast karu?"
        
    try:
        from google.genai import types
        system_instruction = (
            "You are a brutally honest, hilarious, and sarcastic AI coding partner. Roast the user's code. "
            "Make fun of variable names, redundant statements, O(N^2) loops, styling, unnecessary complexity, or lack of comments. "
            "Be witty, extremely funny, but keep it constructive in the end. Write in premium conversational Hinglish "
            "tailored to Pratik Sir (always respectful in addressing him, but hilariously sarcastic about the code itself!)."
        )
        prompt = f"Please roast this code, sir:\n\n```\n{code_to_roast}\n```"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.8
            )
        )
        return response.text
    except Exception as e:
        return f"Roasting engine failed: {e}, sir."

# ==========================================
# 4. Dead Code Finder
# ==========================================
def dead_code_finder(code_str: str = "", file_path: str = "", player=None) -> str:
    """Detects unused variables, functions, parameters, and imports using AST (python) or regex (fallback)."""
    code_content = code_str
    filename = "snippet"
    
    if not code_content and file_path:
        path = Path(file_path)
        if path.exists():
            try:
                code_content = path.read_text(encoding="utf-8")
                filename = path.name
            except Exception as e:
                return f"File read error: {e}"
                
    if not code_content:
        return "No code content to analyze dead code, sir."
        
    findings = []
    
    # Try Python AST analysis
    try:
        tree = ast.parse(code_content)
        imported_names = set()
        used_names = set()
        defined_funcs = {}
        defined_vars = {}
        
        # Walk node tree
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imported_names.add(name.asname or name.name)
            elif isinstance(node, ast.ImportFrom):
                for name in node.names:
                    imported_names.add(name.asname or name.name)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            elif isinstance(node, ast.FunctionDef):
                defined_funcs[node.name] = node.lineno
                # Check parameters
                for arg in node.args.args:
                    defined_vars[f"{node.name}.param.{arg.arg}"] = (arg.arg, node.lineno)
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        defined_vars[target.id] = (target.id, node.lineno)
                        
        # Identify unused imports
        unused_imports = imported_names - used_names
        for imp in unused_imports:
            findings.append(f"- **Unused Import**: `{imp}` load to ho raha hai par use nahi ho raha, sir.")
            
        # Identify unused functions (except main or standard handlers)
        for func, line in defined_funcs.items():
            if func not in used_names and not func.startswith("_") and func != "main":
                findings.append(f"- **Unused Function**: `{func}` (Line {line}) define toh kiya hai par call nahi ho raha, sir.")
                
        # Unused internal variables
        for key, val in defined_vars.items():
            var_name, line = val
            if var_name not in used_names and not var_name.startswith("_"):
                if ".param." in key:
                    func_name = key.split(".param.")[0]
                    findings.append(f"- **Unused Parameter**: `{var_name}` inside function `{func_name}` (Line {line}) is redundant.")
                else:
                    findings.append(f"- **Unused Local Variable**: `{var_name}` (Line {line}) assign kiya par read nahi kiya, sir.")
                    
    except Exception:
        # Static regex backup for multi-language or syntax errors
        imports = re.findall(r"(?:import|from)\s+([a-zA-Z0-9_]+)", code_content)
        for imp in set(imports):
            if code_content.count(imp) <= 1:
                findings.append(f"- **Possible Unused Import**: `{imp}` may be unused in this script, sir.")
                
    if not findings:
        return f"🎉 **Mubarak ho sir!** File `{filename}` mein koi dead code, unused imports, ya redundant variables nahi mile. Perfect clean code!"
        
    return f"🔍 **Dead Code Finder Report for `{filename}`**:\n\n" + "\n".join(findings) + "\n\nInhe remove karke aap apna codebase optimal aur fast bana sakte hain, sir."

# ==========================================
# 5. Code Complexity Analyzer
# ==========================================
def code_complexity_analyzer(code_str: str = "", file_path: str = "", player=None) -> str:
    """Highlights complex functions, nested loops, and deep branches with scoring."""
    code_content = code_str
    if not code_content and file_path:
        path = Path(file_path)
        if path.exists():
            code_content = path.read_text(encoding="utf-8")
            
    if not code_content:
        return "Complexity analyze karne ke liye code provide kijiye, sir!"
        
    issues = []
    
    # Heuristics: Nested loops, deep indentations, function lengths
    lines = code_content.splitlines()
    for idx, line in enumerate(lines, 1):
        indent_level = len(line) - len(line.lstrip())
        if indent_level >= 16:  # Over 4 levels of tab/space nesting
            issues.append(f"- **Deep Nesting (Line {idx})**: Indentation level is very deep here. Substantial branching logic detected.")
            
        # Detect multiple loops on single lines
        if "for " in line and " in " in line and line.count("for ") > 1:
            issues.append(f"- **Complex List Comprehension (Line {idx})**: Multiple loop iterators on a single line.")
            
    # Try parsing functions and counting decisions (if/for/while) to calculate Cyclomatic Complexity
    funcs_complexity = []
    try:
        tree = ast.parse(code_content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = 1
                for sub_node in ast.walk(node):
                    if isinstance(sub_node, (ast.If, ast.For, ast.While, ast.And, ast.Or, ast.ExceptHandler)):
                        complexity += 1
                funcs_complexity.append((node.name, complexity, node.lineno))
    except Exception:
        # Regex backup for function counting
        funcs = re.findall(r"def\s+([a-zA-Z0-9_]+)\(", code_content)
        for f in funcs:
            funcs_complexity.append((f, "Medium (Calculated via fallback)", "N/A"))
            
    complexity_report = ["### 📊 Code Complexity Analyzer Report\n"]
    if funcs_complexity:
        complexity_report.append("#### Functions Complexity Score:")
        for name, score, line in funcs_complexity:
            status = "🟢 Simple (Safe)"
            if isinstance(score, int):
                if score > 10:
                    status = "🔴 Extremely Complex (Refactoring Highly Recommended!)"
                elif score > 5:
                    status = "🟡 Moderately Complex (Consider splitting)"
            complexity_report.append(f"- `{name}` (Line {line}): **Score: {score}** → {status}")
            
    if issues:
        complexity_report.append("\n#### ⚠️ Code Nesting & Structure Warnings:")
        complexity_report.extend(issues[:10])
    else:
        complexity_report.append("\n🟢 Code nesting and structure is clean and within healthy standards, sir!")
        
    return "\n".join(complexity_report)

# ==========================================
# 6. Auto Code Commenter
# ==========================================
def auto_code_commenter(code_str: str = "", file_path: str = "", player=None) -> str:
    """Inserts high-quality inline comments and descriptive JSDoc/docstrings where missing."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API key configure nahi hai, sir."
        
    code_to_comment = code_str
    if not code_to_comment and file_path:
        path = Path(file_path)
        if path.exists():
            code_to_comment = path.read_text(encoding="utf-8")
            
    if not code_to_comment:
        return "Comments insert karne ke liye source code dijiye, sir!"
        
    try:
        from google.genai import types
        system_instruction = (
            "You are a software engineer who writes perfectly documented code. "
            "Scan the provided code, insert helpful inline comments explaining complex logic steps, "
            "and write complete docstrings/JSDoc block comments for every function or class missing them. "
            "Return only the fully commented/documented code block, with no additional explanation wrappers."
        )
        prompt = f"Please add comments and docstrings to this code, sir:\n\n```\n{code_to_comment}\n```"
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt],
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.2
            )
        )
        # Extract code from markdown block if LLM returned it wrapped
        clean_code = response.text
        if "```" in clean_code:
            code_blocks = re.findall(r"```[a-zA-Z]*\n(.*?)```", clean_code, re.DOTALL)
            if code_blocks:
                clean_code = code_blocks[0]
                
        # Optional: Save back to file if requested
        if file_path:
            path = Path(file_path)
            if path.exists():
                path.write_text(clean_code, encoding="utf-8")
                return f"✅ **File successfully commented, sir!** Changes written directly to `{path.name}`."
                
        return f"### 📝 Fully Commented Code:\n\n```python\n{clean_code}\n```"
    except Exception as e:
        return f"Commenting process failed: {e}, sir."

# ==========================================
# 7. Refactor Suggester
# ==========================================
def refactor_suggester(code_str: str = "", file_path: str = "", player=None) -> str:
    """Suggests cleaner, faster, or more modern syntactical ways to rewrite a piece of code."""
    client = _get_gemini_client()
    if not client:
        return "Gemini config required, sir."
        
    code_to_refactor = code_str
    if not code_to_refactor and file_path:
        path = Path(file_path)
        if path.exists():
            code_to_refactor = path.read_text(encoding="utf-8")
            
    if not code_to_refactor:
        return "Refactor suggestions ke liye code block ya file dijiye, sir!"
        
    try:
        from google.genai import types
        system_instruction = (
            "You are a clean code and software design patterns specialist. "
            "Review the provided code and suggest cleaner, faster, DRY-compliant, or more modern "
            "syntactical rewrites (e.g. using list comprehensions, modern async constructs, pattern matching, "
            "or better SOLID principles). Provide side-by-side or block-by-block comparisons with 'Before' and 'After'."
            "Write in a friendly Hinglish tone addressing Pratik Sir."
        )
        prompt = f"Review this code and suggest refactoring, sir:\n\n```\n{code_to_refactor}\n```"
        
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
        return f"Refactor suggest error: {e}, sir."

# ==========================================
# 8. AI Code Generators
# ==========================================
def run_ai_code_generator(action: str, prompt_text: str, schema_description: str = "", player=None) -> str:
    """Helper dispatcher for modular code generation features: tests, api_client, regex, sql, css."""
    client = _get_gemini_client()
    if not client:
        return "Gemini API configure nahi hai, sir."
        
    system_prompts = {
        "gen_tests": (
            "You are a test-driven development expert. Generate complete, highly thorough unit tests "
            "using pytest or unittest framework based on the provided functions or module code. "
            "Ensure edge cases, exceptions, and typical flows are fully tested. Return only clean code."
        ),
        "gen_api_client": (
            "You are an API client generator. Take the endpoint details or requirements, "
            "and generate a fully-featured, elegant client wrapper using fetch/axios (JS/TS) or requests (Python). "
            "Include proper error handling, async/await constructs, headers, and params. Return only clean code."
        ),
        "gen_regex": (
            "You are a Regular Expressions guru. Take the plain English description of what needs matching "
            "and output the exact Regex pattern. Explain step-by-step how each token in the regex works. "
            "Show sample matching and non-matching strings."
        ),
        "gen_sql": (
            "You are a Database Architect. Generate highly optimized SQL queries based on the provided "
            "database description, table schemas, and the plain English request. Organize complex queries with CTEs if needed."
        ),
        "gen_css": (
            "You are a premium CSS and layout designer. Take the UI description, "
            "and generate highly responsive, aesthetic, and modern Vanilla CSS code. "
            "Include variables, smooth transition presets, and hover micro-animations."
        )
    }
    
    sys_instruction = system_prompts.get(action, "Generate clean, production-ready code based on instructions.")
    if schema_description:
        prompt_text = f"Context Schema/Database Structure:\n{schema_description}\n\nRequest:\n{prompt_text}"
        
    try:
        from google.genai import types
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt_text],
            config=types.GenerateContentConfig(
                system_instruction=sys_instruction,
                temperature=0.3
            )
        )
        return response.text
    except Exception as e:
        return f"Code generation error for {action}: {e}, sir."

# ==========================================
# 9. Snippet Manager (Local JSON Registry)
# ==========================================
def manage_snippets(action: str, name: str = "", content: str = "", language: str = "python", player=None) -> str:
    """Manages reusable snippets saved locally in a JSON registry at ~/.ipprime/snippets.json."""
    SNIPPETS_DIR.mkdir(parents=True, exist_ok=True)
    
    registry = {"snippets": []}
    if SNIPPETS_FILE.exists():
        try:
            with open(SNIPPETS_FILE, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            pass
            
    if action == "save":
        if not name or not content:
            return "Snippet save karne ke liye 'name' aur 'content' parameters required hain, sir."
            
        # Check if already exists
        registry["snippets"] = [s for s in registry["snippets"] if s["name"].lower() != name.lower()]
        
        snippet = {
            "name": name,
            "content": content,
            "language": language,
            "created_at": time.strftime("%Y-%m-%d %I:%M %p")
        }
        registry["snippets"].append(snippet)
        
        try:
            with open(SNIPPETS_FILE, "w", encoding="utf-8") as f:
                json.dump(registry, f, indent=4)
            return f"✅ **Snippet '{name}' save ho gaya hai, sir!** Aap isko voice ya command se fetch kar sakte hain."
        except Exception as e:
            return f"Snippet registry write failed: {e}, sir."
            
    elif action == "get":
        if not name:
            return "Snippet retrieve karne ke liye name dijiye, sir."
            
        for s in registry["snippets"]:
            if s["name"].lower() == name.lower():
                return f"### Snippet: {s['name']} ({s['language']})\nSaved at: {s['created_at']}\n\n```{s['language']}\n{s['content']}\n```"
        return f"❌ Snippet '{name}' nahi mila, sir."
        
    elif action == "list":
        if not registry["snippets"]:
            return "Aapke registry mein koi snippets save nahi hain, sir."
            
        lines = ["### 📂 Saved Reusable Snippets:\n"]
        for s in registry["snippets"]:
            lines.append(f"- **{s['name']}** ({s['language']}) - *{s['created_at']}*")
        return "\n".join(lines)
        
    return "Invalid snippet action, sir."

# ==========================================
# Main Code Companion Dispatcher
# ==========================================
def code_companion(parameters: dict, player=None) -> str:
    """Main dispatcher for the Code Companion module."""
    action = parameters.get("action", "explain")
    code_str = parameters.get("code", "")
    file_path = parameters.get("file_path", "")
    language = parameters.get("language", "python")
    
    # AI Generators
    if action in {"gen_tests", "gen_api_client", "gen_regex", "gen_sql", "gen_css"}:
        prompt_text = parameters.get("prompt_text", code_str or "Generate design/structure code")
        schema_desc = parameters.get("schema_description", "")
        return run_ai_code_generator(action, prompt_text, schema_desc, player)
        
    # Snippet Manager
    if action == "snippet":
        sub_action = parameters.get("sub_action", "list")
        name = parameters.get("name", "")
        content = parameters.get("content", code_str)
        return manage_snippets(sub_action, name, content, language, player)
        
    # Standard tools
    if action == "explain":
        return live_code_explainer(code_str, file_path, player)
    elif action == "bug_detect":
        return auto_bug_detector(code_str, file_path, player)
    elif action == "roast":
        return code_roaster(code_str, file_path, player)
    elif action == "dead_code":
        return dead_code_finder(code_str, file_path, player)
    elif action == "complexity":
        return code_complexity_analyzer(code_str, file_path, player)
    elif action == "commenter":
        return auto_code_commenter(code_str, file_path, player)
    elif action == "refactor":
        return refactor_suggester(code_str, file_path, player)
        
    return f"Invalid Code Companion action: '{action}', sir."
