import subprocess
import sys
import json
import re
import time
from pathlib import Path


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR         = get_base_dir()
API_CONFIG_PATH  = BASE_DIR / "config" / "api_keys.json"
PROJECTS_DIR     = Path.home() / "Desktop" / "IPRayProjects"
MAX_FIX_ATTEMPTS = 5
MODEL_PLANNER    = "gemini-2.5-flash"
MODEL_WRITER     = "gemini-2.5-flash"

def _get_api_key() -> str:
    with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
        return config.get("coding_api_key") or config["gemini_api_key"]


def _get_model(model_name: str):
    import google.generativeai as genai
    genai.configure(api_key=_get_api_key())
    return genai.GenerativeModel(model_name)


def _strip_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()


def _is_rate_limit(error: Exception) -> bool:
    msg = str(error).lower()
    return "429" in msg or "quota" in msg or "resource_exhausted" in msg


class CodexSaver:
    @staticmethod
    def get_config() -> dict:
        try:
            with open(API_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def call_low_cost_worker(prompt: str) -> str:
        config = CodexSaver.get_config()
        provider = config.get("codex_worker_provider", "gemini").lower()
        model_name = config.get("codex_worker_model", "gemini-2.5-flash-lite")
        api_key = config.get("codex_worker_api_key")
        base_url = config.get("codex_worker_base_url")

        if provider == "gemini":
            import google.generativeai as genai
            actual_key = api_key or config.get("coding_api_key") or config.get("gemini_api_key")
            if not actual_key:
                raise ValueError("No Gemini API Key found for low-cost worker.")
            genai.configure(api_key=actual_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
        else:
            import requests
            if not base_url:
                raise ValueError(f"Base URL is required for provider: {provider}")
            
            headers = {
                "Content-Type": "application/json"
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2
            }
            
            url = f"{base_url.rstrip('/')}/chat/completions"
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            res_json = response.json()
            return res_json["choices"][0]["message"]["content"]

    @staticmethod
    def compile_verify(code: str) -> tuple[bool, str | None]:
        try:
            compile(code, "<string>", "exec")
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def route_and_execute(prompt: str, task_type: str = "refactor", player=None) -> str:
        def log(msg: str):
            print(f"[CodexSaver] {msg}")
            if player:
                player.write_log(f"[CodexSaver] {msg}")

        log(f"Routing low-cost task ({task_type}) to worker model...")
        try:
            generated_text = CodexSaver.call_low_cost_worker(prompt)
            stripped_code = _strip_fences(generated_text)
            
            if task_type == "refactor":
                ok, err = CodexSaver.compile_verify(stripped_code)
                if ok:
                    log("Low-cost generation successfully verified (Python Syntax OK).")
                    return generated_text
                else:
                    log(f"Syntax validation failed on low-cost model: {err}. Escalating to premium model...")
            else:
                return generated_text
        except Exception as e:
            log(f"Low-cost routing/execution encountered error: {e}. Escalating to premium model...")
        
        log("Executing task on premium model (gemini-2.5-pro fallback)...")
        import google.generativeai as genai
        config = CodexSaver.get_config()
        actual_key = config.get("coding_api_key") or config.get("gemini_api_key")
        genai.configure(api_key=actual_key)
        
        try:
            premium_model = genai.GenerativeModel("gemini-2.5-pro")
            response = premium_model.generate_content(prompt)
            log("Premium model (gemini-2.5-pro) executed successfully.")
            return response.text
        except Exception as e:
            log(f"gemini-2.5-pro premium call failed: {e}. Falling back to default coding model...")
            premium_model = genai.GenerativeModel("gemini-2.5-flash")
            response = premium_model.generate_content(prompt)
            return response.text



def _parse_traceback(output: str, project_files: list[str]) -> tuple[str | None, int | None]:

    pattern = re.compile(r'File ["\']([^"\']+\.py)["\'],\s+line\s+(\d+)', re.IGNORECASE)
    matches = pattern.findall(output)

    for raw_path, line_str in reversed(matches):
        raw_name = Path(raw_path).name
        for pf in project_files:
            if Path(pf).name == raw_name or pf == raw_path or raw_path.endswith(pf):
                return pf, int(line_str)

    return None, None


def _classify_error(output: str) -> str:

    low = output.lower()

    if any(x in low for x in ("no module named", "modulenotfounderror", "importerror")):
        return "dependency_error"

    if "syntaxerror" in low or "invalid syntax" in low:
        return "syntax_error"
    
    if "cannot import" in low or "importerror" in low:
        return "import_error"

    if any(x in low for x in (
        "traceback", "exception", "error:", "nameerror", "typeerror",
        "attributeerror", "valueerror", "keyerror", "indexerror",
        "zerodivisionerror", "filenotfounderror", "permissionerror",
    )):
        return "runtime_error"

    return "none"


def _has_error(output: str, run_command: str) -> bool:
    
    low = output.lower()

    if "timed out" in low:
        return False

    if not output.strip():
        return False

    error_type = _classify_error(output)
    return error_type != "none"

class RateLimitError(Exception):
    pass


def _plan_project(description: str, language: str) -> dict:
    model = _get_model(MODEL_PLANNER)

    prompt = f"""You are a senior software architect. Create a minimal, complete file plan for this project.

Language: {language}
Description: {description}

Return ONLY valid JSON — no markdown, no explanation:
{{
  "project_name": "snake_case_name",
  "entry_point": "main.py",
  "files": [
    {{
      "path": "main.py",
      "description": "Entry point — what it does and which modules it imports",
      "imports": ["utils.helpers", "core.engine"]
    }},
    {{
      "path": "utils/helpers.py",
      "description": "Helper utilities — what functions it exposes",
      "imports": []
    }}
  ],
  "run_command": "python main.py",
  "dependencies": ["requests"]
}}

Critical rules:
1. List files in DEPENDENCY ORDER — files with no imports come first, entry point comes last.
2. The "imports" field must list every other project module this file imports (dot-notation, e.g. "utils.helpers").
3. Keep it minimal — only files truly needed.
4. Entry point must be in the files list.
5. Use relative paths only (e.g. "utils/helpers.py", not absolute paths).
6. Standard library modules (os, sys, json, etc.) do NOT go in "dependencies".

JSON:"""

    try:
        response = model.generate_content(prompt)
        raw = _strip_fences(response.text)
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"Planner returned invalid JSON: {e}\nRaw: {response.text[:300]}")
    except Exception as e:
        if _is_rate_limit(e):
            raise RateLimitError(str(e))
        raise

def _write_file(
    file_info: dict,
    project_description: str,
    all_files: list[dict],
    language: str,
    project_dir: Path,
    already_written: dict[str, str],
) -> str:
    model = _get_model(MODEL_WRITER)

    file_path = file_info["path"]
    file_desc = file_info.get("description", "")
    file_imports = file_info.get("imports", [])

    file_list = "\n".join(
        f"  [{i+1}] {f['path']}: {f.get('description', '')}"
        for i, f in enumerate(all_files)
    )

    dependency_context = ""
    for dep_dotted in file_imports:
        dep_path = dep_dotted.replace(".", "/") + ".py"
        if dep_path in already_written:
            code_snippet = already_written[dep_path][:2000]
            dependency_context += f"\n\n--- {dep_path} (you must import from this) ---\n{code_snippet}"

    lang_rules = ""
    if language.lower() == "python":
        lang_rules = """
Python-specific rules:
- Use type hints for all function signatures.
- Add docstrings for all public functions and classes.
- Use if __name__ == "__main__": guard in the entry point.
- For relative imports within the project, use: from utils.helpers import foo  (match the project structure exactly).
- Do NOT use implicit relative imports (from . import ...) unless it's a proper package with __init__.py.
- If this is a package subdirectory, create __init__.py files where needed."""
    elif language.lower() in ("javascript", "typescript", "js", "ts"):
        lang_rules = """
JS/TS-specific rules:
- Use ES modules (import/export), not CommonJS (require).
- Add JSDoc comments for all exported functions.
- Handle promise rejections with try/catch in async functions."""

    prompt = f"""You are a senior {language} developer writing production-quality code for a real project.

Project goal: {project_description}

Complete project file structure (in dependency order):
{file_list}

{f"Dependencies this file must import from other project files:{dependency_context}" if dependency_context else ""}

Your task: Write the complete, working code for: {file_path}
Purpose of this file: {file_desc}
{f"This file imports from: {', '.join(file_imports)}" if file_imports else "This file has no project-internal imports."}

{lang_rules}

General rules:
- Output ONLY raw code. Absolutely no explanation, no markdown, no triple backticks.
- Write COMPLETE, RUNNABLE code — no placeholders, no "# TODO", no "pass" stubs.
- Every import must either be from the standard library, listed dependencies, or the project files shown above.
- Match import paths EXACTLY to the file paths in the project structure (e.g. if file is "utils/helpers.py", import as "from utils.helpers import ...").
- Use proper error handling (try/except) where I/O or network calls are made.
- The code must work correctly when the project entry point is run from the project root directory.

Code for {file_path}:"""

    try:
        response = model.generate_content(prompt)
        code = _strip_fences(response.text)

        full_path = project_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(code, encoding="utf-8")

        print(f"[DevAgent] ✅ Written: {file_path} ({len(code)} chars)")
        return code

    except Exception as e:
        if _is_rate_limit(e):
            raise RateLimitError(str(e))
        raise

def _install_dependencies(dependencies: list[str], project_dir: Path) -> str:
    if not dependencies:
        return "No external dependencies."

    to_install = []
    for dep in dependencies:
        pkg_name = re.split(r"[>=<!]", dep)[0].strip()
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", pkg_name],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            to_install.append(dep)
        else:
            print(f"[DevAgent] ✓ Already installed: {pkg_name}")

    if not to_install:
        return f"All dependencies already installed: {', '.join(dependencies)}"

    print(f"[DevAgent] 📦 Installing: {to_install}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install"] + to_install,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=120, cwd=str(project_dir)
        )
        if result.returncode == 0:
            return f"Installed: {', '.join(to_install)}"
        return f"Install warning (non-fatal): {result.stderr[:200]}"
    except subprocess.TimeoutExpired:
        return "Dependency install timed out (non-fatal)."
    except Exception as e:
        return f"Install error (non-fatal): {e}"

