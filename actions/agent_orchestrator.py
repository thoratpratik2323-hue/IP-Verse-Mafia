# actions/agent_orchestrator.py
import subprocess
import json
import re
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
from actions.prime_utils import get_base_dir, get_api_key

BASE_DIR = get_base_dir()

def _get_api_key() -> str:
    return get_api_key()

def _get_genai_client():
    from google import genai
    return genai.Client(api_key=_get_api_key())

def run_cmd(args: list[str], cwd: Path) -> tuple[int, str]:
    """Runs a command securely in a specific directory and returns the exit code and output."""
    try:
        res = subprocess.run(
            args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            shell=False,
            timeout=45
        )
        return res.returncode, res.stdout
    except subprocess.TimeoutExpired as e:
        return -1, f"Command timed out: {e.output if e.output else ''}"
    except Exception as e:
        return -1, str(e)

def check_git_repo(project_path: Path, log_fn) -> bool:
    """Ensures the directory is a initialized git repo with at least one commit."""
    if not (project_path / ".git").exists():
        log_fn("Target directory is not a Git repository. Initializing Git repo dynamically...")
        rc, out = run_cmd(["git", "init"], project_path)
        if rc != 0:
            log_fn(f"Failed to initialize Git: {out}")
            return False
        
        # Configure local git user to avoid commit errors
        run_cmd(["git", "config", "user.name", "IPPrimeOrchestrator"], project_path)
        run_cmd(["git", "config", "user.email", "orchestrator@ipprime.ai"], project_path)
        
        # Add files and commit
        run_cmd(["git", "add", "."], project_path)
        rc, out = run_cmd(["git", "commit", "-m", "Initial commit by IP Prime Orchestrator"], project_path)
        if rc != 0:
            log_fn(f"Failed to make initial commit: {out}")
            return False
        log_fn("Successfully initialized Git repository and committed files.")
    else:
        # Check if there are any commits
        rc, out = run_cmd(["git", "rev-parse", "--is-inside-work-tree"], project_path)
        if rc != 0:
            log_fn("Git repository detected but appears corrupted or has no commits. Making initial commit...")
            run_cmd(["git", "add", "."], project_path)
            run_cmd(["git", "commit", "-m", "Initial commit by IP Prime Orchestrator"], project_path)
            
    return True

def clean_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```[a-zA-Z]*\r?\n?", "", text)
    text = re.sub(r"\r?\n?```\s*$", "", text)
    return text.strip()

def plan_tasks(project_path: Path, instruction: str, log_fn) -> list[dict]:
    """Uses Gemini to plan independent task components."""
    log_fn("Generating multi-agent parallel coding execution plan...")
    
    # Let's read files structure to help planning
    file_structure = []
    for p in project_path.rglob("*"):
        if p.is_file() and not any(part.startswith(".") or part == "__pycache__" for part in p.parts):
            file_structure.append(str(p.relative_to(project_path)))
            
    prompt = f"""You are the Master Architecture Planner of IP Prime. 
We have a target coding project located at: {project_path}
The user wants to implement this feature: "{instruction}"

Existing file structure of the project:
{json.dumps(file_structure, indent=2)}

Split this request into up to 3 completely modular, independent sub-tasks that can be worked on concurrently by separate parallel coding agents in different branches.
For each sub-task, assign a unique name, a clear task goal, and the list of specific relative file paths that sub-agent is allowed to write or modify.
Ensure the file paths are distinct between sub-tasks if possible to minimize merge conflicts.

You MUST return ONLY a valid JSON list of dictionaries containing these exact keys:
"name": Short snake_case name for the sub-agent (e.g. auth_module)
"description": Specific features and functions to implement
"files": Array of relative file paths to write or create

Example JSON structure:
[
  {{
    "name": "data_models",
    "description": "Implement class data structure and save methods",
    "files": ["models.py"]
  }}
]
"""
    try:
        client = _get_genai_client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        cleaned = clean_fences(response.text)
        tasks = json.loads(cleaned)
        if isinstance(tasks, list) and len(tasks) > 0:
            log_fn(f"Orchestration DAG formed successfully with {len(tasks)} parallel workers:")
            for t in tasks:
                log_fn(f" - Agent [{t['name']}]: modifying files {t['files']}")
            return tasks
    except Exception as e:
        log_fn(f"Error calling planner, falling back to single default task: {e}")
        
    return [{
        "name": "core_feature",
        "description": instruction,
        "files": ["main.py"]
    }]

def write_and_fix_file(worktree_path: Path, file_path: str, instruction: str, task_desc: str, log_fn) -> bool:
    """Writes a file inside the worktree sandbox and runs an iterative self-correction build loop."""
    full_path = worktree_path / file_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    existing_content = ""
    if full_path.exists():
        try:
            existing_content = full_path.read_text(encoding="utf-8")
        except Exception:
            pass
            
    prompt = f"""You are a senior developer coding agent.
We are implementing the high-level feature: "{instruction}"
Your specific task assignment is: "{task_desc}"
You are assigned to build/modify the file: "{file_path}"

Here is the existing content of the file (if any):
{existing_content}

Write the complete and optimal code for this file. 
Return ONLY the absolute code content with no markdown code fences, no extra text, and no instructions.
"""
    client = _get_genai_client()
    
    for attempt in range(1, 4):
        log_fn(f"[{file_path}] (Attempt {attempt}) Writing code...")
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            code_content = clean_fences(response.text)
            full_path.write_text(code_content, encoding="utf-8")
            
            # Syntax / Compilation Verification
            if file_path.endswith(".py"):
                rc, verify_out = run_cmd(["python", "-m", "py_compile", file_path], worktree_path)
                if rc == 0:
                    log_fn(f"[{file_path}] Compilation verified successfully (Syntax OK).")
                    return True
                else:
                    log_fn(f"[{file_path}] Verification failed: {verify_out.strip()}")
                    # Feed compilation error back into the prompt
                    prompt = f"""The code you wrote previously for "{file_path}" had compilation/syntax errors.
Errors:
{verify_out}

Here was the code you wrote:
{code_content}

Fix all compilation and syntax errors. Return ONLY the complete corrected code with no fences and no conversational explanation."""
            else:
                log_fn(f"[{file_path}] Written successfully.")
                return True
        except Exception as e:
            log_fn(f"[{file_path}] Error during code generation: {e}")
            
    return False

def execute_worker(task: dict, project_path: Path, instruction: str, log_fn) -> bool:
    """Executes a single sub-task inside a dedicated sandbox Git Worktree."""
    worker_name = task["name"]
    branch_name = f"feature/{worker_name}"
    worktree_path = project_path.parent / "worktrees" / worker_name
    
    log_fn(f"[{worker_name}] Spawning sandboxed worker...")
    
    # 1. Clean worktree if it already exists
    if worktree_path.exists():
        try:
            run_cmd(["git", "worktree", "remove", str(worktree_path), "--force"], project_path)
            shutil.rmtree(worktree_path, ignore_errors=True)
        except Exception:
            pass
            
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 2. Add git worktree
    # Check if branch already exists and delete it
    run_cmd(["git", "branch", "-D", branch_name], project_path)
    
    rc, wt_out = run_cmd(["git", "worktree", "add", str(worktree_path), "-b", branch_name], project_path)
    if rc != 0:
        log_fn(f"[{worker_name}] Failed to create worktree: {wt_out}")
        return False
        
    log_fn(f"[{worker_name}] Sandboxed workspace active at: {worktree_path}")
    
    # 3. Write files
    success = True
    for file_path in task["files"]:
        wt_success = write_and_fix_file(worktree_path, file_path, instruction, task["description"], log_fn)
        if not wt_success:
            success = False
            
    if not success:
        log_fn(f"[{worker_name}] Worker failed to build correct files.")
        return False
        
    # 4. Commit changes in worktree
    run_cmd(["git", "add", "."], worktree_path)
    rc, commit_out = run_cmd(["git", "commit", "-m", f"Implemented sub-task {worker_name}"], worktree_path)
    if rc != 0:
        log_fn(f"[{worker_name}] Nothing committed or commit failed: {commit_out}")
        
    log_fn(f"[{worker_name}] Worker completed sub-task execution successfully.")
    return True

def resolve_merge_conflicts(project_path: Path, log_fn):
    """Scans repository files for conflict markers, asks Gemini to resolve them, and commits the fix."""
    log_fn("Scanning for Git merge conflict markers...")
    client = _get_genai_client()
    
    conflicted_files = []
    for p in project_path.rglob("*"):
        if p.is_file() and not any(part.startswith(".") or part == "__pycache__" for part in p.parts):
            try:
                content = p.read_text(encoding="utf-8")
                if "<<<<<<<" in content and "=======" in content and ">>>>>>>" in content:
                    conflicted_files.append(p)
            except Exception:
                pass
                
    if not conflicted_files:
        log_fn("No merge conflicts found.")
        return True
        
    for p in conflicted_files:
        rel_path = p.relative_to(project_path)
        log_fn(f"Conflict detected in file: {rel_path}. Initiating visual conflict resolution...")
        try:
            content = p.read_text(encoding="utf-8")
            prompt = f"""You are an elite Git conflict resolver.
The file "{rel_path}" has merge conflicts represented by conflict markers (<<<<<<<, =======, >>>>>>>).

Here is the complete file content:
{content}

Resolve this conflict logically, combining both feature sets cleanly without breaking any features or logic.
Remove all conflict markers completely.
Return ONLY the clean resolved code with no markdown fences and no conversational explanation."""
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            resolved_code = clean_fences(response.text)
            p.write_text(resolved_code, encoding="utf-8")
            log_fn(f"Successfully resolved conflict markers in {rel_path}!")
        except Exception as e:
            log_fn(f"Failed to resolve conflict in {rel_path}: {e}")
            return False
            
    # Add and commit the resolved files
    run_cmd(["git", "add", "."], project_path)
    rc, out = run_cmd(["git", "commit", "-m", "Resolved merge conflicts automatically"], project_path)
    return rc == 0