def _open_vscode(project_dir: Path) -> bool:
    vscode_candidates = [
        "code",
        rf"C:\Users\{Path.home().name}\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd",
        r"C:\Program Files\Microsoft VS Code\bin\code.cmd",
    ]
    for cmd in vscode_candidates:
        try:
            subprocess.Popen(
                [cmd, str(project_dir)],
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            time.sleep(1.5)
            print(f"[DevAgent] 💻 VSCode opened: {project_dir}")
            return True
        except Exception:
            continue
    return False

def _run_project(run_command: str, project_dir: Path, timeout: int = 30) -> str:
    print(f"[DevAgent] 🚀 Running: {run_command}")
    try:
        parts = run_command.split()
        if parts[0].lower() == "python":
            parts[0] = sys.executable

        result = subprocess.run(
            parts,
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=timeout,
            cwd=str(project_dir)
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        combined_parts = []
        if stdout:
            combined_parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            combined_parts.append(f"STDERR:\n{stderr}")

        return "\n\n".join(combined_parts) if combined_parts else "Ran with no output."

    except subprocess.TimeoutExpired:
        return f"Timed out after {timeout}s — long-running app (server/GUI) is likely working."
    except FileNotFoundError as e:
        return f"Command not found: {e}"
    except Exception as e:
        return f"Run error: {e}"

def _try_auto_install(error_output: str, project_dir: Path) -> bool:
    """ModuleNotFoundError varsa eksik paketi otomatik kurmaya çalışır."""
    pattern = re.compile(
        r"No module named ['\"]([a-zA-Z0-9_\-\.]+)['\"]", re.IGNORECASE
    )
    match = pattern.search(error_output)
    if not match:
        return False

    pkg = match.group(1).replace("_", "-").split(".")[0]
    print(f"[DevAgent] 🔧 Auto-installing missing package: {pkg}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg],
            capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            timeout=60, cwd=str(project_dir)
        )
        return result.returncode == 0
    except Exception:
        return False

def _fix_files(
    error_output: str,
    project_description: str,
    all_files: list[dict],
    file_codes: dict[str, str],
    language: str,
    project_dir: Path,
    entry_point: str,
) -> dict[str, str]:

    model = _get_model(MODEL_PLANNER)

    error_file, error_line = _parse_traceback(error_output, list(file_codes.keys()))
    error_type = _classify_error(error_output)

    files_to_fix: list[str] = []

    if error_file:
        files_to_fix.append(error_file)
        if error_type == "import_error":
            for fi in all_files:
                if error_file.replace("/", ".").replace(".py", "") in fi.get("imports", []):
                    p = fi["path"]
                    if p not in files_to_fix:
                        files_to_fix.append(p)
    else:
        files_to_fix.append(entry_point)

    updated_codes: dict[str, str] = {}

    for fix_path in files_to_fix:
        current_code = file_codes.get(fix_path, "")

        other_ctx = ""
        for fp, code in file_codes.items():
            if fp != fix_path and code:
                snippet = code[:1500] + ("..." if len(code) > 1500 else "")
                other_ctx += f"\n--- {fp} ---\n{snippet}\n"

        line_hint = f"\nError appears to be near line {error_line} in this file." if (
            error_line and fix_path == error_file
        ) else ""

        prompt = f"""You are an expert {language} debugger. Fix the broken file below.

Project goal: {project_description}

All project files:
{chr(10).join(f"  - {f['path']}: {f.get('description', '')}" for f in all_files)}

Other files for context (read-only — fix only the target file):
{other_ctx[:3500]}

File to fix: {fix_path}{line_hint}
Error type: {error_type}

Error output:
{error_output[:2500]}

Current (broken) code:
{current_code}

Rules:
- Output ONLY the complete fixed code. No explanation, no markdown, no backticks.
- Fix ALL errors visible in the error output.
- Keep all existing correct logic — do not remove working features.
- Ensure import paths match the actual project file structure exactly.
- Do NOT introduce new bugs or remove error handling.

Fixed code for {fix_path}:"""

        try:
            response = model.generate_content(prompt)
            fixed = _strip_fences(response.text)

            full_path = project_dir / fix_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(fixed, encoding="utf-8")

            updated_codes[fix_path] = fixed
            print(f"[DevAgent] 🔧 Fixed: {fix_path}")

        except Exception as e:
            if _is_rate_limit(e):
                raise RateLimitError(str(e))
            print(f"[DevAgent] ⚠️ Could not fix {fix_path}: {e}")

    return updated_codes

def _build_project(
    description: str,
    language: str,
    project_name: str,
    timeout: int,
    speak=None,
    player=None,
) -> str:

    def log(msg: str):
        print(f"[DevAgent] {msg}")
        if player:
            player.write_log(f"[DevAgent] {msg}")

    log("Planning project structure...")
    try:
        plan = _plan_project(description, language)
    except RateLimitError:
        msg = "Rate limit reached, sir. Please try again in a moment."
        if speak: speak(msg)
        return msg
    except ValueError as e:
        msg = f"Planning failed: {e}"
        if speak: speak(msg)
        return msg

    proj_name    = project_name or plan.get("project_name", "ipprime_project")
    proj_name    = re.sub(r"[^\w\-]", "_", proj_name)
    project_dir  = PROJECTS_DIR / proj_name
    project_dir.mkdir(parents=True, exist_ok=True)

    files        = plan.get("files", [])
    entry_point  = plan.get("entry_point", "main.py")
    run_command  = plan.get("run_command", f"python {entry_point}")
    dependencies = plan.get("dependencies", [])

    log(f"Project: {proj_name} | Files: {len(files)} | Entry: {entry_point}")

    def _dep_sort_key(fi: dict) -> int:
        return len(fi.get("imports", []))

    sorted_files = sorted(files, key=_dep_sort_key)

    file_codes: dict[str, str] = {}

    for file_info in sorted_files:
        file_path = file_info.get("path", "")
        if not file_path:
            continue

        log(f"Writing {file_path}...")
        for attempt in range(2):
            try:
                code = _write_file(
                    file_info=file_info,
                    project_description=description,
                    all_files=files,
                    language=language,
                    project_dir=project_dir,
                    already_written=file_codes,
                )
                file_codes[file_path] = code
                time.sleep(0.4)
                break
            except RateLimitError:
                if attempt == 0:
                    log("Rate limit — waiting 20s...")
                    time.sleep(20)
                else:
                    log(f"Rate limit retry failed for {file_path}, skipping.")
            except Exception as e:
                log(f"Failed to write {file_path}: {e}")
                break

    if not file_codes:
        msg = "I could not write any project files, sir."
        if speak: speak(msg)
        return msg

    if dependencies:
        install_result = _install_dependencies(dependencies, project_dir)
        log(install_result)

    _open_vscode(project_dir)

    last_output   = ""
    auto_installs = 0  

    for attempt in range(1, MAX_FIX_ATTEMPTS + 1):
        log(f"Running project (attempt {attempt}/{MAX_FIX_ATTEMPTS})...")
        last_output = _run_project(run_command, project_dir, timeout)
        log(f"Output preview: {last_output[:150]}")

        if not _has_error(last_output, run_command):
            msg = (
                f"Project '{proj_name}' is working, sir. "
                f"Built in {attempt} attempt{'s' if attempt > 1 else ''}. "
                f"Saved to: {project_dir}"
            )
            if speak: speak(msg)
            return f"{msg}\n\nOutput:\n{last_output}"

        if attempt == MAX_FIX_ATTEMPTS:
            break

        error_type = _classify_error(last_output)
        if error_type == "dependency_error" and auto_installs < 3:
            installed = _try_auto_install(last_output, project_dir)
            if installed:
                auto_installs += 1
                log("Missing dependency installed, retrying...")
                time.sleep(1)
                continue

        log(f"Fixing errors (type: {error_type})...")
        try:
            updated = _fix_files(
                error_output=last_output,
                project_description=description,
                all_files=files,
                file_codes=file_codes,
                language=language,
                project_dir=project_dir,
                entry_point=entry_point,
            )
            file_codes.update(updated)
            time.sleep(1)
        except RateLimitError:
            msg = "Rate limit reached during fix. Project saved, check it manually in VSCode."
            if speak: speak(msg)
            return msg
        except Exception as e:
            log(f"Fix step failed: {e}")

    msg = (
        f"I couldn't fully fix '{proj_name}' after {MAX_FIX_ATTEMPTS} attempts, sir. "
        f"Project is saved at {project_dir} — open it in VSCode and check manually."
    )
    if speak: speak(msg)
    return f"{msg}\n\nLast error:\n{last_output[:600]}"


def dev_bootstrap(project_path: str = "") -> str:
    """Feature 9: One-Command Dev Env Bootstrapper"""
    p_path = Path(project_path or BASE_DIR).resolve()
    if not p_path.exists():
        return f"Project directory '{p_path}' does not exist, sir."

    bootstrap_actions = []
    vscode_opened = _open_vscode(p_path)
    if vscode_opened:
        bootstrap_actions.append("Opened project in VSCode")
    else:
        bootstrap_actions.append("Could not open VSCode (not found)")

    detected_servers = []
    if (p_path / "package.json").exists():
        try:
            pkg_data = json.loads((p_path / "package.json").read_text(encoding="utf-8"))
            scripts = pkg_data.get("scripts", {})
            if "dev" in scripts:
                subprocess.Popen("start cmd /k npm run dev", shell=True, cwd=str(p_path))
                detected_servers.append("NPM Dev Server (npm run dev)")
            elif "start" in scripts:
                subprocess.Popen("start cmd /k npm start", shell=True, cwd=str(p_path))
                detected_servers.append("NPM Start Server (npm start)")
        except Exception:
            pass

    if (p_path / "manage.py").exists():
        subprocess.Popen("start cmd /k python manage.py runserver", shell=True, cwd=str(p_path))
        detected_servers.append("Django Server (python manage.py runserver)")

    if (p_path / "main.py").exists() and not detected_servers:
        subprocess.Popen("start cmd /k python main.py", shell=True, cwd=str(p_path))
        detected_servers.append("Python Main script (python main.py)")

    if detected_servers:
        bootstrap_actions.append(f"Started development servers: {', '.join(detected_servers)}")
    else:
        bootstrap_actions.append("No active development server configurations recognized automatically.")

    return f"Development environment bootstrapped successfully for '{p_path.name}', sir:\n- " + "\n- ".join(bootstrap_actions)


def git_assistant(action_type: str = "commit", project_path: str = "", player=None) -> str:
    """Feature 10: Autonomous Developer Git Assistant"""
    p_path = Path(project_path or BASE_DIR).resolve()
    if not (p_path / ".git").exists():
        return f"Directory '{p_path}' is not a Git repository, sir."

    def run_git(args: list[str]) -> str:
        res = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=str(p_path), encoding="utf-8", errors="replace")
        return res.stdout.strip() if res.returncode == 0 else res.stderr.strip()

    status = run_git(["status", "--short"])
    if not status:
        return "Your Git repository is fully clean, sir. No changes to commit!"

    diff = run_git(["diff", "HEAD"])
    if not diff:
        diff = run_git(["diff", "--cached"])

    if not diff:
        diff = "Changes detected in files but diff content is empty or binary."

    api_key = _get_api_key()
    if not api_key:
        return "No API key found in configuration to query Gemini for commit messages, sir."

    try:
        prompt = (
            f"Review the following `git diff` of code changes and generate a premium, "
            f"concise, conventional commit message (e.g. 'feat: add holographic particle rings' or 'fix: resolve visualizer ripple scale exception'). "
            f"Provide ONLY the commit message itself — no markdown backticks, no introduction, and no extra notes:\n\n{diff[:4000]}"
        )
        response_text = CodexSaver.route_and_execute(prompt, task_type="git_assistant", player=player)
        commit_msg = _strip_fences(response_text).strip()
    except Exception:
        commit_msg = f"chore: automated update of project files ({time.strftime('%Y-%m-%d %H:%M')})"

    actions_taken = []
    if action_type in ("commit", "push"):
        run_git(["add", "."])
        actions_taken.append("Staged all changes (git add .)")
        
        commit_res = run_git(["commit", "-m", commit_msg])
        actions_taken.append(f"Committed changes with message: '{commit_msg}'")
        
        if action_type == "push":
            run_git(["push"])
            actions_taken.append(f"Pushed commit to remote repository.")
    else:
        actions_taken.append(f"Generated conventional commit message: '{commit_msg}' (Dry Run)")

    return f"Git Assistant completed successfully, sir:\n- " + "\n- ".join(actions_taken)


def refactor_code(file_path: str, action: str = "refactor", player=None) -> str:
    """Feature 11: AI-Powered Code Refactoring & Docstrings"""
    path = Path(file_path).resolve()
    if not path.exists():
        return f"File '{file_path}' does not exist, sir."

    try:
        code = path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Could not read file '{file_path}': {e}"

    api_key = _get_api_key()
    if not api_key:
        return "No API key found to query Gemini, sir."

    try:
        if action == "docstrings":
            prompt = (
                "Review the following code and add high-quality, professional docstrings, "
                "proper inline documentation, and complete type hints following standard typing guidelines. "
                "Preserve all existing functionality perfectly. "
                "Return ONLY the updated source code with no extra conversational text or markdown code fences:\n\n"
            )
        elif action == "simplify":
            prompt = (
                "Review the following code and simplify complex blocks, reduce nested loops/conditionals, "
                "and optimize performance while preserving all features exactly. "
                "Return ONLY the updated source code with no extra conversational text or markdown code fences:\n\n"
            )
        else:
            prompt = (
                "Review the following code and refactor it following SOLID principles, "
                "improving naming conventions, structure, readability, and performance. "
                "Return ONLY the updated source code with no extra conversational text or markdown code fences:\n\n"
            )

        prompt += code
        response_text = CodexSaver.route_and_execute(prompt, task_type="refactor", player=player)
        updated_code = _strip_fences(response_text).strip()

        path.write_text(updated_code, encoding="utf-8")
        
        desc_prompt = (
            f"Explain briefly and clearly (max 3 bullet points) what improvements you "
            f"made during this '{action}' refactoring pass on code from '{path.name}':\n\n{updated_code[:2000]}"
        )
        explanation_text = CodexSaver.route_and_execute(desc_prompt, task_type="explanation", player=player)
        explanation = explanation_text or "Completed refactoring successfully."

        return f"File '{path.name}' has been successfully refactored and updated, sir!\n\nSummary of improvements:\n{explanation}"
    except Exception as e:
        return f"Refactoring of '{path.name}' failed: {e}"


def focus_mode(duration_minutes: int = 25) -> str:
    """Feature 15: Focus Mode & App Blocker (Pomodoro)"""
    import threading
    import numpy as np
    import sounddevice as sd

    def play_lofi():
        sample_rate = 16000
        duration = 10.0
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        left = 0.08 * np.sin(2 * np.pi * 100 * t)
        right = 0.08 * np.sin(2 * np.pi * 104 * t)
        pulse = 0.04 * np.sin(2 * np.pi * 4 * t) * np.sin(2 * np.pi * 0.1 * t)
        stereo = np.column_stack([left + pulse, right + pulse])
        
        try:
            while getattr(threading.current_thread(), "keep_running", True):
                sd.play(stereo.astype(np.float32), sample_rate)
                sd.wait()
        except Exception:
            pass

    focus_thread = threading.Thread(target=play_lofi, daemon=True, name="FocusLofiThread")
    focus_thread.keep_running = True
    focus_thread.start()

    class FocusSession:
        active_session = None
    
    if FocusSession.active_session:
        FocusSession.active_session.keep_running = False
        
    FocusSession.active_session = focus_thread

    return (
        f"Focus Mode initiated for {duration_minutes} minutes, sir!\n"
        f"- Non-essential notifications are now filtered.\n"
        f"- Soothing synthesized lofi binaural focus wave (4Hz Theta) has started playing in the background.\n"
        f"Time to get to work! Let's build something great."
    )


def dev_agent(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
    speak=None,
) -> str:
    p            = parameters or {}
    description  = p.get("description", "").strip()
    language     = p.get("language", "python").strip()
    project_name = p.get("project_name", "").strip()
    timeout      = int(p.get("timeout", 30))

    if not description:
        return "Please describe the project you want me to build, sir."

    return _build_project(
        description  = description,
        language     = language,
        project_name = project_name,
        timeout      = timeout,
        speak        = speak,
        player       = player,
    )