def run_orchestrated_coder(project_path_str: str, instruction: str, player=None) -> str:
    """Main orchestrator routine coordinating multi-agent parallel workflows."""
    def log(msg: str):
        print(f"[Orchestrator] {msg}")
        if player:
            player.write_log(f"[Orchestrator] {msg}")

    def think(msg: str):
        """Push a thought-stream update to the NLA HUD panel."""
        if player and hasattr(player, "write_thought"):
            player.write_thought(msg)

    proj_path = Path(project_path_str).expanduser().resolve()
    if not proj_path.exists():
        return f"Error: Target directory does not exist: {proj_path}"
        
    log(f"Initializing Orchestrator for project workspace: {proj_path}")
    think(f"Orchestrator initialised for workspace: {proj_path.name}")
    
    # 1. Verify Git repo
    if not check_git_repo(proj_path, log):
        return "Initialization failed: Workspace must be a Git repository."
        
    # Ensure working tree is clean before doing anything
    run_cmd(["git", "checkout", "main"], proj_path)
    run_cmd(["git", "checkout", "master"], proj_path) # support master fallback
    run_cmd(["git", "add", "."], proj_path)
    run_cmd(["git", "commit", "-m", "Save workspace state before orchestrating"], proj_path)
    
    # Get current active branch
    rc, active_branch = run_cmd(["git", "branch", "--show-current"], proj_path)
    active_branch = active_branch.strip() or "main"
    log(f"Active workspace branch: {active_branch}")
    
    # 2. Decomposition
    think("Analysing project map to decompose requirements into parallel sub-tasks...")
    tasks = plan_tasks(proj_path, instruction, log)
    
    # 3. Parallel Execution of Workers
    log(f"Launching {len(tasks)} parallel workers concurrently...")
    think(f"Spawning {len(tasks)} sandboxed Git worktree agents concurrently...")
    
    # Thread Pool for execution
    workers_success = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(execute_worker, task, proj_path, instruction, log): task
            for task in tasks
        }
        for fut in as_completed(futures):
            task = futures[fut]
            name = task["name"]
            try:
                result = fut.result()
                workers_success[name] = result
                status = 'SUCCESS' if result else 'FAILURE'
                log(f"Agent [{name}] finished with status: {status}")
                think(f"Agent '{name}' completed — status: {status}")
            except Exception as e:
                workers_success[name] = False
                log(f"Agent [{name}] raised exception: {e}")
                think(f"Agent '{name}' exception: {str(e)[:60]}")
                
    # 4. Merging back into Main Branch
    log("Reconciling and merging parallel workspace branches...")
    think("Reconciling all parallel branches into main workspace...")
    any_merge_failures = False
    
    for task in tasks:
        name = task["name"]
        branch_name = f"feature/{name}"
        worktree_path = proj_path.parent / "worktrees" / name
        
        if not workers_success.get(name, False):
            log(f"Skipping merge of failed agent branch: {branch_name}")
            continue
            
        log(f"Merging changes from {branch_name}...")
        think(f"Merging Git branch '{branch_name}' into '{active_branch}'...")
        rc, merge_out = run_cmd(["git", "merge", branch_name, "--no-edit"], proj_path)
        if rc != 0:
            log(f"Merge conflict or failure encountered on branch {branch_name}. Initiating self-healing conflict resolution...")
            think(f"Conflict detected in branch '{branch_name}' — invoking LLM conflict resolver...")
            resolve_success = resolve_merge_conflicts(proj_path, log)
            if not resolve_success:
                any_merge_failures = True
                log(f"Critical: Failed to auto-resolve conflict on {branch_name}.")
        else:
            log(f"Merged {branch_name} successfully into {active_branch}.")
            
        # Clean up Git Worktree
        log(f"Pruning sandboxed workspace environment for [{name}]...")
        think(f"Pruning Git worktree sandbox for agent '{name}'...")
        run_cmd(["git", "worktree", "remove", str(worktree_path), "--force"], proj_path)
        shutil.rmtree(worktree_path, ignore_errors=True)
        run_cmd(["git", "branch", "-d", branch_name], proj_path)
        
    # Clean up worktree references in git
    run_cmd(["git", "worktree", "prune"], proj_path)
    
    if any_merge_failures:
        return "Orchestrated coding completed, but some merge conflicts required manual intervention. Check git logs, sir!"
        
    return f"Orchestration completed successfully, sir! All parallel sub-agents completed their assigned tasks sandboxed inside Git Worktrees and merged cleanly into '{active_branch}'."
